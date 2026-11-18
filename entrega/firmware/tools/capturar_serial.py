"""Captura el Serial de la placa durante un tiempo fijo y lo guarda con hora.

    /opt/anaconda3/bin/python firmware/tools/capturar_serial.py --minutos 16 --salida docs/entrega2/logs/placa.txt

Cada línea sale con `[  12.3s] ` adelante (segundos desde que empezó la
captura), el mismo formato que los logs del 22/10. Abre el puerto con DTR/RTS
bajos para no reiniciar la placa al conectarse; el reinicio lo hace el upload.
Si no se pasa --puerto, usa el único /dev/cu.usbserial*/SLAB*/wchusbserial*.
"""
from __future__ import annotations

import argparse
import glob
import sys
import time
from pathlib import Path

import serial


def puerto_unico() -> str:
    cands = sorted(set(glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.SLAB*")
                       + glob.glob("/dev/cu.wchusbserial*")))
    if len(cands) != 1:
        sys.exit(f"no hay una sola placa conectada (encontré {cands or 'ninguna'}): pasar --puerto")
    return cands[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto")
    ap.add_argument("--baudios", type=int, default=115200)
    ap.add_argument("--minutos", type=float, default=16.0)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    puerto = a.puerto or puerto_unico()
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = puerto, a.baudios, 0.5
    s.dtr = s.rts = False
    s.open()
    t0 = time.monotonic()
    fin = t0 + a.minutos * 60
    print(f"capturando {puerto} durante {a.minutos:g} min → {a.salida}", flush=True)
    with a.salida.open("w", encoding="utf-8") as f:
        f.write(f"# captura de {puerto} a {a.baudios} baudios, {time.strftime('%Y-%m-%d %H:%M:%S %z')}\n")
        resto = b""
        while time.monotonic() < fin:
            resto += s.read(4096)
            *lineas, resto = resto.split(b"\n")
            for l in lineas:
                texto = l.decode("utf-8", "replace").rstrip("\r")
                linea = f"[{time.monotonic() - t0:6.1f}s] {texto}"
                f.write(linea + "\n")
                f.flush()
                print(linea, flush=True)
    s.close()


if __name__ == "__main__":
    main()
