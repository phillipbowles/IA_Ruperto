# syntax=docker/dockerfile:1

# ─── base ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Las dependencias se instalan ANTES de copiar el código, para que un cambio en
# un .py no invalide la capa de instalación. El paquete stub existe solo para
# que `pip install -e .` resuelva durante esta capa; después lo pisa el código real.
COPY pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py

# ─── dev ───────────────────────────────────────────────────────────────────
FROM base AS dev
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ─── prod ──────────────────────────────────────────────────────────────────
FROM base AS prod
RUN pip install --no-cache-dir -e .
COPY . .

# Sin root: si alguien escapa del proceso, no escapa como administrador.
RUN useradd --create-home --uid 10001 planta && chown -R planta:planta /app
USER planta

EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
# 0.0.0.0 y no ::. La tentacion es usar :: para cubrir las dos familias, pero
# asyncio pone IPV6_V6ONLY=1 en todo socket IPv6, asi que uvicorn con :: acepta
# SOLO IPv6: la red privada de Railway entra, pero el edge publico llega por
# IPv4 y se come un RST -> 502. Y el publico es el que necesita la ESP32.
# El front no pierde nada: le apuntamos BACKEND_URL a la URL publica.
# Para servir ambas familias haria falta gunicorn con dos -b; no vale la pena.
# Railway inyecta $PORT; en local cae a 8000. sh -c para que la variable expanda.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
