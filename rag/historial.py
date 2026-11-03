"""Historial de Ruperto → chunks de texto (fuente `historial`, docs/ENTREGA3.md §4).

Un chunk por **día** (hora de Montevideo) y uno por **episodio** de
`data/episodios.csv`. Todo sale de plantaia_ml para no tener dos versiones de
la misma lógica:

- `dataset.serie_maceta01(filtrado=False)`: lee el snapshot crudo, une
  `maceta-02` a `maceta-01` (`datos_reales.unificar_maceta`), remuestrea a 5 min,
  cruza con los episodios y calcula las features como la placa.
- **Riegos**: las filas donde `h_desde_riego` vale 0, es decir, donde la regla
  del contrato de features (ENTREGA2.md §4: caída ≥ 250 mV de una lectura real
  fuera del warm-up) registró un riego. Es exactamente lo que vería la placa.

Las estadísticas de la sonda no cuentan los bins con la sonda saturada (fuera
del sustrato) ni la primera hora tras cada arranque (transitorio de la sonda,
`post_boot`). Los huecos de la serie quedan como huecos: un día sin datos no
tiene chunk.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import RAIZ  # noqa: F401  (agrega ml/ al sys.path)
from .chunks import Chunk
from plantaia_ml import DATOS
from plantaia_ml.dataset import serie_maceta01
from plantaia_ml.datos_reales import EPISODIOS_DUDOSOS, leer_episodios

ZONA = "America/Montevideo"
MAX_PALABRAS_NOTA = 70


def _num(v: float, dec: int = 0) -> str:
    """Número con coma decimal (estilo del informe); 's/d' si falta."""
    if v is None or (isinstance(v, float) and np.isnan(v)) or pd.isna(v):
        return "s/d"
    return f"{v:.{dec}f}".replace(".", ",")


def _rango(s: pd.Series, dec: int = 0, unidad: str = "") -> str:
    s = s.dropna()
    if s.empty:
        return "sin datos"
    u = f" {unidad}" if unidad else ""
    return f"mín {_num(s.min(), dec)}, media {_num(s.mean(), dec)}, máx {_num(s.max(), dec)}{u}"


def _nota_corta(nota) -> str:
    if not isinstance(nota, str) or not nota.strip():
        return ""
    p = nota.split()
    return " ".join(p[:MAX_PALABRAS_NOTA]) + (" …" if len(p) > MAX_PALABRAS_NOTA else "")


def _hora(ts: pd.Timestamp) -> str:
    return ts.tz_convert(ZONA).strftime("%d/%m %H:%M")


def cargar_serie(snapshot: Path | str, episodios: Path | str = DATOS / "episodios.csv") -> pd.DataFrame:
    """Serie a 5 min de la maceta, sin filtrar, con `riego` (bool) y `dia` local."""
    df = serie_maceta01(snapshot, episodios, filtrado=False)
    df["riego"] = df.h_desde_riego.eq(0.0)
    df["ts_local"] = df.ts.dt.tz_convert(ZONA)
    df["dia"] = df.ts_local.dt.strftime("%Y-%m-%d")
    # Sonda utilizable para describir el sustrato.
    df["suelo_ok"] = df.suelo_mv.where(~df.suelo_saturado & ~df.post_boot)
    return df


def riegos(df: pd.DataFrame) -> pd.Series:
    """Horas (UTC) de los riegos detectados, en orden."""
    return df.loc[df.riego, "ts"].sort_values().reset_index(drop=True)


def _episodios_del_dia(ep: pd.DataFrame, dia: str) -> pd.DataFrame:
    ini = pd.Timestamp(dia, tz=ZONA).tz_convert("UTC")
    fin = ini + pd.Timedelta(days=1)
    return ep[(ep.ts_inicio < fin) & (ep.ts_fin > ini)].sort_values("ts_inicio")


def texto_dia(dia: str, d: pd.DataFrame, ep: pd.DataFrame) -> str:
    horas = len(d) * 5 / 60
    lineas = [
        f"Resumen del día {dia} (hora de Montevideo) de la maceta de Ruperto.",
        f"Muestras a 5 min: {len(d)} (unas {_num(horas, 1)} h medidas), "
        f"de {d.ts_local.min():%H:%M} a {d.ts_local.max():%H:%M}.",
        f"Sonda de suelo (más mV = más seco): {_rango(d.suelo_ok, 0, 'mV')}.",
        f"Temperatura del aire (DHT11): {_rango(d.temp_c, 1, '°C')}.",
        f"Humedad relativa del aire: {_rango(d.hum_aire_pct, 0, '%')}.",
        f"Luz máxima del LDR: {_num(d.luz_mv.max(), 0)} mV.",
    ]
    r = d.loc[d.riego, "ts"]
    if len(r):
        lineas.append("Riegos detectados (caída de la sonda ≥ 250 mV): "
                      + ", ".join(f"{_hora(t)}" for t in r) + ".")
    else:
        lineas.append("Riegos detectados: ninguno.")
    eps = _episodios_del_dia(ep, dia)
    if eps.empty:
        lineas.append("Episodio de etiqueta: ninguno (nadie etiquetó la planta en este tramo).")
    for _, e in eps.iterrows():
        dud = " Episodio dudoso." if e.episodio_id in EPISODIOS_DUDOSOS else ""
        nota = _nota_corta(e.nota)
        lineas.append(f"Episodio {e.episodio_id}: {e.clase} (origen {e.origen}), "
                      f"de {_hora(e.ts_inicio)} a {_hora(e.ts_fin)}.{dud}"
                      + (f" Nota: {nota}" if nota else ""))
    return "\n".join(lineas)


def texto_episodio(e: pd.Series, d: pd.DataFrame) -> str:
    dur = (e.ts_fin - e.ts_inicio).total_seconds() / 3600
    lineas = [
        f"Episodio {e.episodio_id} de Ruperto: clase {e.clase}, origen {e.origen}.",
        f"Desde {_hora(e.ts_inicio)} hasta {_hora(e.ts_fin)} (hora de Montevideo), "
        f"{_num(dur, 1)} h.",
    ]
    if e.episodio_id in EPISODIOS_DUDOSOS:
        lineas.append(f"Es un episodio dudoso, fuera del entrenamiento del modelo: "
                      f"{EPISODIOS_DUDOSOS[e.episodio_id]}.")
    if d.empty:
        lineas.append("No hay muestras de la placa en este intervalo.")
    else:
        lineas += [
            f"Muestras a 5 min: {len(d)}.",
            f"Sonda de suelo: {_rango(d.suelo_ok, 0, 'mV')}.",
            f"Temperatura del aire: {_rango(d.temp_c, 1, '°C')}; "
            f"humedad relativa: {_rango(d.hum_aire_pct, 0, '%')}.",
        ]
        r = d.loc[d.riego, "ts"]
        lineas.append("Riegos detectados en el episodio: "
                      + (", ".join(_hora(t) for t in r) if len(r) else "ninguno") + ".")
    nota = _nota_corta(e.nota)
    if nota:
        lineas.append(f"Nota del observador: {nota}")
    return "\n".join(lineas)


def chunks_historial(snapshot: Path | str, episodios: Path | str = DATOS / "episodios.csv",
                     serie: pd.DataFrame | None = None) -> list[Chunk]:
    """Chunks por día (ordenados por fecha) y después por episodio (por id)."""
    df = cargar_serie(snapshot, episodios) if serie is None else serie
    ep = leer_episodios(episodios)
    ep = ep[ep.dispositivo == "maceta-01"]
    out: list[Chunk] = []
    for dia, d in df.groupby("dia", sort=True):
        out.append(Chunk(f"historial/dia-{dia}#0", "historial", f"Resumen del día {dia}",
                         None, dia, texto_dia(dia, d, ep)))
    for _, e in ep.sort_values("episodio_id").iterrows():
        d = df[(df.ts >= e.ts_inicio) & (df.ts < e.ts_fin)]
        dia = e.ts_inicio.tz_convert(ZONA).strftime("%Y-%m-%d")
        out.append(Chunk(f"historial/episodio-{e.episodio_id}#0", "historial",
                         f"Episodio {e.episodio_id} ({e.clase})", None, dia,
                         texto_episodio(e, d)))
    return out
