"""Arma el índice del RAG de Ruperto — contrato en docs/ENTREGA3.md §4.

    python -m rag.construir_indice                     # snapshot más nuevo de data/
    python -m rag.construir_indice --env-file ../.env  # clave desde un .env
    python -m rag.construir_indice --solo-chunks       # sin red: lista los chunks

Escribe en `backend/app/bot/indice/` (GENERADO, no se edita a mano):
`chunks.jsonl`, `embeddings.npy` (float32 [n, d], filas de norma 1, mismo
orden que las líneas de chunks.jsonl) y `meta.json`.

Primero arma todos los chunks y todos los embeddings en memoria; recién si
todo salió bien escribe, en una carpeta temporal al lado que después
reemplaza a la vieja. Sin clave o con un error a mitad de camino no queda un
índice a medias.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

if __package__ in (None, ""):  # permite también `python rag/construir_indice.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag import CORPUS, INDICE, RAIZ  # noqa: E402
from rag.chunks import FUENTES, Chunk, chunks_corpus  # noqa: E402
from rag.embeber import Embedder, GeminiEmbedder, SinClave, leer_clave  # noqa: E402

MARCA = "por rag/construir_indice.py — no editar"


def snapshot_mas_nuevo(datos: Path = RAIZ / "data") -> Path:
    snaps = sorted(datos.glob("mediciones_raw_*.csv"))
    if not snaps:
        raise FileNotFoundError(f"no hay mediciones_raw_*.csv en {datos}")
    return snaps[-1]


def armar_chunks(snapshot: Path, corpus: Path = CORPUS,
                 episodios: Path = RAIZ / "data" / "episodios.csv") -> list[Chunk]:
    """ciencia, historial, proyecto — en ese orden; dentro de cada fuente, orden estable."""
    from rag.historial import chunks_historial

    out = chunks_corpus(corpus / "ciencia", "ciencia")
    out += chunks_historial(snapshot, episodios)
    out += chunks_corpus(corpus / "proyecto", "proyecto")
    ids = [c.id for c in out]
    if len(set(ids)) != len(ids):
        raise ValueError("ids de chunk repetidos")
    return out


def texto_a_embeber(c: Chunk) -> str:
    """Lo que se embebe: título + texto (el título da contexto a secciones sueltas)."""
    return f"{c.titulo}\n\n{c.texto}"


def hash_corpus(chunks: list[Chunk]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(json.dumps(c.dict(), ensure_ascii=False, sort_keys=True).encode())
        h.update(b"\n")
    return h.hexdigest()


def escribir_indice(chunks: list[Chunk], emb: np.ndarray, destino: Path, modelo: str,
                    snapshot: str, ahora: datetime | None = None) -> dict:
    """Escribe los tres archivos de forma atómica (carpeta temporal + reemplazo)."""
    emb = np.asarray(emb, dtype=np.float32)
    if emb.ndim != 2 or emb.shape[0] != len(chunks):
        raise ValueError(f"embeddings {emb.shape} no coinciden con {len(chunks)} chunks")
    if not np.allclose(np.linalg.norm(emb, axis=1), 1.0, atol=1e-4):
        raise ValueError("los embeddings tienen que venir normalizados")
    ahora = ahora or datetime.now(timezone.utc)
    meta = {
        "_generado": MARCA,
        "modelo_embed": modelo,
        "dim": int(emb.shape[1]),
        "task_type": "RETRIEVAL_DOCUMENT",
        "generado": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n": len(chunks),
        "n_por_fuente": {f: sum(c.fuente == f for c in chunks) for f in FUENTES},
        "snapshot": snapshot,
        "hash_corpus": hash_corpus(chunks),
    }
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    with open(tmp / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.dict(), ensure_ascii=False) + "\n")
    np.save(tmp / "embeddings.npy", emb)
    (tmp / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
    viejo = destino.with_name(destino.name + ".viejo")
    if viejo.exists():
        shutil.rmtree(viejo)
    if destino.exists():
        destino.rename(viejo)
    tmp.rename(destino)
    if viejo.exists():
        # Conserva lo que no es del índice (p. ej. un __init__.py), si lo hubiera.
        for p in viejo.iterdir():
            if p.name not in ("chunks.jsonl", "embeddings.npy", "meta.json") and not (destino / p.name).exists():
                p.rename(destino / p.name)
        shutil.rmtree(viejo)
    return meta


def construir(snapshot: Path, destino: Path, embedder: Embedder, corpus: Path = CORPUS,
              episodios: Path = RAIZ / "data" / "episodios.csv") -> dict:
    chunks = armar_chunks(snapshot, corpus, episodios)
    print(f"{len(chunks)} chunks; embebiendo con {embedder.modelo} (dim {embedder.dim})", flush=True)
    emb = embedder([texto_a_embeber(c) for c in chunks])
    return escribir_indice(chunks, emb, destino, embedder.modelo, Path(snapshot).name)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", type=Path, default=None,
                    help="CSV crudo de Railway (default: el mediciones_raw_*.csv más nuevo)")
    ap.add_argument("--destino", type=Path, default=INDICE)
    ap.add_argument("--env-file", type=Path, default=RAIZ / ".env",
                    help="si GEMINI_API_KEY no está en el entorno, se busca acá")
    ap.add_argument("--dim", type=int, default=None, help="dimensión del embedding (default 768)")
    ap.add_argument("--solo-chunks", action="store_true", help="no embebe ni escribe: lista los chunks")
    a = ap.parse_args(argv)

    snapshot = a.snapshot or snapshot_mas_nuevo()
    if a.solo_chunks:
        for c in armar_chunks(snapshot):
            print(f"{c.id:45s} {len(c.texto.split()):4d} palabras  {c.titulo[:60]}")
        return 0
    try:
        clave = leer_clave(a.env_file)
    except SinClave as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    emb = GeminiEmbedder(clave, **({"dim": a.dim} if a.dim else {}))
    meta = construir(snapshot, a.destino, emb)
    print(json.dumps({k: meta[k] for k in ("modelo_embed", "dim", "n", "n_por_fuente", "snapshot")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
