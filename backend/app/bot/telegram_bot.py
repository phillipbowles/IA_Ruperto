"""Handlers de Telegram (python-telegram-bot ≥ 21, polling). Finos a propósito:
toda la lógica está en `responder.responder` y `responder.comando`, que se
testean sin Telegram. Los avisos (§6) los manda `emisor.bucle`, una tarea de
asyncio que arranca con la Application.

Las notas de voz (D222) pasan por `voz.conversar`: se transcriben, se contestan
con el mismo `responder` y la respuesta vuelve en texto y en nota de voz."""
from __future__ import annotations

import asyncio
import io
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..database import SessionLocal
from . import emisor, persona, recuperar, voz
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


MAX_SEGUNDOS_VOZ = 60


def _cliente_voz() -> voz.ClienteVoz | None:
    try:
        c = voz.cliente() if voz.configurada() else None
    except voz.ErrorVoz:
        return None
    return c if c is not None and c.disponible else None


async def _mandar_audio(update: Update, c: voz.Charla, cliente: voz.ClienteVoz) -> None:
    """La respuesta hablada. Telegram sólo muestra como nota de voz un Ogg/Opus:
    si ElevenLabs devolvió otra cosa, se pide en mp3 y va como audio."""
    audio = c.audio
    if audio and audio[:4] == b"OggS":
        await update.effective_message.reply_voice(io.BytesIO(audio))
        return
    # Opus sin contenedor Ogg: no se puede reproducir, se pide en mp3. Si ya
    # se había pedido en mp3 (`opus_es_ogg` aprendido), se manda el que vino.
    if audio and c.audio_mime != voz.FORMATOS["mp3"][1]:
        fijo = c.respuesta is None or voz._es_fijo(c.respuesta)
        audio, _, _ = await voz.hablar(c.texto, cliente, "mp3", fijo=fijo)
    if audio:
        await update.effective_message.reply_audio(io.BytesIO(audio), filename="ruperto.mp3",
                                                   title="Ruperto", performer="Ruperto")


async def _voz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Nota de voz (o audio, o videomensaje) → respuesta en texto y en voz."""
    m = update.effective_message
    adjunto = m.voice or m.audio or m.video_note
    cliente = _cliente_voz()
    if cliente is None:
        await _enviar(update, persona.SIN_OIDOS)
        return
    if (adjunto.duration or 0) > MAX_SEGUNDOS_VOZ or (adjunto.file_size or 0) > voz.MAX_BYTES_AUDIO:
        await _enviar(update, persona.AUDIO_LARGO)
        return
    await update.effective_chat.send_action(ChatAction.RECORD_VOICE)
    archivo = await adjunto.get_file()
    datos = bytes(await archivo.download_as_bytearray())
    mime = getattr(adjunto, "mime_type", None) or ("video/mp4" if m.video_note else "audio/ogg")
    # Si ya se sabe que el opus de ElevenLabs no viene en Ogg, se pide mp3 de entrada.
    formato = "mp3" if cliente.opus_es_ogg is False else "opus"
    with SessionLocal() as db:
        c = await voz.conversar(datos, mime, update.effective_chat.id, db, voz=cliente,
                                formato=formato)
    r = c.respuesta
    log.info("chat %s (voz): oír %d ms, hablar %d ms, voz=%s%s", update.effective_chat.id,
             c.ms_oir, c.ms_hablar, c.error_voz or "ok",
             f" dominio={r.en_dominio} intención={r.intencion} error={r.error}" if r else "")
    # El texto va siempre: sirve de subtítulo y deja a la vista lo que se entendió.
    texto = f"🎙️ «{c.pregunta}»\n\n{c.texto}" if c.pregunta else c.texto
    await _enviar(update, texto)
    if c.audio:
        try:
            await _mandar_audio(update, c, cliente)
        except Exception:
            log.exception("no se pudo mandar la nota de voz a %s", update.effective_chat.id)


async def _error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("error en un handler", exc_info=context.error)


async def _arrancar_avisos(app: Application) -> None:
    # Tarea propia y no JobQueue: no suma el extra [job-queue] de python-telegram-bot.
    app.bot_data["avisos"] = asyncio.create_task(emisor.bucle(app.bot), name="avisos")


async def _parar_avisos(app: Application) -> None:
    tarea = app.bot_data.pop("avisos", None)
    if tarea:
        tarea.cancel()


def construir(token: str) -> Application:
    app = (Application.builder().token(token)
           .post_init(_arrancar_avisos).post_stop(_parar_avisos).build())
    app.add_handler(CommandHandler(list(COMANDOS), _comando))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _texto))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO_NOTE, _voz))
    app.add_error_handler(_error)
    return app


def correr(token: str) -> None:
    _gemini_default()                 # crea el cliente y configura el embedder
    recuperar._indice_default()       # carga (o avisa que falta) el índice al arrancar
    log.info("Ruperto arrancando (polling)")
    # Una sola réplica: dos procesos en polling se pisan los updates (D2).
    construir(token).run_polling(allowed_updates=Update.ALL_TYPES)
