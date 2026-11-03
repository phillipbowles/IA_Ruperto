"""Handlers de Telegram (python-telegram-bot ≥ 21, polling). Finos a propósito:
toda la lógica está en `responder.responder` y `responder.comando`, que se
testean sin Telegram."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..database import SessionLocal
from . import recuperar
from .responder import _gemini_default, comando, responder

log = logging.getLogger("ruperto.telegram")

COMANDOS = ("start", "estado", "riego", "silencio", "ayuda")
MAX_MENSAJE = 4000      # Telegram corta en 4096


async def _enviar(update: Update, texto: str) -> None:
    # Texto plano: el Markdown de Gemini rompe el parse_mode con cualquier _ suelto.
    await update.effective_message.reply_text(texto[:MAX_MENSAJE])


async def _comando(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    nombre = update.effective_message.text.split()[0].lstrip("/").split("@")[0].lower()
    usuario = update.effective_user.username if update.effective_user else None
    with SessionLocal() as db:
        r = await comando(nombre, update.effective_chat.id, db, usuario=usuario)
    await _enviar(update, r.texto)


async def _texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_action(ChatAction.TYPING)
    with SessionLocal() as db:
        r = await responder(update.effective_message.text, update.effective_chat.id, db)
    log.info("chat %s: dominio=%s intención=%s %d frags %d ms%s", update.effective_chat.id,
             r.en_dominio, r.intencion, len(r.fragmentos), r.latencia_ms,
             f" error={r.error}" if r.error else "")
    await _enviar(update, r.texto)


async def _error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("error en un handler", exc_info=context.error)


def construir(token: str) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler(list(COMANDOS), _comando))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _texto))
    app.add_error_handler(_error)
    return app


def correr(token: str) -> None:
    _gemini_default()                 # crea el cliente y configura el embedder
    recuperar._indice_default()       # carga (o avisa que falta) el índice al arrancar
    log.info("Ruperto arrancando (polling)")
    # Una sola réplica: dos procesos en polling se pisan los updates (D2).
    construir(token).run_polling(allowed_updates=Update.ALL_TYPES)
