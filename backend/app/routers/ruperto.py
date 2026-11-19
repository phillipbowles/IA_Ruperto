"""«Hablar con Ruperto»: la planta que escucha y contesta en voz alta
(docs/ENTREGA3.md D219–D223).

    GET  /api/v1/ruperto/estado   cómo está y qué puede hacer (voz, chat). Sin LLM.
    POST /api/v1/ruperto/hablar   audio crudo (webm/ogg/mp4) → {pregunta, respuesta, audio}
    POST /api/v1/ruperto/mensaje  {"texto": ...}             → lo mismo, sin micrófono
    GET  /api/v1/ruperto/frase/…  audio de un texto fijo (saludo, cosquillas)

Es el mismo `responder` del bot de Telegram (guardrail, RAG, log en
`conversaciones`) con ElevenLabs por fuera: si la voz falla, la respuesta en
texto sale igual y el front la lee con la voz del navegador.

El front es público y cada charla gasta cupo de Gemini y créditos de
ElevenLabs. Tres frenos, de menor a mayor: un límite por IP (reparte entre
visitantes honestos, pero la IP sale de una cabecera y se puede falsear), un
tope global de charlas por minuto y por día (ese no se puede esquivar) y los
topes diarios de caracteres y de audios de `voz.py`. Todos viven en la memoria
del proceso: un redeploy los pone en cero.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..bot import avisos, contexto, persona, voz
from ..database import get_db

router = APIRouter(prefix="/api/v1/ruperto", tags=["ruperto"])
log = logging.getLogger("uvicorn.error")

TIPOS_AUDIO = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav",
               "audio/aac", "video/webm", "video/mp4"}
MAX_TEXTO = 400
# Los chats de la web no tienen chat_id de Telegram: se deriva uno de la sesión
# del navegador, en un rango que Telegram no usa (sus ids negativos son de
# grupos y llegan hasta ~ -1,1e12). Así `conversaciones` no necesita otra columna.
BASE_CHAT_WEB = 10**15
POR_MINUTO_DEFAULT = 8
POR_HORA_DEFAULT = 60
GLOBAL_POR_MINUTO_DEFAULT = 30
GLOBAL_POR_DIA_DEFAULT = 600
MAX_BYTES_AUDIO_WEB = 1_500_000     # 20 s de micrófono pesan < 400 kB en cualquier navegador

_pedidos: dict[str, deque[float]] = defaultdict(deque)
_todos: deque[float] = deque()      # todas las charlas del proceso, de cualquier IP


def chat_id_web(sesion: str | None, ip: str) -> int:
    """Id estable (y negativo) de una sesión del navegador; sin sesión, de la IP."""
    h = int(hashlib.sha256((sesion or f"ip:{ip}").encode()).hexdigest()[:14], 16)
    return -(BASE_CHAT_WEB + h % BASE_CHAT_WEB)


def es_chat_web(chat_id: int) -> bool:
    return chat_id <= -BASE_CHAT_WEB


def _ip(request: Request) -> str:
    # Detrás del nginx del front y del edge de Railway: el cliente es el primero.
    xff = request.headers.get("x-forwarded-for", "")
    return (xff.split(",")[0].strip() or request.headers.get("x-real-ip", "")
            or (request.client.host if request.client else "?"))


def limitar(request: Request) -> str:
    """Límite por IP (ventana deslizante en memoria del proceso). Devuelve la IP."""
    ip = _ip(request)
    por_minuto = int(os.getenv("RUPERTO_WEB_POR_MINUTO") or POR_MINUTO_DEFAULT)
    por_hora = int(os.getenv("RUPERTO_WEB_POR_HORA") or POR_HORA_DEFAULT)
    ahora = time.monotonic()
    while _todos and ahora - _todos[0] > 86400:
        _todos.popleft()
    if len(_todos) >= int(os.getenv("RUPERTO_WEB_GLOBAL_POR_DIA") or GLOBAL_POR_DIA_DEFAULT):
        raise HTTPException(status_code=429, detail="Ruperto habló demasiado por hoy: volvé mañana")
    if (sum(1 for t in _todos if ahora - t <= 60)
            >= int(os.getenv("RUPERTO_WEB_GLOBAL_POR_MINUTO") or GLOBAL_POR_MINUTO_DEFAULT)):
        raise HTTPException(status_code=429, detail="Hay mucha gente hablándole a Ruperto: probá en un minuto")
    cola = _pedidos[ip]
    while cola and ahora - cola[0] > 3600:
        cola.popleft()
    if len(cola) >= por_hora or sum(1 for t in cola if ahora - t <= 60) >= por_minuto:
        raise HTTPException(status_code=429, detail="Ruperto necesita un respiro: probá en un minuto")
    cola.append(ahora)
    _todos.append(ahora)
    if len(_pedidos) > 5000:            # no crecer sin límite con IPs que no vuelven
        for k in [k for k, v in _pedidos.items() if not v or ahora - v[-1] > 3600]:
            del _pedidos[k]
    return ip


def _voz() -> voz.ClienteVoz | None:
    try:
        c = voz.cliente() if voz.configurada() else None
    except voz.ErrorVoz:
        return None
    # Sin créditos o con la clave rechazada, por un rato es como no tener voz.
    return c if c is not None and c.disponible else None


def _con_chat() -> bool:
    return bool((os.getenv("GEMINI_API_KEY_VOZ") or os.getenv("GEMINI_API_KEY") or "").strip())


def _estado(db: Session) -> tuple[str | None, bool, contexto.Contexto]:
    ctx = contexto.armar_contexto(db)
    return avisos._clase(ctx), ctx.sensores_caidos, ctx


class EstadoOut(BaseModel):
    nombre: str = persona.NOMBRE
    estado: str | None            # saludable | estresada | marchita | None (sin dato)
    sensores_caidos: bool
    edad_min: int | None
    tierra: str | None            # húmeda / secándose / muy seca
    temperatura_c: float | None
    humedad_pct: float | None
    h_desde_riego: float | None
    voz: bool                     # hay ElevenLabs: oye y habla el servidor
    chat: bool                    # hay Gemini: puede contestar
    saludo: str


class CharlaOut(BaseModel):
    pregunta: str
    respuesta: str
    estado: str | None
    en_dominio: bool | None = None
    intencion: str | None = None
    audio_b64: str | None = None
    audio_mime: str | None = None
    # Por qué no hay audio o no se entendió: sin-voz | sin-creditos | no-se-entendio | error: …
    error_voz: str | None = None
    error: str | None = None
    latencia_ms: int = 0


class MensajeIn(BaseModel):
    texto: str = Field(min_length=1, max_length=MAX_TEXTO)
    con_audio: bool = True


@router.get("/estado", response_model=EstadoOut)
def estado(db: Session = Depends(get_db)):
    clase, caidos, ctx = _estado(db)
    u = ctx.ultima
    return EstadoOut(
        estado=None if caidos else clase, sensores_caidos=caidos,
        edad_min=u.edad_min if u else None,
        tierra=contexto.tierra_simple(u.suelo_mv) if u and u.suelo_mv is not None else None,
        temperatura_c=u.temp_c if u else None, humedad_pct=u.hum_pct if u else None,
        h_desde_riego=round(ctx.h_desde_riego, 1) if ctx.ultimo_riego else None,
        voz=_voz() is not None, chat=_con_chat(), saludo=persona.SALUDO_VOZ)


async def _leer_audio(request: Request) -> tuple[bytes, str]:
    tipo = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if tipo not in TIPOS_AUDIO:
        raise HTTPException(status_code=415, detail="Se requiere un audio (webm, ogg, mp4, mp3 o wav)")
    datos = bytearray()
    async for chunk in request.stream():
        datos.extend(chunk)
        if len(datos) > MAX_BYTES_AUDIO_WEB:
            raise HTTPException(status_code=413, detail="El audio es demasiado largo")
    if not datos:
        raise HTTPException(status_code=400, detail="El audio está vacío")
    return bytes(datos), tipo


def _salida(c: voz.Charla, estado_ahora: str | None, t0: float) -> CharlaOut:
    r = c.respuesta
    return CharlaOut(
        pregunta=c.pregunta, respuesta=c.texto, estado=estado_ahora,
        en_dominio=r.en_dominio if r else None, intencion=r.intencion if r else None,
        audio_b64=base64.b64encode(c.audio).decode() if c.audio else None,
        audio_mime=c.audio_mime, error_voz=c.error_voz, error=r.error if r else None,
        latencia_ms=int((time.perf_counter() - t0) * 1000))


def _estado_seguro(db: Session) -> str | None:
    try:
        clase, caidos, _ = _estado(db)
        return None if caidos else clase
    except Exception:
        db.rollback()
        log.exception("ruperto: no se pudo armar el estado")
        return None


@router.post("/hablar", response_model=CharlaOut)
async def hablar(request: Request, db: Session = Depends(get_db),
                 x_ruperto_sesion: str | None = Header(None)):
    """Audio del micrófono → lo que se entendió, la respuesta y su audio."""
    cliente = _voz()
    if cliente is None:
        raise HTTPException(status_code=503, detail="La voz no está disponible ahora (sin configurar o sin créditos)")
    if not _con_chat():
        raise HTTPException(status_code=503, detail="Ruperto no puede contestar (falta GEMINI_API_KEY)")
    ip = limitar(request)
    audio, tipo = await _leer_audio(request)
    t0 = time.perf_counter()
    chat_id = chat_id_web(x_ruperto_sesion, ip)
    c = await voz.conversar(audio, tipo, chat_id, db, voz=cliente)
    log.info("ruperto web %s: oír %d ms, hablar %d ms, voz=%s", chat_id, c.ms_oir, c.ms_hablar,
             c.error_voz or "ok")
    return _salida(c, _estado_seguro(db), t0)


@router.post("/mensaje", response_model=CharlaOut)
async def mensaje(cuerpo: MensajeIn, request: Request, db: Session = Depends(get_db),
                  x_ruperto_sesion: str | None = Header(None)):
    """Lo mismo que /hablar con la pregunta escrita (o transcripta por el navegador)."""
    if not _con_chat():
        raise HTTPException(status_code=503, detail="Ruperto no puede contestar (falta GEMINI_API_KEY)")
    texto = cuerpo.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El mensaje está vacío")
    ip = limitar(request)
    t0 = time.perf_counter()
    c = await voz.conversar(None, "", chat_id_web(x_ruperto_sesion, ip), db, texto=texto,
                            voz=_voz(), con_audio=cuerpo.con_audio)
    return _salida(c, _estado_seguro(db), t0)


FRASES = ("saludo", "cosquillas")


class FraseOut(BaseModel):
    texto: str
    audio_b64: str | None = None
    audio_mime: str | None = None


@router.get("/frase/{clave}", response_model=FraseOut)
async def frase(clave: str, n: int = 0, db: Session = Depends(get_db)):
    """Texto fijo de Ruperto (el saludo, o lo que dice cuando lo tocan) con su
    audio. El audio de cada frase se sintetiza una sola vez por proceso
    (`fijo=True`): tocarlo diez veces no gasta diez veces. Sin voz devuelve
    sólo el texto y el front lo lee con la voz del navegador."""
    if clave not in FRASES:
        raise HTTPException(status_code=404, detail="Esa frase no existe")
    if clave == "saludo":
        texto = persona.SALUDO_VOZ
    else:
        texto = persona.cosquillas(n, mal=_estado_seguro(db) == "marchita")
    cliente = _voz()
    audio = mime = None
    if cliente is not None:
        # Sin `limitar`: son siete frases y cada una se sintetiza una vez por
        # proceso, así que tocarlo no le saca pedidos a la charla.
        audio, mime, _ = await voz.hablar(texto, cliente, fijo=True)
    return FraseOut(texto=texto, audio_b64=base64.b64encode(audio).decode() if audio else None,
                    audio_mime=mime)
