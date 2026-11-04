"""`python -m app.bot`: arranca Ruperto en Telegram por polling (D2).

Verifica las variables antes de importar nada que toque la base o Gemini, para
fallar con un mensaje claro en vez de un KeyError en medio de un import.
"""
from __future__ import annotations

import logging
import os
import sys

REQUERIDAS = {
    "TELEGRAM_BOT_TOKEN": "el token que da @BotFather",
    "GEMINI_API_KEY": "la clave de Google AI Studio",
    "DATABASE_URL": "la URL de Postgres (la misma del backend)",
}


def faltantes(env: dict[str, str] | None = None) -> list[str]:
    env = os.environ if env is None else env
    return [k for k in REQUERIDAS if not env.get(k, "").strip()]


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx loguea cada getUpdates del polling, con el token en la URL.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    falta = faltantes()
    if falta:
        print("Ruperto no puede arrancar: faltan variables de entorno.", file=sys.stderr)
        for k in falta:
            print(f"  {k}: {REQUERIDAS[k]}", file=sys.stderr)
        print("Ver .env.example y docs/ENTREGA3.md §5.6.", file=sys.stderr)
        return 2
    from .telegram_bot import correr
    correr(os.environ["TELEGRAM_BOT_TOKEN"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
