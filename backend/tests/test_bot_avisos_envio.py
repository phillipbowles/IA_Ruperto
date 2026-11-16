"""Envío de los avisos (emisor.py, §6 y D7) con un bot falso: sin Telegram."""
import asyncio
from datetime import timedelta

from conftest import PASO, T0, cargar
from telegram.error import Forbidden, NetworkError

from app.bot import emisor
from app.models import ChatTelegram

SECA = [2100.0] * 12                     # sobre el umbral de marchita, sin riegos
AHORA = T0 + 11 * PASO + timedelta(minutes=2)


class BotFalso:
    def __init__(self, errores=None):
        self.errores = errores or {}     # chat_id → excepción
        self.enviados: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text):
        if chat_id in self.errores:
            raise self.errores[chat_id]
        self.enviados.append((chat_id, text))


def correr(coro):
    return asyncio.run(coro)


def chats(db, *ids, apagados=()):
    db.add_all([ChatTelegram(chat_id=i, suscripto=True) for i in ids]
               + [ChatTelegram(chat_id=i, suscripto=False) for i in apagados])
    db.commit()


def test_medicion_va_solo_a_los_suscriptos(db):
    cargar(db, [1700.0] * 12)
    chats(db, 1, 2, apagados=(3,))
    bot = BotFalso()
    assert correr(emisor.avisar_medicion(bot, db, AHORA)) == 2
    assert sorted(c for c, _ in bot.enviados) == [1, 2]
    assert "Tierra:" in bot.enviados[0][1]


def test_riego_respeta_el_antirrebote(db):
    cargar(db, SECA)
    chats(db, 1)
    bot = BotFalso()
    assert correr(emisor.avisar_riego(bot, db, AHORA)) == 1
    assert "Agua" in bot.enviados[0][1]
    assert db.get(ChatTelegram, 1).ultimo_aviso_riego is not None
    # 5 min después no repite; a las 6 h sí.
    assert correr(emisor.avisar_riego(bot, db, AHORA + PASO)) == 0
    cargar(db, [2100.0] * 3, t0=AHORA + timedelta(hours=6) - 2 * PASO)
    assert correr(emisor.avisar_riego(bot, db, AHORA + timedelta(hours=6))) == 1
    assert len(bot.enviados) == 2


def test_sin_aviso_de_riego_con_los_sensores_caidos(db):
    cargar(db, SECA)
    chats(db, 1)
    bot = BotFalso()
    assert correr(emisor.avisar_riego(bot, db, AHORA + timedelta(hours=3))) == 0   # datos viejos
    assert bot.enviados == []


def test_forbidden_desuscribe(db):
    cargar(db, [1700.0] * 12)
    chats(db, 1, 2)
    bot = BotFalso(errores={1: Forbidden("bot was blocked by the user")})
    assert correr(emisor.avisar_medicion(bot, db, AHORA)) == 1
    assert db.get(ChatTelegram, 1).suscripto is False
    assert db.get(ChatTelegram, 2).suscripto is True


def test_un_error_no_corta_a_los_demas(db):
    cargar(db, SECA)
    chats(db, 1, 2, 3)
    bot = BotFalso(errores={2: NetworkError("timeout")})
    assert correr(emisor.avisar_riego(bot, db, AHORA)) == 2
    assert sorted(c for c, _ in bot.enviados) == [1, 3]
    # El que falló sigue suscripto y sin marca: le toca en el próximo tick.
    falla = db.get(ChatTelegram, 2)
    assert falla.suscripto is True and falla.ultimo_aviso_riego is None


def test_handlers_arrancan_la_tarea_de_avisos():
    from app.bot.telegram_bot import _arrancar_avisos, _parar_avisos, construir
    app = construir("123456:ABC-token-de-prueba")

    async def ciclo():
        emisor_bucle, emisor.bucle = emisor.bucle, lambda bot: asyncio.sleep(3600)
        try:
            await _arrancar_avisos(app)
            tarea = app.bot_data["avisos"]
            await _parar_avisos(app)
            await asyncio.sleep(0)
            return tarea.cancelled()
        finally:
            emisor.bucle = emisor_bucle

    assert correr(ciclo())
