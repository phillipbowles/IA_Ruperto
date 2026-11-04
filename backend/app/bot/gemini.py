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

import asyncio
import logging
import os
import time
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


def _pensar_poco(modelo: str):
    """Razonamiento bajo: el guardrail es una clasificación y la respuesta sale
    de un contexto ya armado; con el default, gemini-3 tardaba 9–30 s por
    respuesta (D213). `thinking_level` es de la familia gemini-3 y posteriores;
    en las anteriores se deja el default del modelo."""
    from google.genai import types

    if modelo.startswith(("gemini-3", "models/gemini-3")):
        return types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW)
    return None


REINTENTO_S = 2.0
SALTEO_SIN_CUPO_S = 3600


async def _llamar(fn):
    """Un reintento si Gemini está saturado (5xx): pasa seguido en el plan
    gratuito y a los pocos segundos suele andar (D216). Un 429 no se reintenta:
    es cupo, no carga."""
    from google.genai import errors as genai_errors

    try:
        return await fn()
    except genai_errors.ServerError as e:
        log.warning("Gemini %s, reintento en %.0f s", e.code, REINTENTO_S)
        await asyncio.sleep(REINTENTO_S)
        return await fn()


class ClienteGemini:
    def __init__(self, api_key: str | None = None, modelo: str | None = None,
                 modelo_embed: str | None = None):
        from google import genai

        # GEMINI_MODELO admite una lista separada por comas: si uno se queda sin
        # cupo (429) se responde con el siguiente. En el plan gratuito cada modelo
        # flash da 20 pedidos por día, así que la cadena suma cupo (D216).
        lista = modelo or os.getenv("GEMINI_MODELO") or MODELO_DEFAULT
        self.modelos = [m.strip() for m in lista.split(",") if m.strip()]
        self.modelo = self.modelos[0]
        self.ultimo_modelo: str | None = None      # el que respondió la última vez
        self._sin_cupo: dict[str, float] = {}      # modelo → hasta cuándo (monotonic) se saltea
        # El guardrail puede ir en otro modelo: clasificar no necesita el mismo
        # modelo que responder, y así no le gasta cupo (D216).
        self.modelo_guardrail = os.getenv("GEMINI_MODELO_GUARDRAIL") or self.modelo
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
            r = await _llamar(lambda: self._client.aio.models.generate_content(
                model=self.modelo_guardrail,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=esquema,
                    temperature=0.0,
                    # Sin max_output_tokens: en los modelos con razonamiento el
                    # tope cuenta también los tokens de "thinking" y con 200 la
                    # salida llegaba cortada (MAX_TOKENS, JSON vacío). Para una
                    # clasificación alcanza con razonar poco.
                    thinking_config=_pensar_poco(self.modelo_guardrail),
                ),
            ))
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
        ahora = time.monotonic()
        candidatos = [m for m in self.modelos if self._sin_cupo.get(m, 0) <= ahora] or self.modelos
        sin_cupo: SinCupo | None = None
        for m in candidatos:
            try:
                r = await _llamar(lambda m=m: self._client.aio.models.generate_content(
                    model=m,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=system, temperature=0.7,
                                                       thinking_config=_pensar_poco(m)),
                ))
            except Exception as e:
                err = self._traducir(e)
                if not isinstance(err, SinCupo):
                    raise err from e
                # Se saltea una hora: el cupo diario no vuelve antes, y probarlo
                # en cada pregunta sólo suma latencia.
                self._sin_cupo[m] = ahora + SALTEO_SIN_CUPO_S
                sin_cupo = err
                continue
            self.ultimo_modelo = m
            break
        else:
            raise sin_cupo or SinCupo("sin modelos con cupo")
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
