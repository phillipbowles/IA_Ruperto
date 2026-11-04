"""recuperar.buscar con un índice de fixture chico (contrato §4)."""
import json

import numpy as np
import pytest

from app.bot import recuperar

CHUNKS = [
    {"id": "ciencia/riego#0", "fuente": "ciencia", "titulo": "Riego del lirio",
     "url": "https://ejemplo.edu/riego", "fecha": None, "texto": "regar cuando se seca"},
    {"id": "ciencia/luz#0", "fuente": "ciencia", "titulo": "Luz", "url": "https://ejemplo.edu/luz",
     "fecha": None, "texto": "luz indirecta"},
    {"id": "historial/2026-10-20", "fuente": "historial", "titulo": "Día 20/10", "url": None,
     "fecha": "2026-10-20", "texto": "riego a las 10"},
    {"id": "proyecto/sonda#0", "fuente": "proyecto", "titulo": "La sonda", "url": None,
     "fecha": None, "texto": "más mV = más seco"},
]
EMB = np.array([[1, 0, 0], [0, 1, 0], [0.8, 0.6, 0], [0, 0, 1]], dtype=np.float32)


@pytest.fixture
def ruta(tmp_path):
    (tmp_path / "chunks.jsonl").write_text("\n".join(json.dumps(c) for c in CHUNKS) + "\n")
    np.save(tmp_path / "embeddings.npy", EMB)
    (tmp_path / "meta.json").write_text(json.dumps(
        {"modelo_embed": "emb-test", "dim": 3, "n_por_fuente": {"ciencia": 2}}))
    return tmp_path


def embedder(vector):
    llamadas = []

    def f(texto, modelo, dim):
        llamadas.append((texto, modelo, dim))
        return vector
    f.llamadas = llamadas
    return f


def test_top_k_por_coseno(ruta):
    idx = recuperar.cargar_indice(ruta)
    emb = embedder([2.0, 0.0, 0.0])                       # sin normalizar a propósito
    r = recuperar.buscar("¿cuándo regar?", k=2, indice=idx, embedder=emb)
    assert [f.id for f in r] == ["ciencia/riego#0", "historial/2026-10-20"]
    assert r[0].score == pytest.approx(1.0) and r[1].score == pytest.approx(0.8)
    assert r[0].url == "https://ejemplo.edu/riego" and r[1].fecha == "2026-10-20"
    # La consulta usa el modelo y la dimensión del índice, no la del entorno.
    assert emb.llamadas == [("¿cuándo regar?", "emb-test", 3)]


def test_filtra_por_fuente(ruta):
    idx = recuperar.cargar_indice(ruta)
    r = recuperar.buscar("x", k=5, fuentes={"ciencia"}, indice=idx, embedder=embedder([1, 0, 0]))
    assert [f.id for f in r] == ["ciencia/riego#0", "ciencia/luz#0"]
    assert recuperar.buscar("x", fuentes=set(), indice=idx, embedder=embedder([1, 0, 0])) == []


def test_sin_indice_devuelve_vacio(tmp_path, caplog):
    assert recuperar.cargar_indice(tmp_path / "no-existe") is None
    assert "sin fragmentos" in caplog.text


def test_indice_inconsistente(ruta):
    np.save(ruta / "embeddings.npy", EMB[:2])
    assert recuperar.cargar_indice(ruta) is None


def test_dimension_distinta_no_rompe(ruta):
    idx = recuperar.cargar_indice(ruta)
    assert recuperar.buscar("x", indice=idx, embedder=embedder([1.0, 0.0])) == []
