#!/usr/bin/env bash
# Corre el replay en host y deja el log en docs/entrega2/logs/replay_host.txt.
#
#   firmware/tools/correr_replay.sh            # desde cualquier lado
#
# Para cambiar el tramo, regenerar antes el header:
#   /opt/anaconda3/bin/python firmware/tools/generar_replay.py --tramo ...
set -euo pipefail

FIRMWARE="$(cd "$(dirname "$0")/.." && pwd)"
SALIDA="$FIRMWARE/../docs/entrega2/logs/replay_host.txt"
mkdir -p "$(dirname "$SALIDA")"

cd "$FIRMWARE"
PLANTAIA_REPLAY_SALIDA="$SALIDA" pio test -e native -f test_replay
echo "log: $(cd "$(dirname "$SALIDA")" && pwd)/$(basename "$SALIDA")"
