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
    assert contexto.armar_contexto(db, ahora=T0).ultima.suelo_mv == 1500.0
