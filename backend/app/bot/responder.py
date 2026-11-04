"""Punto de entrada único para contestar (docs/ENTREGA3.md §3).

    respuesta = await responder(texto, chat_id, db)

Lo usan el handler de Telegram, los tests y la evaluación (§7), sin Telegram de
por medio. Flujo: guardrail → (fuera de dominio: rechazo fijo, sin generar) →
contexto SQL → fragmentos del índice según la intención → prompt → Gemini →
memoria corta → log en `conversaciones` (D9).

Las dependencias externas (Gemini, búsqueda, reloj, memoria) se pueden
inyectar; por defecto se crean una vez por proceso. Los comandos (`/start`,
`/estado`, ...) también pasan por acá (`comando`) para que toda respuesta
quede logueada.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..models import ChatTelegram, Conversacion
from . import avisos, contexto, dominio, persona, prompt, recuperar
from .gemini import ErrorGemini, SinCupo

log = logging.getLogger("ruperto")

K_FRAGMENTOS = 5
SIN_LLM = "sin-llm"


@dataclass
class Respuesta:
    texto: str
    en_dominio: bool | None
    intencion: str | None
    fragmentos: list[tuple[str, float]] = field(default_factory=list)   # (id, score)
    citados: list[str] = field(default_factory=list)                    # ids marcados con [n]
    modelo: str | None = None
    latencia_ms: int = 0
    error: str | None = None


_gemini = None
_memoria = prompt.Memoria(desde_db=True)
# Una repregunta corta ("¿y eso cuándo fue?") se busca junto con la anterior (D218).
PALABRAS_REPREGUNTA = 10
# Para preguntas sobre el pasado o el estado, además de lo parecido entran los
# episodios etiquetados más recientes: la búsqueda semántica no sabe de "lo último".
EPISODIOS_RECIENTES = 3
INTENCIONES_CON_RECIENTES = {"estado", "historial", "riego"}


def _gemini_default():
    global _gemini
    if _gemini is None:
        from .gemini import ClienteGemini
        _gemini = ClienteGemini()
        recuperar.configurar(embedder=_gemini.embeber_consulta)
    return _gemini


def _loguear(db: Session, chat_id: int, pregunta: str, r: Respuesta) -> None:
    try:
        db.add(Conversacion(chat_id=chat_id, pregunta=pregunta, en_dominio=r.en_dominio,
                            intencion=r.intencion,
                            fragmentos=[{"id": i, "score": s, "citado": i in r.citados}
                                        for i, s in r.fragmentos],
                            respuesta=r.texto, modelo=r.modelo, latencia_ms=r.latencia_ms,
                            error=r.error))
        db.commit()
    except Exception:
        db.rollback()
        log.exception("no se pudo loguear la conversación de %s", chat_id)


async def responder(texto: str, chat_id: int, db: Session, *, gemini=None,
                    buscar: Callable[..., list[recuperar.Fragmento]] | None = None,
                    ahora: datetime | None = None,
                    memoria: prompt.Memoria | None = None) -> Respuesta:
    t0 = time.perf_counter()
    gemini = gemini or _gemini_default()
    buscar = buscar or recuperar.buscar
    memoria = memoria if memoria is not None else _memoria
    r = Respuesta(texto="", en_dominio=None, intencion=None, modelo=getattr(gemini, "modelo", None))
    try:
        if memoria.desde_db and memoria.vacia(chat_id):
            _recordar(db, memoria, chat_id)
        anterior = memoria.ultimo_intercambio(chat_id)
        c = await dominio.clasificar(texto, gemini, anterior)
        r.en_dominio, r.intencion = c.en_dominio, c.intencion
        if not c.en_dominio:
            r.texto = persona.rechazo()   # el generador no se llama
            r.modelo = getattr(gemini, "modelo_guardrail", r.modelo)
        else:
            ctx = contexto.armar_contexto(db, ahora=ahora)
            fuentes = dominio.fuentes_para(c.intencion)
            frags: list[recuperar.Fragmento] = []
            consulta = texto
            if anterior and len(texto.split()) <= PALABRAS_REPREGUNTA:
                consulta = f"{anterior[0]} {texto}"
            if fuentes is None or fuentes:
                try:
                    frags = await asyncio.to_thread(buscar, consulta, K_FRAGMENTOS, fuentes)
                except Exception:
                    log.exception("falló la búsqueda en el índice; sigo sin fragmentos")
            if c.intencion in INTENCIONES_CON_RECIENTES:
                hoy = ctx.ahora.astimezone(contexto.ZONA).date().isoformat()
                ya = {f.id for f in frags}
                frags += [f for f in recuperar.recientes("historial/episodio", EPISODIOS_RECIENTES, hoy)
                          if f.id not in ya]
            frags = prompt.solo_pasado(frags, ctx.ahora)
            r.fragmentos = [(f.id, f.score) for f in frags]
            turno = prompt.turno_usuario(contexto.texto_estado(ctx), contexto.texto_dias(ctx),
                                         frags, texto, simple=contexto.texto_simple(ctx))
            crudo = await gemini.generar(prompt.system(), prompt.contenidos(memoria, chat_id, turno))
            r.modelo = getattr(gemini, "ultimo_modelo", None) or r.modelo
            r.texto, citados = prompt.citas(prompt.sin_rotulos(crudo), frags)
            r.citados = [frags[i].id for i in sorted(citados)]
            # Sin marcas ni pie: los [n] de un turno viejo no apuntan a los fragmentos de ahora.
            memoria.agregar(chat_id, texto, prompt.citas(crudo, [])[0])
    except SinCupo as e:
        r.texto, r.error = persona.SIN_ALIENTO, f"429: {e}"[:500]
    except ErrorGemini as e:
        r.texto, r.error = persona.ERROR, str(e)[:500]
    except Exception as e:
        log.exception("error respondiendo a %s", chat_id)
        db.rollback()
        r.texto, r.error = persona.ERROR, f"{type(e).__name__}: {e}"[:500]
    r.latencia_ms = int((time.perf_counter() - t0) * 1000)
    _loguear(db, chat_id, texto, r)
    return r


def _recordar(db: Session, memoria: prompt.Memoria, chat_id: int) -> None:
    """Rearma la memoria de un chat desde `conversaciones` (después de un
    redeploy la del proceso arranca vacía). Sólo lo vigente y lo que salió bien."""
    try:
        limite = datetime.now(UTC) - memoria.VIGENCIA
        filas = (db.query(Conversacion)
                 .filter(Conversacion.chat_id == chat_id, Conversacion.ts >= limite,
                         Conversacion.error.is_(None), Conversacion.en_dominio.is_(True))
                 .order_by(Conversacion.ts.desc()).limit(memoria.turnos).all())
    except Exception:
        db.rollback()
        log.exception("no se pudo rearmar la memoria de %s", chat_id)
        return
    for f in reversed(filas):
        ts = f.ts if f.ts.tzinfo else f.ts.replace(tzinfo=UTC)
        memoria.agregar(chat_id, f.pregunta, prompt.citas(f.respuesta or "", [])[0], ts=ts)


# ─── comandos (§5.4) ──────────────────────────────────────────────────────
def suscribir(db: Session, chat_id: int, usuario: str | None, suscripto: bool) -> None:
    chat = db.get(ChatTelegram, chat_id)
    if chat is None:
        db.add(ChatTelegram(chat_id=chat_id, usuario=usuario, suscripto=suscripto))
    else:
        chat.suscripto = suscripto
        if usuario:
            chat.usuario = usuario
    db.commit()


async def comando(nombre: str, chat_id: int, db: Session, usuario: str | None = None,
                  ahora: datetime | None = None) -> Respuesta:
    """`/start`, `/silencio`, `/estado`, `/riego`, `/ayuda`. Sin LLM: textos
    fijos o armados desde el contexto, así funcionan aunque Gemini no tenga
    cupo. Se loguean igual (modelo = "sin-llm")."""
    t0 = time.perf_counter()
    r = Respuesta(texto="", en_dominio=True, intencion=None, modelo=SIN_LLM)
    try:
        if nombre == "start":
            suscribir(db, chat_id, usuario, True)
            r.texto, r.intencion = persona.BIENVENIDA, "saludo"
        elif nombre == "silencio":
            suscribir(db, chat_id, usuario, False)
            r.texto, r.intencion = persona.SILENCIO, "otro"
        elif nombre == "estado":
            r.texto = avisos.texto_medicion(contexto.armar_contexto(db, ahora=ahora))
            r.intencion = "estado"
            _memoria.agregar(chat_id, "/estado (cómo estás)", r.texto)
        elif nombre == "riego":
            r.texto = avisos.texto_riego(contexto.armar_contexto(db, ahora=ahora))
            r.intencion = "riego"
            _memoria.agregar(chat_id, "/riego (necesitás agua)", r.texto)
        else:
            r.texto, r.intencion = persona.AYUDA, "otro"
    except Exception as e:
        log.exception("error en /%s de %s", nombre, chat_id)
        db.rollback()
        r.texto, r.error = persona.ERROR, f"{type(e).__name__}: {e}"[:500]
    r.latencia_ms = int((time.perf_counter() - t0) * 1000)
    _loguear(db, chat_id, f"/{nombre}", r)
    return r
