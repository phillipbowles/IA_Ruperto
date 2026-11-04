"""Regla vigente recalculada en el server y h_desde_riego (docs/ENTREGA3.md D8)."""
import math
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from conftest import PASO, T0

from app.bot import modelo
from app.bot.modelo import Muestra, detectar_riegos, evaluar


# ─── las cuatro hojas de la regla regla-p3-f07-79b556 ─────────────────────
@pytest.mark.parametrize("suelo, h, clase, rama", [
    (1900, 2.0, "estresada", ["h_desde_riego = 2 ≤ 5.5"]),           # recién regada
    (1600, 30.0, "saludable", ["h_desde_riego = 30 > 5.5", "suelo_mv = 1600 ≤ 1716"]),
    (1800, 30.0, "estresada", ["h_desde_riego = 30 > 5.5", "suelo_mv = 1800 > 1716",
                               "suelo_mv = 1800 ≤ 1939.88"]),
    (2000, 96.0, "marchita", ["h_desde_riego = 96 > 5.5", "suelo_mv = 2000 > 1716",
                              "suelo_mv = 2000 > 1939.88"]),
])
def test_regla_cuatro_ramas(suelo, h, clase, rama):
    r = evaluar({"suelo_mv": suelo, "h_desde_riego": h})
    assert r.clase == clase
    assert list(r.rama) == rama
    assert r.version == "regla-p3-f07-79b556"
    assert 0 < r.proba <= 1


def test_regla_umbral_inclusivo():
    # sklearn compara x <= umbral: el valor exacto va por "si".
    assert evaluar({"suelo_mv": 1716, "h_desde_riego": 10}).clase == "saludable"
    assert evaluar({"suelo_mv": 1800, "h_desde_riego": 5.5}).clase == "estresada"


@pytest.mark.parametrize("x", [
    {"suelo_mv": None, "h_desde_riego": 30.0},          # sonda caída o saturada
    {"suelo_mv": float("nan"), "h_desde_riego": 30.0},
    {"h_desde_riego": 30.0},
])
def test_regla_sensores_caidos_no_predice(x):
    r = evaluar(x)
    assert r.clase is None and r.proba is None
    assert "suelo_mv" in r.motivo


def test_regla_lee_el_json_del_exportador():
    regla = modelo.cargar_regla()
    assert regla.features == ("suelo_mv", "h_desde_riego")
    front = Path(__file__).parents[2] / "frontend" / "src" / "modelo_placa.json"
    if front.exists():   # el del bot es el mismo JSON que dibuja el dashboard
        assert front.read_text() == modelo.RUTA_MODELO.read_text()


# ─── h_desde_riego sobre una serie sintética ──────────────────────────────
def serie(suelos, t0=T0, boot=1, raw=None):
    return [Muestra(ts=t0 + i * PASO, suelo_mv=s, boot_id=boot,
                    suelo_raw=(raw[i] if raw else None)) for i, s in enumerate(suelos)]


def test_riego_detectado_y_horas():
    s = serie([1900.0] * 20 + [1500.0] + [1500.0] * 23)    # cae 400 mV en la muestra 20
    r = detectar_riegos(s)
    assert r.detectados == [T0 + 20 * PASO]
    assert r.h_desde_riego == pytest.approx(23 * 5 / 60)


def test_caida_chica_no_es_riego():
    r = detectar_riegos(serie([1900.0] * 20 + [1660.0] * 5))   # 240 < 250
    assert r.detectados == [] and r.h_desde_riego == modelo.RIEGO_TOPE_H


def test_caida_en_warmup_no_cuenta():
    # La ventana necesita 12 muestras anteriores: la caída en la muestra 11 no vale.
    r = detectar_riegos(serie([1900.0] * 11 + [1500.0] * 5))
    assert r.detectados == []
    r = detectar_riegos(serie([1900.0] * 12 + [1500.0] * 5))
    assert len(r.detectados) == 1


def test_hueco_corta_el_tramo_pero_conserva_el_riego():
    a = serie([1900.0] * 15 + [1500.0] * 3)                       # riego en la 15
    t1 = a[-1].ts + timedelta(minutes=30)                         # hueco > 7,5 min
    b = serie([1950.0] * 5 + [1500.0], t0=t1)                     # caída en warm-up: no cuenta
    r = detectar_riegos(a + b)
    assert r.detectados == [T0 + 15 * PASO]
    assert r.h_desde_riego == pytest.approx((b[-1].ts - (T0 + 15 * PASO)).total_seconds() / 3600)


def test_reinicio_corta_el_tramo():
    a = serie([1900.0] * 15, boot=1)
    b = serie([1500.0] * 3, t0=a[-1].ts + PASO, boot=2)           # sin hueco, pero otro boot
    assert detectar_riegos(a + b).detectados == []


def test_sonda_saturada_o_faltante_no_es_riego():
    # La repetición de la última empujada no es una lectura real; volver de un
    # faltante a una caída sí compara contra la última empujada.
    suelos = [1900.0] * 14 + [None, 1500.0]
    assert len(detectar_riegos(serie(suelos)).detectados) == 1
    raw = [2300] * 14 + [0, 0]                                    # saturada = faltante
    r = detectar_riegos(serie([1900.0] * 14 + [0.0, 0.0], raw=raw))
    assert r.detectados == []


def test_tope_96_h():
    s = serie([1900.0] * 13 + [1500.0])
    s += [Muestra(ts=s[-1].ts + timedelta(hours=200), suelo_mv=1500.0, boot_id=1)]
    r = detectar_riegos(s)
    assert r.h_desde_riego == modelo.RIEGO_TOPE_H


def test_paridad_con_features_py():
    """Misma semántica que ml/plantaia_ml/features.py (si está instalado el entorno de ml)."""
    pd = pytest.importorskip("pandas")
    sys.path.insert(0, str(Path(__file__).parents[2] / "ml"))
    features = pytest.importorskip("plantaia_ml.features")
    import random
    rng = random.Random(7)
    filas, ts, boot, nivel = [], T0, 1, 1900.0
    for i in range(400):
        if rng.random() < 0.02:
            ts += timedelta(minutes=20)                 # hueco
        if rng.random() < 0.01:
            boot += 1                                   # reinicio
        nivel = nivel - 400 if rng.random() < 0.03 else min(2300.0, nivel + rng.uniform(0, 8))
        suelo = None if rng.random() < 0.05 else round(nivel)
        filas.append({"ts": ts, "dispositivo": "maceta-01", "boot_id": boot, "suelo_mv": suelo,
                      "luz_mv": 800.0, "temp_c": 22.0, "hum_aire_pct": 55.0})
        ts += PASO
    df = pd.DataFrame(filas)
    df["suelo_mv"] = df.suelo_mv.astype(float)
    df["ts"] = pd.to_datetime(df.ts, utc=True)
    f = features.calcular_features(df, col_ntc=None)
    esperado = f.h_desde_riego.to_numpy()
    s = [Muestra(ts=r["ts"], suelo_mv=r["suelo_mv"], boot_id=r["boot_id"]) for r in filas]
    con_riego = 0
    for k in range(50, 400, 7):      # h_desde_riego en distintos cortes de la serie
        if math.isnan(esperado[k]):
            continue
        assert detectar_riegos(s[: k + 1]).h_desde_riego == pytest.approx(esperado[k], abs=1e-6), k
        con_riego += esperado[k] < modelo.RIEGO_TOPE_H
    assert con_riego > 10            # la serie tiene riegos de verdad, no sólo el tope
