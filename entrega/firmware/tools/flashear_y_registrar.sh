#!/usr/bin/env bash
# Flashea el firmware (pio run -t upload) y captura el Serial con hora en
# docs/entrega2/logs/placa_<fecha>_<hora>.txt. Hace falta la placa por USB y
# firmware/include/secrets.h (WiFi + token).
#
#   firmware/tools/flashear_y_registrar.sh            # 16 min de log (~4 inferencias)
#   MINUTOS=65 firmware/tools/flashear_y_registrar.sh # para salir del warm-up (1 h)
set -euo pipefail

FIRMWARE="$(cd "$(dirname "$0")/.." && pwd)"
RAIZ="$(cd "$FIRMWARE/.." && pwd)"
SALIDA="$RAIZ/docs/entrega2/logs/placa_$(date +%F_%H%M).txt"
MINUTOS="${MINUTOS:-16}"
PY="${PY:-/opt/anaconda3/bin/python}"

[ -f "$FIRMWARE/include/secrets.h" ] || { echo "falta firmware/include/secrets.h (copiar secrets.example.h)"; exit 1; }

cd "$FIRMWARE"
pio run -e esp32dev -t upload
# Sin pausa el puerto todavía está ocupado por el upload.
sleep 1
"$PY" "$FIRMWARE/tools/capturar_serial.py" --minutos "$MINUTOS" --salida "$SALIDA"
echo "log: $SALIDA"
grep -E "^\[ *[0-9.]+s\] (\[INF\]|\[RIE\]|modelo=|ultimo riego)" "$SALIDA" || true
