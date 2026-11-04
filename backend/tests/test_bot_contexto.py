"""Contexto en vivo por SQL (§5.1) sobre SQLite en memoria."""
from datetime import timedelta

from conftest import PASO, T0, cargar

from app.bot import contexto


def test_sin_mediciones(db):
    ctx = contexto.armar_contexto(db, ahora=T0)
    assert ctx.ultima is None and ctx.sensores_caidos
    assert "No hay ninguna medición" in contexto.texto_estado(ctx)


def test_estado_vivo_con_riego_y_placa_vieja(db):
    # 2 h a 1900 mV, riego (cae a 1500) y 1 h más: regla = estresada (recién regada).
    suelos = [1900.0] * 24 + [1500.0] * 12
    filas = cargar(db, suelos, pred=("saludable", 0.7, "arbol-p2-f012-58e644"))
    ahora = filas[-1].ts_dispositivo + timedelta(minutes=3)
    ctx = contexto.armar_contexto(db, ahora=ahora)
    assert not ctx.sensores_caidos and ctx.ultima.edad_min == 3
    assert ctx.ultima.suelo_mv == 1500.0
    assert ctx.ultimo_riego == T0 + 24 * PASO and ctx.riegos_7d == [T0 + 24 * PASO]
    assert ctx.h_desde_riego == 11 * 5 / 60
    assert ctx.regla.clase == "estresada" and ctx.placa.clase == "saludable"
    assert ctx.coinciden is False
    assert ctx.tendencia_24h == {"min": 1500.0, "max": 1900.0, "delta": -400.0, "n": 36}
    assert ctx.ultima.vpd_kpa is not None
    txt = contexto.texto_estado(ctx)
    assert "1500 mV" in txt and "estresada" in txt and "arbol-p2-f012-58e644" in txt
    assert "modelo viejo" in txt and "SENSORES CAÍDOS" not in txt
    dias = contexto.texto_dias(ctx)
    assert "2026-11-01" in dias and "36 muestras" in dias


def test_sensores_caidos(db):
    filas = cargar(db, [1800.0] * 20)
    ctx = contexto.armar_contexto(db, ahora=filas[-1].ts_dispositivo + timedelta(days=5))
    assert ctx.sensores_caidos and ctx.ultima.edad_min == 5 * 24 * 60
    txt = contexto.texto_estado(ctx)
    assert "SENSORES CAÍDOS" in txt and "NO de ahora" in txt and "5 días" in txt
    # Las ventanas se cuentan hasta la última muestra: los días con datos siguen ahí.
    assert ctx.dias and ctx.tendencia_24h["n"] == 20


def test_sonda_saturada_es_faltante(db):
    filas = cargar(db, [1800.0] * 3)
    filas[-1].suelo_raw = 4095
    db.commit()
    ctx = contexto.armar_contexto(db, ahora=filas[-1].ts_dispositivo)
    assert ctx.ultima.suelo_mv is None
    assert ctx.regla.clase is None and "suelo_mv" in ctx.regla.motivo
    assert "saturada (suelo_raw 4095)" in contexto.texto_estado(ctx)


def test_otro_dispositivo_no_se_mezcla(db, monkeypatch):
    cargar(db, [1800.0] * 3, dispositivo="maceta-01")
    cargar(db, [1500.0] * 3, dispositivo="otra", t0=T0 + timedelta(hours=1))
    ctx = contexto.armar_contexto(db, ahora=T0 + timedelta(hours=2))
    assert ctx.dispositivo == "maceta-01" and ctx.ultima.suelo_mv == 1800.0
    monkeypatch.setenv("BOT_DISPOSITIVO", "otra")
    assert contexto.armar_contexto(db, ahora=T0 + timedelta(hours=2)).ultima.suelo_mv == 1500.0


def test_palabras_simples_en_masculino():
    from app.bot import modelo
    assert modelo.umbrales_suelo()[0] == 1716.0 and 1939 < modelo.umbrales_suelo()[1] < 1941
    assert [contexto.tierra_simple(v) for v in (1500, 1716, 1800, 2000, None)] == \
        ["húmeda", "húmeda", "secándose", "muy seca", None]
    assert contexto.aire_simple(10, 60) == "fresco" and contexto.aire_simple(30, 30) == "caluroso y seco"


def test_texto_simple_marchito_y_caido(db):
    filas = cargar(db, [2000.0] * 20)
    ctx = contexto.armar_contexto(db, ahora=filas[-1].ts_dispositivo + timedelta(minutes=2))
    s = contexto.texto_simple(ctx)
    assert "marchito" in s and "marchita" not in s and "Tierra: muy seca." in s
    assert "No sé cómo estoy AHORA" not in s
    caido = contexto.texto_simple(contexto.armar_contexto(db, ahora=filas[-1].ts_dispositivo
                                                          + timedelta(days=2)))
    assert caido.startswith("- No sé cómo estoy AHORA")


def test_texto_simple_recien_regado(db):
    filas = cargar(db, [1900.0] * 24 + [1500.0] * 12)
    ctx = contexto.armar_contexto(db, ahora=filas[-1].ts_dispositivo)
    assert "recuperándome de un riego reciente" in contexto.texto_simple(ctx)


def test_el_reloj_inyectado_no_ve_el_futuro(db):
    filas = cargar(db, [1500.0] * 12 + [2000.0] * 12)
    ctx = contexto.armar_contexto(db, ahora=filas[11].ts_dispositivo)
    assert ctx.ultima.suelo_mv == 1500.0 and ctx.ultima.edad_min == 0


def test_maceta_02_es_la_misma_planta(db):
    # Riego registrado como maceta-02 y después la placa vuelve como maceta-01 (D212).
    cargar(db, [1950.0] * 13 + [1500.0] * 3, dispositivo="maceta-02")
    cargar(db, [1520.0] * 3, dispositivo="maceta-01", t0=T0 + 16 * PASO)
    ctx = contexto.armar_contexto(db, ahora=T0 + 19 * PASO)
    assert ctx.ultimo_riego == T0 + 13 * PASO and ctx.ultima.suelo_mv == 1520.0
