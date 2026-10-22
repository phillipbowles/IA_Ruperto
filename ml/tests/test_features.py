"""Tests de features.py contra el contrato §4.

    /opt/anaconda3/bin/python -m pytest ml/tests
    /opt/anaconda3/bin/python ml/tests/test_features.py      # sin pytest
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plantaia_ml.features import FEATURES, calcular_features, vpd_kpa  # noqa: E402


def _serie(n, suelo=None, luz=None, temp=20.0, hum=50.0, boot=1, inicio="2026-10-01 00:00",
           paso_min=5, dispositivo="x"):
    ts = pd.date_range(inicio, periods=n, freq=f"{paso_min}min", tz="UTC")
    return pd.DataFrame({
        "ts": ts, "dispositivo": dispositivo, "boot_id": boot,
        "suelo_mv": suelo if suelo is not None else np.full(n, 1500.0),
        "luz_mv": luz if luz is not None else np.full(n, 1000.0),
        "temp_c": temp, "hum_aire_pct": hum, "temp_ntc_c": np.nan,
    })


def test_orden_de_columnas():
    assert FEATURES == ["suelo_mv", "suelo_delta_1h", "temp_c", "hum_aire_pct",
                        "vpd_kpa", "luz_mv", "luz_media_1h"]
    f = calcular_features(_serie(3))
    assert list(f.columns[:7]) == FEATURES


def test_warmup_y_delta_en_rampa():
    # Rampa de +10 mV por muestra: fuera del warm-up el delta es 12·10 = 120.
    n = 20
    f = calcular_features(_serie(n, suelo=1000.0 + 10 * np.arange(n)))
    assert f.warmup.iloc[:12].all()          # muestras 0..11: menos de 12 anteriores
    assert not f.warmup.iloc[12:].any()      # la 12 ya tiene 12 anteriores
    assert (f.suelo_delta_1h.iloc[:12] == 0).all()
    assert np.allclose(f.suelo_delta_1h.iloc[12:], 120.0)


def test_media_de_luz():
    n = 20
    luz = np.arange(n, dtype=float) * 100
    f = calcular_features(_serie(n, luz=luz))
    assert f.luz_media_1h.iloc[0] == 0.0                      # sólo la actual
    assert math.isclose(f.luz_media_1h.iloc[4], luz[:5].mean())
    assert math.isclose(f.luz_media_1h.iloc[19], luz[7:20].mean())  # últimas 13


def test_vpd_punto_conocido():
    # A 20 °C la presión de saturación de Tetens es 2,3383 kPa; con 50 % de HR,
    # el déficit es la mitad.
    assert math.isclose(float(vpd_kpa(20.0, 50.0)), 1.16916, rel_tol=1e-4)
    assert math.isclose(float(vpd_kpa(25.0, 100.0)), 0.0, abs_tol=1e-12)
    f = calcular_features(_serie(2))
    assert math.isclose(f.vpd_kpa.iloc[0], 1.16916, rel_tol=1e-4)


def test_corte_en_huecos_y_boot():
    a = _serie(15, suelo=1000.0 + 10 * np.arange(15))
    # Hueco de 10 min: arranca otro tramo, vuelve el warm-up.
    b = _serie(15, suelo=1000.0 + 10 * np.arange(15), inicio="2026-10-01 01:20")
    c = _serie(15, boot=2, inicio="2026-10-01 02:35")  # pegado, pero otro boot_id
    df = pd.concat([a, b, c], ignore_index=True)
    f = calcular_features(df)
    assert f.tramo.nunique() == 3
    assert f.warmup.iloc[15:27].all() and not f.warmup.iloc[27]
    assert f.warmup.iloc[30:42].all()
    assert (f.suelo_delta_1h.iloc[15:27] == 0).all()


def test_faltantes():
    s = _serie(14)
    s.loc[0, "temp_c"] = np.nan
    s.loc[0, "hum_aire_pct"] = np.nan
    s.loc[0, "temp_ntc_c"] = 25.0
    s.loc[5, ["temp_c", "hum_aire_pct"]] = [np.nan, np.nan]
    s.loc[6, "suelo_mv"] = np.nan
    f = calcular_features(s)
    # Sin DHT nunca visto: no hay T ni HR (el termistor no es respaldo, §4) y no
    # se infiere, pero la muestra entra al buffer.
    assert not f.valido.iloc[0]
    assert np.isnan(f.temp_c.iloc[0]) and np.isnan(f.hum_aire_pct.iloc[0])
    assert f.marcas.iloc[0] & 0x40 and f.marcas.iloc[0] & 0x80
    assert f.luz_media_1h.iloc[1] == 1000.0 and f.valido.iloc[1]
    # DHT faltante → último válido del tramo.
    assert f.valido.iloc[5] and f.temp_c.iloc[5] == 20.0
    # Suelo faltante → se repite el anterior.
    assert f.suelo_mv.iloc[6] == 1500.0 and f.marcas.iloc[6] & 0x01
    # El primer valor del tramo sin suelo no tiene con qué rellenarse.
    s2 = _serie(3)
    s2.loc[0, "suelo_mv"] = np.nan
    f2 = calcular_features(s2)
    assert not f2.valido.iloc[0] and f2.valido.iloc[1]
    assert f2.luz_media_1h.iloc[1] == 1000.0  # la fila 0 no entró al buffer


def test_termistor_nunca_es_respaldo():
    # HR válida y T del DHT ausente desde el arranque: T queda en NaN aunque el
    # termistor lea, y no se infiere hasta que aparezca una T del DHT.
    s = _serie(4)
    s["temp_ntc_c"] = 30.0
    s.loc[0:1, "temp_c"] = np.nan
    f = calcular_features(s)
    assert not f.valido.iloc[0] and not f.valido.iloc[1]
    assert np.isnan(f.temp_c.iloc[0]) and f.hum_aire_pct.iloc[0] == 50.0
    assert f.valido.iloc[2] and f.temp_c.iloc[2] == 20.0
    # Una falla suelta después usa el último válido, nunca el termistor.
    s.loc[3, "temp_c"] = np.nan
    f = calcular_features(s)
    assert f.valido.iloc[3] and f.temp_c.iloc[3] == 20.0 and f.marcas.iloc[3] & 0x04


def test_sonda_saturada_es_faltante():
    # dataset._con_features pasa la sonda saturada como NaN: se repite el anterior.
    from plantaia_ml.dataset import _con_features
    b = _serie(4)
    b["suelo_saturado"] = [False, True, False, False]
    b.loc[1, "suelo_mv"] = 3124.0
    b["clase"] = "saludable"
    f = _con_features(b)
    assert f.suelo_mv.iloc[1] == 1500.0 and f.marcas.iloc[1] & 0x01


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
            print("ok", nombre)
