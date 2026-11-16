"""Envío de los avisos (docs/ENTREGA3.md §6, D7 opción a): el servicio del bot
lee la base y le escribe a cada chat suscripto. La ESP32 no habla con Telegram.

    medición cada 30 min  → texto_medicion
    riego, revisado c/5 min → debe_avisar_riego (el antirrebote de 6 h está ahí)

Sin LLM: funcionan con Gemini caído y no gastan cupo. El bot y la sesión se
inyectan para testear sin Telegram ni Postgres. Un error en un chat no corta a
los demás ni tira abajo el bucle.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session
from telegram.error import Forbidden

from ..database import SessionLocal
from ..models import ChatTelegram
from . import avisos
from .contexto import armar_contexto

log = logging.getLogger("ruperto.avisos")

CADA_RIEGO = timedelta(minutes=5)
CADA_MEDICION = timedelta(minutes=30)
MAX_MENSAJE = 4000


async def _mandar(bot, db: Session, chat: ChatTelegram, texto: str) -> bool:
    try:
        await bot.send_message(chat_id=chat.chat_id, text=texto[:MAX_MENSAJE])
        return True
    except Forbidden:
        # Bloqueó el bot: no insistir hasta que vuelva a mandar /start.
        log.info("chat %s bloqueó el bot: se desuscribe", chat.chat_id)
        chat.suscripto = False
        db.commit()
    except Exception:
        log.exception("no se pudo avisar a %s", chat.chat_id)
    return False


def _suscriptos(db: Session) -> list[ChatTelegram]:
    return db.query(ChatTelegram).filter(ChatTelegram.suscripto.is_(True)).all()


async def avisar_medicion(bot, db: Session, ahora: datetime | None = None) -> int:
    """Manda la medición a cada suscripto. Devuelve a cuántos llegó."""
    texto = avisos.texto_medicion(armar_contexto(db, ahora))
    return sum([await _mandar(bot, db, c, texto) for c in _suscriptos(db)])


async def avisar_riego(bot, db: Session, ahora: datetime | None = None) -> int:
    """Aviso de riego a los suscriptos que no lo recibieron hace poco."""
    ahora = ahora or datetime.now(UTC)
    ctx = armar_contexto(db, ahora)
    if not avisos.necesita_riego(ctx):
        return 0
    texto, n = avisos.texto_aviso_riego(ctx), 0
    for c in _suscriptos(db):
        ultimo = c.ultimo_aviso_riego
        if ultimo is not None and ultimo.tzinfo is None:      # SQLite no guarda la zona
            ultimo = ultimo.replace(tzinfo=UTC)
        if avisos.debe_avisar_riego(ctx, ultimo, ahora) and await _mandar(bot, db, c, texto):
            c.ultimo_aviso_riego = ahora
            db.commit()
            n += 1
    return n


async def bucle(bot, sesion: Callable[[], Session] = SessionLocal) -> None:
    """Revisa el riego cada 5 min y manda la medición cada 30 (la primera al
    arrancar). Corre como tarea de asyncio dentro de la Application."""
    ultima_medicion: datetime | None = None
    while True:
        ahora = datetime.now(UTC)
        try:
            with sesion() as db:
                if ultima_medicion is None or ahora - ultima_medicion >= CADA_MEDICION:
                    ultima_medicion = ahora
                    log.info("tick medición: %d chats", await avisar_medicion(bot, db, ahora))
                n = await avisar_riego(bot, db, ahora)
                if n:
                    log.info("tick riego: %d chats", n)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("falló un tick de avisos")
        await asyncio.sleep(CADA_RIEGO.total_seconds())
