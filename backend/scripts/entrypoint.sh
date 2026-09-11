#!/bin/sh
# Entrypoint del contenedor del backend.
#
# Aplica las migraciones pendientes y recién después arranca el servidor, para
# que el código nunca corra contra un esquema viejo. Si una migración falla,
# `set -e` corta acá y el contenedor no levanta: es lo que queremos — es
# preferible un servicio caído a uno sirviendo contra una base a medio migrar.
set -e

echo "→ aplicando migraciones (alembic upgrade head)"
alembic upgrade head
echo "→ migraciones al día"

# exec reemplaza el proceso del shell: uvicorn queda como PID 1 y recibe
# directamente el SIGTERM del `docker compose down`, sin esperar el timeout.
echo "→ arrancando servidor"
exec "$@"
