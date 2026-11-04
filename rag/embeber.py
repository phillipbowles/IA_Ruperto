"""Embeddings con Gemini (`google-genai`) para el índice — D4 y D10 de docs/ENTREGA3.md.

- Modelo por `GEMINI_MODELO_EMBED` (default `gemini-embedding-001`).
- `task_type` RETRIEVAL_DOCUMENT al indexar. Quien consulta (bot/recuperar.py)
  tiene que usar RETRIEVAL_QUERY, el mismo modelo y la misma dimensión
  (`meta.json` → `modelo_embed`, `dim`).
- Lotes chicos con pausa entre lotes y reintento con espera exponencial ante
  429 / RESOURCE_EXHAUSTED (plan gratuito).
- Las filas salen normalizadas a norma 1 (con dimensión < 3072 Gemini no
  las normaliza).
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Callable, Protocol, Sequence

import numpy as np

MODELO_DEFAULT = "gemini-embedding-001"
DIM_DEFAULT = 768
TAM_LOTE = 20
PAUSA_S = 1.0
REINTENTOS = 6


class SinClave(RuntimeError):
    pass


class Embedder(Protocol):
    modelo: str
    dim: int

    def __call__(self, textos: Sequence[str]) -> np.ndarray: ...


def normalizar(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=np.float32)
    n = np.linalg.norm(m, axis=1, keepdims=True)
    if (n == 0).any():
        raise ValueError("embedding con norma 0")
    return (m / n).astype(np.float32)


def leer_clave(env_file: Path | str | None = None) -> str:
    """GEMINI_API_KEY del entorno; si no está, de `env_file` (formato .env). Nunca se imprime."""
    clave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not clave and env_file and Path(env_file).is_file():
        for linea in Path(env_file).read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(?:export\s+)?GEMINI_API_KEY\s*=\s*(.*)$", linea)
            if m:
                clave = m.group(1).strip().strip('"').strip("'")
    if not clave:
        raise SinClave(
            "Falta GEMINI_API_KEY: exportala en el entorno o pasá --env-file con un .env "
            "que la tenga. No se escribió nada en el índice.")
    return clave


def _es_429(e: Exception) -> bool:
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    return code == 429 or "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e)[:20]


def con_reintentos(f: Callable[[], np.ndarray], reintentos: int = REINTENTOS,
                   espera_s: float = 5.0, dormir: Callable[[float], None] = time.sleep) -> np.ndarray:
    """Llama a `f`; ante un 429 espera (5, 10, 20, ... s) y reintenta. Otros errores suben."""
    for intento in range(reintentos + 1):
        try:
            return f()
        except Exception as e:  # noqa: BLE001 — se filtra abajo
            if not _es_429(e) or intento == reintentos:
                raise
            dormir(espera_s * 2 ** intento)
    raise AssertionError("inalcanzable")


class GeminiEmbedder:
    def __init__(self, clave: str, modelo: str | None = None, dim: int = DIM_DEFAULT,
                 tam_lote: int = TAM_LOTE, pausa_s: float = PAUSA_S):
        from google import genai  # import diferido: los tests no lo necesitan

        self._genai = genai
        self.cliente = genai.Client(api_key=clave)
        self.modelo = modelo or os.environ.get("GEMINI_MODELO_EMBED") or MODELO_DEFAULT
        self.dim = dim
        self.tam_lote = tam_lote
        self.pausa_s = pausa_s

    def _lote(self, textos: Sequence[str]) -> np.ndarray:
        from google.genai import types

        r = self.cliente.models.embed_content(
            model=self.modelo, contents=list(textos),
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT",
                                            output_dimensionality=self.dim))
        return np.array([e.values for e in r.embeddings], dtype=np.float32)

    def __call__(self, textos: Sequence[str]) -> np.ndarray:
        filas = []
        for i in range(0, len(textos), self.tam_lote):
            lote = textos[i:i + self.tam_lote]
            m = con_reintentos(lambda: self._lote(lote))
            if m.shape != (len(lote), self.dim):
                raise RuntimeError(f"Gemini devolvió {m.shape}, se esperaba ({len(lote)}, {self.dim})")
            filas.append(m)
            print(f"  embebidos {min(i + self.tam_lote, len(textos))}/{len(textos)}", flush=True)
            if i + self.tam_lote < len(textos):
                time.sleep(self.pausa_s)
        return normalizar(np.vstack(filas))


class EmbedderFalso:
    """Determinista y sin red, para tests: hash del texto → vector."""

    modelo = "falso"

    def __init__(self, dim: int = 16):
        self.dim = dim

    def __call__(self, textos: Sequence[str]) -> np.ndarray:
        import hashlib

        filas = []
        for t in textos:
            semilla = int.from_bytes(hashlib.sha256(t.encode()).digest()[:8], "little")
            filas.append(np.random.default_rng(semilla).normal(size=self.dim))
        return normalizar(np.array(filas))
