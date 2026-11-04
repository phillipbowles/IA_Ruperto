"""Recuperación top-k sobre el índice generado (docs/ENTREGA3.md §4, D4).

Lee `backend/app/bot/indice/` (lo genera `rag/construir_indice.py`; no se edita
a mano): `chunks.jsonl`, `embeddings.npy` (filas de norma 1) y `meta.json`.
Similitud coseno con numpy: son unos cientos de chunks.

La consulta se embebe con el **modelo y la dimensión del índice** (`meta.json`),
no con `GEMINI_MODELO_EMBED`: un vector de otro modelo no es comparable con los
del índice. Si difieren se avisa en el log.

Si el índice no existe o está roto, `buscar` devuelve `[]` y lo loguea una vez:
el bot sigue contestando con el estado en vivo, sin fragmentos.
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

log = logging.getLogger("ruperto.recuperar")

RUTA_INDICE = Path(__file__).with_name("indice")
FUENTES = {"ciencia", "historial", "proyecto"}

# (texto, modelo, dim) -> vector. En producción, ClienteGemini.embeber_consulta.
Embedder = Callable[[str, str, int], list[float]]


@dataclass(frozen=True)
class Fragmento:
    id: str
    fuente: str
    titulo: str
    url: str | None
    fecha: str | None
    texto: str
    score: float


@dataclass
class Indice:
    chunks: list[dict]
    emb: np.ndarray          # float32 [n, d], norma 1
    meta: dict

    @property
    def modelo_embed(self) -> str:
        return self.meta.get("modelo_embed", "gemini-embedding-001")

    @property
    def dim(self) -> int:
        return int(self.meta.get("dim", self.emb.shape[1]))


def cargar_indice(ruta: Path = RUTA_INDICE) -> Indice | None:
    """Lee el índice; None si falta o es inconsistente (y lo loguea)."""
    ruta = Path(ruta)
    archivos = [ruta / "chunks.jsonl", ruta / "embeddings.npy", ruta / "meta.json"]
    if not all(a.exists() for a in archivos):
        log.warning("no hay índice en %s: Ruperto contesta sin fragmentos", ruta)
        return None
    try:
        chunks = [json.loads(l) for l in archivos[0].read_text().splitlines() if l.strip()]
        emb = np.load(archivos[1]).astype(np.float32)
        meta = json.loads(archivos[2].read_text())
    except Exception:
        log.exception("índice ilegible en %s: Ruperto contesta sin fragmentos", ruta)
        return None
    if emb.ndim != 2 or len(chunks) != emb.shape[0]:
        log.error("índice inconsistente: %d chunks y embeddings %s", len(chunks), emb.shape)
        return None
    env = os.getenv("GEMINI_MODELO_EMBED")
    if env and env != meta.get("modelo_embed"):
        log.warning("GEMINI_MODELO_EMBED=%s pero el índice se hizo con %s: se usa el del índice",
                    env, meta.get("modelo_embed"))
    log.info("índice cargado: %d chunks, dim %d, %s", len(chunks), emb.shape[1],
             meta.get("n_por_fuente"))
    return Indice(chunks, emb, meta)


_indice: Indice | None = None
_cargado = False
_embedder: Embedder | None = None


def configurar(embedder: Embedder | None = None, indice: Indice | None = None) -> None:
    """Fija el embedder por defecto (lo llama el arranque del bot)."""
    global _embedder, _indice, _cargado
    if embedder is not None:
        _embedder = embedder
    if indice is not None:
        _indice, _cargado = indice, True


def _indice_default() -> Indice | None:
    global _indice, _cargado
    if not _cargado:
        _indice, _cargado = cargar_indice(), True
    return _indice


def buscar(consulta: str, k: int = 5, fuentes: set[str] | None = None, *,
           embedder: Embedder | None = None, indice: Indice | None = None) -> list[Fragmento]:
    """Top-k por coseno. `fuentes=None` busca en todas; un conjunto vacío no busca."""
    idx = indice if indice is not None else _indice_default()
    emb_fn = embedder or _embedder
    if idx is None or k <= 0 or (fuentes is not None and not fuentes):
        return []
    if emb_fn is None:
        log.warning("buscar sin embedder configurado: sin fragmentos")
        return []
    mascara = np.array([fuentes is None or c.get("fuente") in fuentes for c in idx.chunks])
    if not mascara.any():
        return []
    q = np.asarray(emb_fn(consulta, idx.modelo_embed, idx.dim), dtype=np.float32)
    if q.shape != (idx.emb.shape[1],):
        log.error("la consulta tiene dim %s y el índice %d: sin fragmentos", q.shape, idx.emb.shape[1])
        return []
    norma = float(np.linalg.norm(q))
    if norma == 0:
        return []
    scores = idx.emb @ (q / norma)
    scores[~mascara] = -np.inf
    orden = np.argsort(-scores, kind="stable")[: min(k, int(mascara.sum()))]
    return [
        Fragmento(id=c["id"], fuente=c.get("fuente", ""), titulo=c.get("titulo", ""),
                  url=c.get("url"), fecha=c.get("fecha"), texto=c.get("texto", ""),
                  score=round(float(scores[i]), 4))
        for i in orden
        for c in [idx.chunks[i]]
    ]
