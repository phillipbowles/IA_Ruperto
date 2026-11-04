"""Textos y decisiones de avisos.py (§6), funciones puras."""
from datetime import UTC, datetime, timedelta

from app.bot import avisos, modelo
from app.bot.contexto import Contexto, PrediccionPlaca, Ultima

AHORA = datetime(2026, 11, 3, 15, 0, tzinfo=UTC)


def ctx(suelo=1800.0, edad=5, h=30.0, riego=None, placa=None, tendencia=-10.0):
    u = Ultima(ts=AHORA - timedelta(minutes=edad), edad_min=edad, suelo_mv=suelo, temp_c=22.4,
               hum_pct=58.0, vpd_kpa=1.1, luz_mv=900.0, firmware="2.0.0")
    c = Contexto(dispositivo="maceta-01", ahora=AHORA, ultima=u, sensores_caidos=edad > 60,
                 h_desde_riego=h, ultimo_riego=riego, placa=placa,
                 tendencia_24h={"min": 1700, "max": 1810, "delta": tendencia, "n": 288})
    c.regla = modelo.evaluar({"suelo_mv": suelo, "h_desde_riego": h})
    return c


def test_texto_medicion():
    t = avisos.texto_medicion(ctx())
    assert t.startswith("🟡 estoy algo caído")
    assert "Tierra: secándose (1800 mV" in t and "estable" in t and "22.4 °C" in t
    assert "humedad 58 %" in t and "templado" in t
    assert "secándose" in avisos.texto_medicion(ctx(tendencia=120))


def test_texto_medicion_sensores_caidos_no_repite_numeros():
    t = avisos.texto_medicion(ctx(edad=600))
    assert "no reportan" in t and "1800" not in t


def test_texto_medicion_avisa_modelo_viejo():
    t = avisos.texto_medicion(ctx(placa=PrediccionPlaca("saludable", 0.9, "arbol-p2-f012-58e644")))
    assert "arbol-p2-f012-58e644" in t


def test_necesita_riego():
    assert avisos.necesita_riego(ctx(suelo=2000))                 # regla: marchita
    assert not avisos.necesita_riego(ctx(suelo=1800))             # estresada, sin umbral
    assert not avisos.necesita_riego(ctx(suelo=2000, h=3))        # regada hace 3 h
    assert not avisos.necesita_riego(ctx(suelo=2000, edad=120))   # datos viejos


def test_antirrebote():
    c = ctx(suelo=2000)
    assert avisos.debe_avisar_riego(c, None, AHORA)
    assert not avisos.debe_avisar_riego(c, AHORA - timedelta(hours=5), AHORA)
    assert avisos.debe_avisar_riego(c, AHORA - timedelta(hours=6), AHORA)
    # Hubo un riego después del último aviso y se volvió a secar: avisa aunque no pasaron 6 h.
    c2 = ctx(suelo=2000, h=6, riego=AHORA - timedelta(hours=6))
    assert avisos.debe_avisar_riego(c2, AHORA - timedelta(hours=7), AHORA)
    assert not avisos.debe_avisar_riego(ctx(suelo=1600), None, AHORA)


def test_texto_aviso_riego():
    assert "tierra está muy seca (2000 mV)" in avisos.texto_aviso_riego(ctx(suelo=2000))
    assert "más de 4 días" in avisos.texto_aviso_riego(ctx(suelo=2000, h=96))


def test_texto_riego():
    t = avisos.texto_riego(ctx(suelo=1600, h=30, riego=AHORA - timedelta(hours=30)))
    assert "30.0 h" in t and "no necesito agua" in t
    assert "¡Agua" in avisos.texto_riego(ctx(suelo=2000, h=96))
    assert "no sé si necesito agua" in avisos.texto_riego(ctx(edad=600))
