#!/opt/anaconda3/bin/python
"""Genera firmware/test/test_replay/replay_datos.h a partir de un CSV crudo.

El replay en host (test/test_replay) pasa estas muestras por el MISMO código C++
que corre en la placa (lib/plantaia_ml: buffer → features → modelo) e imprime
las líneas [INF]. Para que la ventana de 1 h signifique lo mismo que en la placa,
el CSV (que en el dato real quedó a 30 s) se remuestrea a 5 min con la mediana
por bin.

Uso (desde la raíz del repo):

    /opt/anaconda3/bin/python firmware/tools/generar_replay.py \\
        --tramo data/mediciones_raw_2026-10-21.csv maceta-01 2026-10-19T14:00Z 150

    # cuando exista el simulado, se agregan más tramos al mismo header:
    #   --tramo data/sintetico/mediciones_sim.csv.gz sim-01 <desde> 150

Reglas (las mismas que aplica la placa al armar la MuestraCruda, ver main.cpp):
  - hora = ts_dispositivo si es válida (>= 2026-01-01), si no ts_servidor;
  - suelo saturado (suelo_raw <= 0 o >= 4095: sonda fuera del sustrato) → NAN,
    y el buffer repite el anterior;
  - la luz saturada NO es faltante (es luz fuerte de verdad);
  - DHT / termistor en null → NAN;
  - un bin de 5 min sin ninguna fila es un HUECO: el bin no se emite y la
    muestra siguiente corta (vacía el buffer). Es lo mismo que hace
    ml/plantaia_ml/features.py (asignar_tramos: hueco > 7,5 min → tramo nuevo);
    no se interpola ni se inventan filas. Se avisa por stderr;
  - cambio de boot_id dentro del tramo → también corta, como la placa al reiniciar.

Sólo pandas/numpy (sin dependencias nuevas).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
SALIDA_DEFECTO = RAIZ / "firmware" / "test" / "test_replay" / "replay_datos.h"
HORA_MINIMA_VALIDA = pd.Timestamp("2026-01-01", tz="UTC")
COLUMNAS = ["suelo_mv", "luz_mv", "temperatura_c", "humedad_ambiente_pct", "temp_ntc_c"]


def cargar(ruta: Path, dispositivo: str) -> pd.DataFrame:
    d = pd.read_csv(ruta)
    d = d[d["dispositivo"] == dispositivo].copy()
    if d.empty:
        sys.exit(f"{ruta}: no hay filas de {dispositivo!r}")
    ts_srv = pd.to_datetime(d["ts_servidor"], utc=True, format="mixed")
    if "ts_dispositivo" in d:
        ts_dev = pd.to_datetime(d["ts_dispositivo"], utc=True, format="mixed", errors="coerce")
        d["t"] = ts_dev.where(ts_dev >= HORA_MINIMA_VALIDA, ts_srv)
    else:
        d["t"] = ts_srv
    saturado = (d["suelo_raw"] <= 0) | (d["suelo_raw"] >= 4095)
    d.loc[saturado, "suelo_mv"] = np.nan
    return d.sort_values("t")


def remuestrear(d: pd.DataFrame, desde: pd.Timestamp, n: int) -> pd.DataFrame:
    hasta = desde + pd.Timedelta(minutes=5 * n)
    d = d[(d["t"] >= desde) & (d["t"] < hasta)].copy()
    d["bin"] = d["t"].dt.floor("5min")
    agg = {c: "median" for c in COLUMNAS}
    agg.update({"boot_id": "last", "condicion_codigo": "last"})
    r = d.groupby("bin").agg(agg)
    bins = pd.date_range(desde, periods=n, freq="5min")
    r = r.reindex(bins)
    hueco = r["boot_id"].isna()
    if hueco.any():
        print(f"aviso: {int(hueco.sum())} bins de 5 min sin filas → se omiten y la "
              f"muestra siguiente corta el buffer", file=sys.stderr)
    # corte = vaciar el buffer antes de esta muestra: primera del tramo, cambio
    # de boot_id o viene después de un hueco.
    corte = hueco.shift(1, fill_value=True) | (r["boot_id"] != r["boot_id"].shift(1))
    r["corte"] = corte
    r = r[~hueco].copy()
    r["corte"] = r["corte"] | (r["boot_id"] != r["boot_id"].shift(1))
    r["condicion_codigo"] = r["condicion_codigo"].fillna(0)
    return r


def f(v: float, dec: int = 1) -> str:
    return "NAN" if (v is None or (isinstance(v, float) and math.isnan(v))) else f"{v:.{dec}f}f"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tramo", nargs=4, action="append", required=True,
                    metavar=("CSV", "DISPOSITIVO", "DESDE_UTC", "N"),
                    help="CSV crudo, dispositivo, inicio (ISO, UTC) y cantidad de muestras de 5 min")
    ap.add_argument("--salida", type=Path, default=SALIDA_DEFECTO)
    args = ap.parse_args()

    filas, descs = [], []
    for k, (csv, disp, desde, n) in enumerate(args.tramo):
        ruta = Path(csv)
        if not ruta.is_absolute():
            ruta = RAIZ / ruta
        desde_ts = pd.Timestamp(desde).tz_convert("UTC") if pd.Timestamp(desde).tzinfo else pd.Timestamp(desde, tz="UTC")
        r = remuestrear(cargar(ruta, disp), desde_ts, int(n))
        try:
            nombre = ruta.relative_to(RAIZ)
        except ValueError:
            nombre = ruta.name
        descs.append(f"{nombre} {disp} desde {desde_ts:%Y-%m-%dT%H:%MZ} x{n} (5 min)")
        for ts, fila in r.iterrows():
            filas.append((int(ts.timestamp()), int(fila["boot_id"]), k, int(bool(fila["corte"])),
                          int(fila["condicion_codigo"]),
                          fila["suelo_mv"], fila["luz_mv"], fila["temperatura_c"],
                          fila["humedad_ambiente_pct"], fila["temp_ntc_c"]))

    lineas = [
        "// GENERADO por firmware/tools/generar_replay.py — no editar a mano.",
        "// Secuencia cruda remuestreada a 5 min (mediana por bin) para el replay en host.",
        "// NAN = faltante (la placa lo trata igual: repite el anterior / último válido).",
        "#pragma once",
        "#include <math.h>",
        "#include <stdint.h>",
        "",
        "struct FilaReplay {",
        "  uint32_t ts_unix;   // inicio del bin de 5 min, UTC",
        "  uint32_t boot_id;",
        "  uint8_t  tramo;     // índice en REPLAY_TRAMOS",
        "  uint8_t  corte;     // 1 = vaciar el buffer antes (tramo nuevo, boot_id nuevo o tras un hueco)",
        "  uint8_t  etiqueta;  // condicion_codigo observada (0 = sin_etiquetar), sólo para comparar",
        "  float    suelo_mv, luz_mv, temp_dht_c, hum_aire_pct, temp_ntc_c;",
        "};",
        "",
        "static const char *const REPLAY_TRAMOS[] = {",
        *[f'  "{d}",' for d in descs],
        "};",
        f"static const int REPLAY_N_TRAMOS = {len(descs)};",
        "",
        "static const FilaReplay REPLAY[] = {",
    ]
    for ts, boot, tr, corte, et, s, l, t, h, ntc in filas:
        lineas.append(f"  {{{ts}u, {boot}u, {tr}, {corte}, {et}, {f(s)}, {f(l)}, {f(t)}, {f(h)}, {f(ntc)}}},")
    lineas += [
        "};",
        "static const int REPLAY_N = (int)(sizeof(REPLAY) / sizeof(REPLAY[0]));",
        "",
    ]
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text("\n".join(lineas), encoding="utf-8")
    print(f"{args.salida}: {len(filas)} muestras en {len(descs)} tramo(s)")


if __name__ == "__main__":
    main()
