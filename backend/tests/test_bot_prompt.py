"""Armado del prompt (§5.3): bloques, numeración de fragmentos, persona, memoria."""
from app.bot import persona, prompt
from app.bot.recuperar import Fragmento


def frag(i, fuente="ciencia", url="https://u", fecha=None):
    return Fragmento(id=f"{fuente}/d#{i}", fuente=fuente, titulo=f"Doc {i}", url=url,
                     fecha=fecha, texto=f"texto {i}", score=0.9)


def test_bloques_en_orden():
    t = prompt.turno_usuario("- suelo 1800 mV", "- 7 días", [frag(0)], "¿tenés sed?")
    pos = [t.index(b) for b in ("ESTADO ACTUAL", "ÚLTIMOS 7 DÍAS", "FRAGMENTOS", "PREGUNTA")]
    assert pos == sorted(pos)
    assert "- suelo 1800 mV" in t and t.rstrip().endswith("¿tenés sed?")


def test_fragmentos_numerados_desde_1_con_fuente():
    t = prompt.texto_fragmentos([frag(0), frag(1, "historial", url=None, fecha="2026-10-20")])
    assert t.startswith("[1] fuente: ciencia — Doc 0 — https://u\ntexto 0")
    assert "[2] fuente: historial — Doc 1 — fecha 2026-10-20\ntexto 1" in t
    assert prompt.texto_fragmentos([]) == "(no se recuperó ningún fragmento)"


def test_fragmento_largo_se_recorta():
    f = Fragmento("a", "ciencia", "t", None, None, "x" * 5000, 0.5)
    assert len(prompt.texto_fragmentos([f])) < 1700


def test_system_es_ruperto_con_reglas():
    s = prompt.system()
    assert "Ruperto" in s and "lirio de paz" in s and "voseo" in s
    for regla in ("[2]", "SENSORES CAÍDOS", "más mV", "120 palabras", "no coinciden"):
        assert regla in s
    assert s is persona.SYSTEM


def test_memoria_guarda_seis_turnos():
    m = prompt.Memoria()
    for i in range(8):
        m.agregar(1, f"p{i}", f"r{i}")
    h = m.historial(1)
    assert len(h) == 12 and h[0] == {"role": "user", "text": "p2"} and h[-1]["text"] == "r7"
    assert m.historial(2) == []
    c = prompt.contenidos(m, 1, "TURNO")
    assert c[-1] == {"role": "user", "text": "TURNO"} and len(c) == 13
