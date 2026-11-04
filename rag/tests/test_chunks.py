import re

from rag import CORPUS
from rag.chunks import (MAX_PALABRAS, MIN_PALABRAS, bloques, chunks_corpus, chunks_documento,
                        leer_cabecera, palabras, secciones)


def _doc(tmp_path, cuerpo, nombre="doc"):
    ruta = tmp_path / f"{nombre}.md"
    ruta.write_text('---\ntitulo: "Un título: con dos puntos"\nurl: "https://x.org/a"\n'
                    'fecha_acceso: "2026-11-03"\nautores: null\n---\n\n# T\n\n' + cuerpo,
                    encoding="utf-8")
    return ruta


def test_cabecera():
    meta, cuerpo = leer_cabecera('---\ntitulo: "A: b"\nurl: null\n---\n\n# X\ntexto')
    assert meta == {"titulo": "A: b", "url": None}
    assert cuerpo.startswith("# X")


def test_secciones_cortas_se_juntan_y_largas_se_parten():
    corta = " ".join(["corta"] * 60)
    larga = "\n\n".join(" ".join([f"p{k}"] * 90) for k in range(10))  # 900 palabras
    secs = secciones(f"## A\n{corta}\n\n## B\n{corta}\n\n## C\n{larga}\n\n## D\n{corta}")
    out = bloques(secs)
    assert all(palabras(t) <= MAX_PALABRAS for t in out)
    assert out[0].startswith("A\n") and "\nB\n" in out[0]  # A y B (60 + 60) juntas
    # No se pierde ni se duplica texto.
    total = sum(palabras(t) for t in out)
    assert total >= 60 * 3 + 900
    assert sum(t.count("p3") for t in out) == 90


def test_parrafo_enorme_se_parte_por_palabras():
    out = bloques([("X", " ".join(["w"] * 1000))])
    assert all(palabras(t) <= MAX_PALABRAS for t in out)
    assert sum(t.split().count("w") for t in out) == 1000


def test_ids_estables_y_campos(tmp_path):
    ruta = _doc(tmp_path, "## Uno\n" + "a " * 200 + "\n\n## Dos\n" + "b " * 200)
    c1 = chunks_documento(ruta, "ciencia")
    c2 = chunks_documento(ruta, "ciencia")
    assert [c.id for c in c1] == [c.id for c in c2] == ["ciencia/doc#0", "ciencia/doc#1"]
    assert c1[0].titulo == "Un título: con dos puntos"
    assert c1[0].url == "https://x.org/a" and c1[0].fecha is None
    assert set(c1[0].dict()) == {"id", "fuente", "titulo", "url", "fecha", "texto"}


def test_corpus_real_respeta_tamanos_y_cita_fuentes():
    for fuente in ("ciencia", "proyecto"):
        cs = chunks_corpus(CORPUS / fuente, fuente)
        assert cs
        assert all(re.fullmatch(rf"{fuente}/[a-z0-9-]+#\d+", c.id) for c in cs)
        assert len({c.id for c in cs}) == len(cs)
        assert all(palabras(c.texto) <= MAX_PALABRAS for c in cs)
        # Un chunk corto sólo si juntarlo con el siguiente del mismo documento se pasaría.
        for a, b in zip(cs, cs[1:]):
            if a.id.split("#")[0] == b.id.split("#")[0] and palabras(a.texto) < MIN_PALABRAS:
                assert palabras(a.texto) + palabras(b.texto) > MAX_PALABRAS
    docs = sorted((CORPUS / "ciencia").glob("*.md"))
    assert len(docs) >= 6
    for d in docs:
        meta, _ = leer_cabecera(d.read_text(encoding="utf-8"))
        assert meta["url"].startswith("https://"), d
        assert meta["fecha_acceso"] and meta["institucion"], d
