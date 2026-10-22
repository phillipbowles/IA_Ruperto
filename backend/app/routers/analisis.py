import base64
import logging
import os
from typing import Literal

import anthropic
from fastapi import APIRouter, HTTPException, Query, Request
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from PIL import UnidentifiedImageError
from pydantic import BaseModel

from .. import vision
from ..schemas import AnalisisFotoOut

router = APIRouter(prefix="/api/v1/analisis-foto", tags=["analisis"])
log = logging.getLogger("uvicorn.error")

MODELO_CLAUDE = "claude-opus-5-5"
# Override con GEMINI_MODELO: los modelos de Gemini disponibles en el plan
# gratuito cambian seguido (gemini-2.5-flash ya no se habilita a cuentas nuevas).
MODELO_GEMINI = os.getenv("GEMINI_MODELO", "gemini-3-flash-preview")
TIPOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Mismas tres clases que el clasificador de la placa (CLAUDE.md). El puntaje
# manda: el estado se deriva de él con estos cortes, así la aguja del medidor
# y la etiqueta nunca se contradicen.
CORTE_ESTRESADA = 67
CORTE_MARCHITA = 34

PROMPT = f"""Sos un asistente botánico. La foto debería mostrar un lirio de paz \
(Spathiphyllum) en maceta. Evaluá su estado hídrico mirando SOLO la postura:

- Hojas: ¿están firmes y erguidas, empiezan a ceder y arquearse, o cuelgan \
sobre el borde de la maceta?
- Flores (espatas blancas): ¿están erguidas, inclinadas, o caídas? Si no hay \
flores visibles, decilo y basate en las hojas.

Devolvé un puntaje de turgencia de 0 a 100:
- {CORTE_ESTRESADA}–100: turgente (saludable). Hojas firmes, espata arriba.
- {CORTE_MARCHITA}–{CORTE_ESTRESADA - 1}: marchitez transitoria (estresada). \
Las hojas empiezan a ceder, la flor se inclina.
- 0–{CORTE_MARCHITA - 1}: marchitez franca (marchita). Hojas caídas sobre la maceta.

No juzgues por el color, las manchas ni el fondo: sólo cuánto están caídas las \
hojas y las flores. Si la foto no muestra una planta, poné es_planta en false. \
Escribí las descripciones en español, en una o dos oraciones cada una."""


class _Respuesta(BaseModel):
    es_planta: bool
    puntaje: int
    hojas: str
    flores: str
    explicacion: str


def _estado(puntaje: int) -> Literal["saludable", "estresada", "marchita"]:
    if puntaje >= CORTE_ESTRESADA:
        return "saludable"
    if puntaje >= CORTE_MARCHITA:
        return "estresada"
    return "marchita"


def _proveedor() -> Literal["gemini", "anthropic"] | None:
    """IA_PROVEEDOR fuerza uno; si no, Gemini (tiene plan gratuito) y después
    Claude, según qué clave esté cargada."""
    elegido = os.getenv("IA_PROVEEDOR", "").lower()
    if elegido in ("gemini", "anthropic"):
        return elegido
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


@router.post("", response_model=AnalisisFotoOut)
async def analizar_foto(
    request: Request,
    metodo: Literal["ia", "vision"] = Query(
        default="ia", description="ia = Gemini o Claude; vision = visión por computadora clásica"
    ),
):
    proveedor = _proveedor() if metodo == "ia" else None
    if metodo == "ia" and proveedor is None:
        raise HTTPException(status_code=503, detail="El análisis con IA no está configurado")

    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type not in TIPOS:
        raise HTTPException(status_code=415, detail="Se requiere una imagen JPEG, PNG, WebP o GIF")

    max_bytes = int(os.getenv("MAX_ANALISIS_BYTES", "5242880"))
    contenido = bytearray()
    async for chunk in request.stream():
        contenido.extend(chunk)
        if len(contenido) > max_bytes:
            raise HTTPException(status_code=413, detail="La imagen supera el tamano permitido")
    if not contenido:
        raise HTTPException(status_code=400, detail="La imagen esta vacia")

    if metodo == "vision":
        return _con_vision(bytes(contenido))

    if proveedor == "gemini":
        r, modelo = await _con_gemini(bytes(contenido), content_type)
    else:
        r, modelo = await _con_claude(bytes(contenido), content_type)

    puntaje = max(0, min(100, r.puntaje))
    return AnalisisFotoOut(
        es_planta=r.es_planta,
        estado=_estado(puntaje) if r.es_planta else None,
        puntaje=puntaje if r.es_planta else None,
        hojas=r.hojas,
        flores=r.flores,
        explicacion=r.explicacion,
        metodo="ia",
        modelo=modelo,
    )


async def _con_gemini(datos: bytes, content_type: str) -> tuple[_Respuesta, str]:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    try:
        respuesta = await client.aio.models.generate_content(
            model=MODELO_GEMINI,
            contents=[genai_types.Part.from_bytes(data=datos, mime_type=content_type), PROMPT],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=_Respuesta
            ),
        )
    except genai_errors.ClientError as e:
        log.warning("analisis-foto: %s de Gemini: %s", e.code, e.message)
        if e.code == 429:
            # Plan gratuito: pocos pedidos por minuto.
            raise HTTPException(status_code=429, detail="Se alcanzó el límite gratuito de Gemini: probá en un minuto")
        raise HTTPException(status_code=502, detail=f"Gemini respondió {e.code}")
    except genai_errors.ServerError as e:
        log.warning("analisis-foto: %s de Gemini: %s", e.code, e.message)
        raise HTTPException(status_code=503, detail="Gemini está saturado en este momento: probá de nuevo")

    if not isinstance(respuesta.parsed, _Respuesta):
        raise HTTPException(status_code=502, detail="La IA no pudo analizar esta imagen")
    return respuesta.parsed, MODELO_GEMINI


async def _con_claude(datos: bytes, content_type: str) -> tuple[_Respuesta, str]:
    imagen = base64.standard_b64encode(datos).decode("ascii")
    client = anthropic.AsyncAnthropic()
    try:
        respuesta = await client.messages.parse(
            model=MODELO_CLAUDE,
            max_tokens=16000,
            output_config={"effort": "medium"},
            output_format=_Respuesta,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": content_type, "data": imagen}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
            # Si un clasificador de seguridad rechaza el pedido, la API lo
            # reintenta sola en el modelo de respaldo que corresponda.
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"fallbacks": "default"},
        )
    except anthropic.RateLimitError as e:
        log.warning("analisis-foto: 429 de Anthropic (%s): %s", e.request_id, e.message)
        # Un límite momentáneo trae retry-after; sin él suele ser la cuenta sin
        # crédito o con el tope de gasto en 0.
        if e.response.headers.get("retry-after"):
            raise HTTPException(status_code=429, detail="Demasiados análisis seguidos, probá en un minuto")
        raise HTTPException(
            status_code=503,
            detail="La cuenta de la API de Anthropic no tiene cupo: revisá el crédito y los límites en la Consola",
        )
    except anthropic.APIStatusError as e:
        log.warning("analisis-foto: %s de Anthropic (%s): %s", e.status_code, e.request_id, e.message)
        raise HTTPException(status_code=502, detail=f"La IA respondió {e.status_code}")
    except anthropic.APIConnectionError:
        log.warning("analisis-foto: sin conexión con Anthropic")
        raise HTTPException(status_code=502, detail="No se pudo contactar a la IA")

    if respuesta.stop_reason == "refusal" or respuesta.parsed_output is None:
        raise HTTPException(status_code=502, detail="La IA no pudo analizar esta imagen")
    return respuesta.parsed_output, respuesta.model


def _con_vision(datos: bytes) -> AnalisisFotoOut:
    try:
        v = vision.analizar(datos)
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="No se pudo leer la imagen")
    return AnalisisFotoOut(
        es_planta=v.es_planta,
        estado=_estado(v.puntaje) if v.puntaje is not None else None,
        puntaje=v.puntaje,
        hojas=v.hojas,
        flores=v.flores,
        explicacion=v.explicacion,
        metodo="vision",
        modelo="vision-clasica-v1",
        metricas=v.metricas,
    )
