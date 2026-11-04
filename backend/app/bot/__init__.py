"""Ruperto, el bot de Telegram de la maceta (Tarea 3, docs/ENTREGA3.md).

    python -m app.bot          # polling

Sin imports acá a propósito: `app.database` exige DATABASE_URL al importarse,
y `python -m app.bot` tiene que poder decir qué variable falta antes de eso.
El punto de entrada para contestar es `app.bot.responder.responder`.
"""
