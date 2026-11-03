"""Cliente de Gemini del bot (docs/ENTREGA3.md D10).

Los modelos salen del entorno (`GEMINI_MODELO`, `GEMINI_MODELO_EMBED`): los del
plan gratuito cambian seguido y cambiar uno no puede requerir un commit. Los
errores se traducen a dos excepciones propias para que el resto del bot no
dependa de `google.genai`: `SinCupo` (429, Ruperto contesta en personaje) y
`ErrorGemini` (cualquier otra falla).

Los tests no usan esta clase: le pasan a `responder` un falso con la misma
interfaz (`clasificar`, `generar`, `embeber_consulta`, `modelo`).
"""
from __future__ import annotations

import logging
import os
from typing import TypeVar

from pydantic import BaseModel

log = logging.getLogger("ruperto.gemini")

MODELO_DEFAULT = "gemini-3-flash-preview"      # mismo default que app/routers/analisis.py
MODELO_EMBED_DEFAULT = "gemini-embedding-001"

T = TypeVar("T", bound=BaseModel)


class ErrorGemini(Exception):
    """Gemini falló (5xx, respuesta vacía o ilegible, 4xx que no es 429)."""


class SinCupo(ErrorGemini):
    """429 del plan gratuito: hay que esperar, no es un bug."""


class ClienteGemini:
    def __init__(self, api_key: str | None = None, modelo: str | None = None,
                 modelo_embed: str | None = None):
        from google import genai

        self.modelo = modelo or os.getenv("GEMINI_MODELO") or MODELO_DEFAULT
        self.modelo_embed = modelo_embed or os.getenv("GEMINI_MODELO_EMBED") or MODELO_EMBED_DEFAULT
        self._client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])

    @staticmethod
    def _traducir(e: Exception) -> ErrorGemini:
        from google.genai import errors as genai_errors

        if isinstance(e, genai_errors.ClientError) and e.code == 429:
            log.warning("Gemini 429: %s", e.message)
            return SinCupo(str(e.message))
        if isinstance(e, genai_errors.APIError):
            log.warning("Gemini %s: %s", e.code, e.message)
            return ErrorGemini(f"Gemini respondió {e.code}")
        log.exception("error inesperado llamando a Gemini")
        return ErrorGemini(type(e).__name__)

    async def clasificar(self, prompt: str, esquema: type[T]) -> T:
        """Llamada corta con salida estructurada (el guardrail, §5.2)."""
        from google.genai import types

        try:
            r = await self._client.aio.models.generate_content(
                model=self.modelo,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=esquema,
                    temperature=0.0,
                    max_output_tokens=200,
                ),
            )
        except Exception as e:
            raise self._traducir(e) from e
        if isinstance(r.parsed, esquema):
            return r.parsed
        try:
            return esquema.model_validate_json(r.text or "")
        except Exception as e:
            raise ErrorGemini("salida estructurada ilegible") from e

    async def generar(self, system: str, contenidos: list[dict]) -> str:
        """Generación de la respuesta. `contenidos`: [{"role": "user"|"model", "text": ...}]."""
        from google.genai import types

        contents = [types.Content(role=c["role"], parts=[types.Part(text=c["text"])])
                    for c in contenidos]
        try:
            r = await self._client.aio.models.generate_content(
                model=self.modelo,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=system, temperature=0.7),
            )
        except Exception as e:
            raise self._traducir(e) from e
        texto = (r.text or "").strip()
        if not texto:
            raise ErrorGemini("respuesta vacía")
        return texto

    def embeber_consulta(self, texto: str, modelo: str, dim: int) -> list[float]:
        """Embedding de una consulta (task_type de consulta, D4). Sincrónico:
        `recuperar.buscar` tiene interfaz sincrónica y `responder` lo corre en
        un hilo."""
        from google.genai import types

        try:
            r = self._client.models.embed_content(
                model=modelo,
                contents=texto,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY",
                                                output_dimensionality=dim),
            )
        except Exception as e:
            raise self._traducir(e) from e
        return list(r.embeddings[0].values)
