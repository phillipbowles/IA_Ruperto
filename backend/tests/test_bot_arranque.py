"""`python -m app.bot` sin variables falla con un mensaje claro."""
import subprocess
import sys
from pathlib import Path

from app.bot.__main__ import faltantes


def test_faltantes():
    assert faltantes({}) == ["TELEGRAM_BOT_TOKEN", "GEMINI_API_KEY", "DATABASE_URL"]
    assert faltantes({"TELEGRAM_BOT_TOKEN": "t", "GEMINI_API_KEY": " ", "DATABASE_URL": "x"}) == \
        ["GEMINI_API_KEY"]


def test_python_m_app_bot_sin_token():
    env = {"PATH": "/usr/bin:/bin", "DATABASE_URL": "sqlite://"}
    p = subprocess.run([sys.executable, "-m", "app.bot"], check=False, cwd=Path(__file__).parents[1], env=env,
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 2
    assert "TELEGRAM_BOT_TOKEN" in p.stderr and "GEMINI_API_KEY" in p.stderr
    assert "Traceback" not in p.stderr


def test_handlers_de_telegram_se_registran():
    from app.bot.telegram_bot import COMANDOS, construir
    app = construir("123456:ABC-token-de-prueba")
    cmds = set()
    for h in app.handlers[0]:
        cmds |= set(getattr(h, "commands", ()))
    assert cmds == set(COMANDOS)
    assert len(app.handlers[0]) == 2
