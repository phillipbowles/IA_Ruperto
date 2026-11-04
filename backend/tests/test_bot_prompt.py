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
    for regla in ("[2]", "sensores están caídos", "EN PALABRAS SIMPLES", "80 palabras", "no coinciden",
                  "marchito"):
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


def _frag(id_, fuente="ciencia"):
    return Fragmento(id_, fuente, "t", None, None, "x", 0.5)


def test_citas_salen_del_texto_y_la_ciencia_va_al_pie():
    frags = [_frag("ciencia/ufifas-house-plant-care#0"), _frag("historial/dia-2026-10-12#0", "historial"),
             _frag("ciencia/aspca-toxicidad#0"), _frag("ciencia/ufifas-dano-por-frio#1")]
    texto, citados = prompt.citas("Regame [1, 2]. Soy tóxico para gatos [3][4]. Y [9] no existe.", frags)
    assert texto == ("Regame. Soy tóxico para gatos. Y no existe.\n\n"
                     "📚 Fuente: Universidad de Florida (UF/IFAS), ASPCA")
    assert citados == {0, 1, 2, 3}


def test_sin_citas_no_hay_pie():
    assert prompt.citas("Hola.", [_frag("ciencia/rhs-guia-genero#0")]) == ("Hola.", set())
    # Historial o proyecto citados no van al pie: son datos propios, no una fuente externa.
    assert prompt.citas("Me regaron [1].", [_frag("historial/dia-2026-10-12#0", "historial")])[0] \
        == "Me regaron."


def test_turno_lleva_primero_las_palabras_simples():
    t = prompt.turno_usuario("e", "d", [], "¿?", simple="- Tierra: seca.")
    assert t.startswith("EN PALABRAS SIMPLES\n- Tierra: seca.\n\nESTADO ACTUAL")
