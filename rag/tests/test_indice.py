import json

import numpy as np
import pytest

from rag import CORPUS
from rag import construir_indice as ci
from rag.chunks import Chunk
from rag.embeber import EmbedderFalso, SinClave, con_reintentos, leer_clave, normalizar


def _chunks(n=3):
    return [Chunk(f"ciencia/d#{i}", "ciencia", "T", "https://x", None, f"texto {i}") for i in range(n)]


def test_escribe_los_tres_archivos_en_orden(tmp_path):
    cs = _chunks()
    emb = EmbedderFalso(dim=8)
    m = emb([ci.texto_a_embeber(c) for c in cs])
    meta = ci.escribir_indice(cs, m, tmp_path / "indice", "falso", "snap.csv")
    d = tmp_path / "indice"
    lineas = [json.loads(x) for x in (d / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [x["id"] for x in lineas] == [c.id for c in cs]
    E = np.load(d / "embeddings.npy")
    assert E.dtype == np.float32 and E.shape == (3, 8)
    assert np.allclose(np.linalg.norm(E, axis=1), 1)
    # Fila i ↔ chunk i.
    for i, c in enumerate(cs):
        assert np.allclose(E[i], emb([ci.texto_a_embeber(c)])[0])
    disco = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    assert disco == meta
    assert disco["_generado"] == ci.MARCA
    assert {"modelo_embed", "dim", "generado", "n_por_fuente", "snapshot", "hash_corpus"} <= set(disco)
    assert disco["n_por_fuente"] == {"ciencia": 3, "historial": 0, "proyecto": 0}
    assert not (tmp_path / "indice.tmp").exists()


def test_rechaza_filas_que_no_coinciden_o_sin_normalizar(tmp_path):
    with pytest.raises(ValueError):
        ci.escribir_indice(_chunks(3), np.eye(2, dtype=np.float32), tmp_path / "i", "f", "s")
    with pytest.raises(ValueError):
        ci.escribir_indice(_chunks(2), np.full((2, 4), 3.0), tmp_path / "i", "f", "s")
    assert not (tmp_path / "i").exists()


def test_construir_completo_sin_red(tmp_path, snapshot_chico, episodios_chico):
    meta = ci.construir(snapshot_chico, tmp_path / "indice", EmbedderFalso(dim=8),
                        corpus=CORPUS, episodios=episodios_chico)
    n = meta["n_por_fuente"]
    assert n["historial"] == 4 and n["ciencia"] > 0 and n["proyecto"] > 0
    lineas = (tmp_path / "indice" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lineas) == meta["n"] == np.load(tmp_path / "indice" / "embeddings.npy").shape[0]
    # Mismo corpus → mismo hash (ids y textos estables).
    meta2 = ci.construir(snapshot_chico, tmp_path / "otro", EmbedderFalso(dim=8),
                         corpus=CORPUS, episodios=episodios_chico)
    assert meta2["hash_corpus"] == meta["hash_corpus"]


def test_error_a_mitad_no_toca_el_indice_existente(tmp_path, snapshot_chico, episodios_chico):
    destino = tmp_path / "indice"
    ci.escribir_indice(_chunks(), normalizar(np.ones((3, 4))), destino, "f", "s")
    antes = (destino / "chunks.jsonl").read_bytes()

    def roto(textos):
        raise RuntimeError("se cortó la red")
    roto.modelo, roto.dim = "x", 4
    with pytest.raises(RuntimeError):
        ci.construir(snapshot_chico, destino, roto, corpus=CORPUS, episodios=episodios_chico)
    assert (destino / "chunks.jsonl").read_bytes() == antes


def test_sin_clave_error_claro_y_no_escribe(tmp_path, monkeypatch, capsys, snapshot_chico):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SinClave, match="GEMINI_API_KEY"):
        leer_clave(tmp_path / "no-existe.env")
    destino = tmp_path / "indice"
    rc = ci.main(["--snapshot", str(snapshot_chico), "--destino", str(destino),
                  "--env-file", str(tmp_path / "no-existe.env")])
    assert rc == 2
    assert "GEMINI_API_KEY" in capsys.readouterr().err
    assert not destino.exists()


def test_clave_desde_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    f = tmp_path / ".env"
    f.write_text('OTRA=1\nGEMINI_API_KEY="abc123"\n')
    assert leer_clave(f) == "abc123"


def test_reintenta_ante_429():
    llamadas, esperas = [], []

    class Err(Exception):
        code = 429

    def f():
        llamadas.append(1)
        if len(llamadas) < 3:
            raise Err("RESOURCE_EXHAUSTED")
        return np.ones((1, 2))

    assert con_reintentos(f, dormir=esperas.append).shape == (1, 2)
    assert esperas == [5.0, 10.0]

    def g():
        raise ValueError("400 bad request")
    with pytest.raises(ValueError):
        con_reintentos(g, dormir=esperas.append)
