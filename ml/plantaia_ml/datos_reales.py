"""Carga y limpieza de los snapshots crudos de Railway (docs/ENTREGA2.md §3.1).

Cualquier CSV con el esquema crudo de Railway pasa por el mismo camino; la
columna `fuente` dice de dónde salió cada fila (`real` = lo medido por la placa).

Pasos, en este orden y por qué:

1. **Hora**: `ts_dispositivo` si es válida, si no `ts_servidor`. Válida quiere
   decir posterior a `HORA_VALIDA_DESDE` (2026-01-01, el mismo criterio que el
   notebook 02): la fila id 1 trae la placa en 2025-09-11 con el reloj sin
   sincronizar y un umbral en 2025 la dejaría un año corrida.
2. **Episodio por fila**: la etiqueta es la del episodio de `episodios.csv` que
   contiene la fila (intervalo semiabierto), no la `condicion_etiqueta` que
   mandó la placa.
3. **Remuestreo a 5 min** por `(dispositivo, boot_id)`: mediana por bin de
   reloj. Con la placa a 30 s, sin esto la ventana de "1 h" del contrato §4
   serían 120 muestras en vez de 13 y no significaría lo mismo que en la ESP32.
   No se interpola: un bin sin filas no existe y el cálculo de features corta
   el tramo ahí.
4. **Marcas** (no se borra nada en `preparar`): `post_boot` (primeros 60 min
   tras el arranque: el transitorio exponencial de la sonda que mostró el
   notebook 02 tiene τ de 24–83 min y a los 30 min queda todavía la mitad),
   `suelo_saturado` (sonda fuera del sustrato) y `dudoso`.
5. `cargar_reales` aplica los filtros: fuera post-boot, saturados y filas sin
   episodio.

Las temperaturas de 26–36 °C del 15 y 16/09 **no son outliers**: la maceta
estaba sobre un radiador (ver data/README.md). No se recortan ni se filtran.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import DATOS, SNAPSHOT_VIGENTE

HORA_VALIDA_DESDE = pd.Timestamp("2026-01-01", tz="UTC")
BIN = pd.Timedelta(minutes=5)
POST_BOOT_MIN = 60
ADC_MAX = 4095

# Episodios reales cuya etiqueta no se sostiene sola. El notebook de modelos
# reporta con y sin ellos. El porqué completo está en la nota de cada uno.
EPISODIOS_DUDOSOS = {
    8: "marchita con el sustrato igual que saludable (~1550 mV), nocturna",
    9: "estresada con el sustrato en ~1454 mV, el rango de los saludable de octubre",
    11: "propagada de Preferences 16 días después; contradicha por la observación siguiente",
    14: "estresada propagada ~25 h después de un riego, sin nadie que la confirme",
}

# Columnas numéricas que se remuestrean con la mediana del bin.
_NUMERICAS = ["suelo_mv", "suelo_raw", "luz_mv", "luz_raw", "temperatura_c",
              "humedad_ambiente_pct", "temp_ntc_c"]


def leer_crudo(ruta: Path | str = SNAPSHOT_VIGENTE) -> pd.DataFrame:
    """Lee un CSV con el esquema crudo de Railway y agrega la columna `ts` (UTC)."""
    raw = pd.read_csv(ruta, low_memory=False)
    raw["ts"] = elegir_hora(raw)
    return raw


def elegir_hora(raw: pd.DataFrame) -> pd.Series:
    """`ts_dispositivo` si existe y es posterior a 2026-01-01; si no, `ts_servidor`."""
    disp = pd.to_datetime(raw["ts_dispositivo"], utc=True, format="ISO8601", errors="coerce")
    serv = pd.to_datetime(raw["ts_servidor"], utc=True, format="ISO8601", errors="coerce")
    return disp.where(disp >= HORA_VALIDA_DESDE, serv)


def leer_episodios(ruta: Path | str = DATOS / "episodios.csv") -> pd.DataFrame:
    ep = pd.read_csv(ruta)
    for c in ("ts_inicio", "ts_fin"):
        ep[c] = pd.to_datetime(ep[c], utc=True, format="ISO8601")
    return ep


def asignar_episodios(df: pd.DataFrame, episodios: pd.DataFrame, col_ts: str = "ts") -> pd.DataFrame:
    """Agrega `episodio_id`, `clase` y `etiqueta_origen` según el intervalo que contiene cada fila.

    Exige que los episodios de un mismo dispositivo no se pisen (data/README.md);
    si se pisan, levanta en vez de elegir uno en silencio.
    """
    out = df.copy()
    out["episodio_id"] = pd.array([pd.NA] * len(out), dtype="Int64")
    out["clase"] = pd.Series([None] * len(out), index=out.index, dtype=object)
    out["etiqueta_origen"] = pd.Series([None] * len(out), index=out.index, dtype=object)
    for disp, eps in episodios.groupby("dispositivo"):
        eps = eps.sort_values("ts_inicio")
        ini = eps.ts_inicio.values
        fin = eps.ts_fin.values
        if (ini[1:] < fin[:-1]).any():
            raise ValueError(f"episodios solapados en {disp}")
        filas = out.index[out.dispositivo == disp]
        t = out.loc[filas, col_ts].values
        k = np.searchsorted(ini, t, side="right") - 1
        ok = (k >= 0) & (t < fin[np.clip(k, 0, None)])
        idx, kk = filas[ok], k[ok]
        out.loc[idx, "episodio_id"] = eps.episodio_id.values[kk]
        out.loc[idx, "clase"] = eps.clase.values[kk]
        out.loc[idx, "etiqueta_origen"] = eps.origen.values[kk]
    return out


def _union_errores(s: pd.Series) -> str | None:
    tokens = sorted({t for v in s.dropna() for t in str(v).split("|") if t})
    return "|".join(tokens) if tokens else None


def _moda(s: pd.Series):
    s = s.dropna()
    if s.empty:
        return None
    # La moda con desempate por la última fila: en un bin que cruza un borde de
    # episodio gana el que tiene más filas, y si empatan, el más reciente.
    vc = s.value_counts(sort=False)
    mejores = vc[vc == vc.max()].index
    return s[s.isin(mejores)].iloc[-1]


def _fuente_bin(s: pd.Series):
    # Un bin es "real" sólo si todas sus filas lo son: un bin mezclado ya no es
    # una medición pura y no debe contar para el test sobre lo medido.
    otras = s[s != "real"].dropna()
    return otras.iloc[0] if len(otras) else "real"


def remuestrear_5min(df: pd.DataFrame) -> pd.DataFrame:
    """Mediana por bin de reloj de 5 min, por `(dispositivo, boot_id)`.

    Las filas deben traer `ts` y, si ya se cruzaron, `episodio_id`/`clase`/
    `etiqueta_origen`, que se resuelven por moda. Un bin es `suelo_saturado` si la mitad o más de sus filas lo son
    (entonces la mediana también está en el techo del ADC).
    """
    d = df.dropna(subset=["ts"]).copy()
    d["bin"] = d.ts.dt.floor("5min")
    d["_sat_suelo"] = (d.suelo_raw <= 0) | (d.suelo_raw >= ADC_MAX)
    d["_sat_luz"] = (d.luz_raw <= 0) | (d.luz_raw >= ADC_MAX)
    claves = ["dispositivo", "boot_id", "bin"]
    d = d.sort_values(claves + ["ts"], kind="stable")
    g = d.groupby(claves, sort=True)
    out = g[_NUMERICAS].median()
    out["n_filas"] = g.size()
    out["suelo_saturado"] = g["_sat_suelo"].mean() >= 0.5
    out["luz_saturada"] = g["_sat_luz"].mean() >= 0.5
    # Las columnas de texto se resuelven con funciones de Python, que son lentas
    # por grupo: sólo se aplican a los bins con más de una fila (el dato real a
    # 30 s). Lo que ya viene a 5 min pasa directo.
    texto = [c for c in ("errores", "episodio_id", "clase", "etiqueta_origen", "fuente")
             if c in d.columns]
    n = g["ts"].transform("size")
    unicas = d[n == 1].set_index(claves)[texto]
    multi = d[n > 1].groupby(claves, sort=True)
    agg = {"errores": _union_errores, "fuente": _fuente_bin}
    agregadas = pd.DataFrame({c: multi[c].agg(agg.get(c, _moda)) for c in texto})
    out = out.join(pd.concat([unicas, agregadas]).astype(object))
    out = out.reset_index().rename(columns={"bin": "ts"})
    if "episodio_id" in out.columns:
        out["episodio_id"] = pd.array(out.episodio_id, dtype="Int64")
    # El arranque se mide desde la primera fila cruda del boot, no desde el bin.
    arranque = d.groupby(["dispositivo", "boot_id"]).ts.min().rename("ts_arranque")
    out = out.join(arranque, on=["dispositivo", "boot_id"])
    out["min_desde_boot"] = (out.ts - out.ts_arranque).dt.total_seconds() / 60
    return out.drop(columns="ts_arranque")


def preparar(raw: pd.DataFrame, episodios: pd.DataFrame | None, fuente: str = "real",
             dudosos: dict | None = None, post_boot_min: float = POST_BOOT_MIN) -> pd.DataFrame:
    """Cruza, remuestrea y marca. **No descarta nada**: los filtros van aparte.

    Se devuelve todo para que las features se calculen sobre la serie que la
    placa realmente vio (incluidos los primeros minutos tras el arranque) y
    recién después se filtren las filas que no van al entrenamiento.
    """
    d = raw.copy()
    if "ts" not in d.columns:
        d["ts"] = elegir_hora(d)
    if episodios is not None:
        d = asignar_episodios(d, episodios)
    if "fuente" not in d.columns:
        d["fuente"] = fuente
    b = remuestrear_5min(d)
    b = b.rename(columns={"temperatura_c": "temp_c", "humedad_ambiente_pct": "hum_aire_pct"})
    # El primer bin puede empezar antes del arranque (min_desde_boot < 0): también cae.
    b["post_boot"] = b.min_desde_boot < post_boot_min
    dudosos = EPISODIOS_DUDOSOS if dudosos is None and fuente == "real" else (dudosos or {})
    b["dudoso"] = b.episodio_id.isin(list(dudosos)).fillna(False).astype(bool)
    b = b.sort_values(["dispositivo", "ts"]).reset_index(drop=True)
    return b


def filtrar(b: pd.DataFrame) -> pd.DataFrame:
    """Saca post-boot, sonda saturada y filas sin episodio."""
    m = ~b.post_boot & ~b.suelo_saturado & b.episodio_id.notna()
    return b[m].reset_index(drop=True)


COLUMNAS_SALIDA = ["ts", "dispositivo", "boot_id", "episodio_id", "clase", "etiqueta_origen",
                   "suelo_mv", "luz_mv", "temp_c", "hum_aire_pct", "temp_ntc_c", "errores",
                   "fuente", "dudoso", "n_filas", "min_desde_boot"]


def cargar_reales(snapshot: Path | str = SNAPSHOT_VIGENTE,
                  episodios: Path | str = DATOS / "episodios.csv",
                  post_boot_min: float = POST_BOOT_MIN, filtrado: bool = True) -> pd.DataFrame:
    """Muestras reales de `maceta-01` a 5 min, cruzadas con los episodios.

    Con `filtrado=False` devuelve también las filas post-boot, saturadas y sin
    episodio, con sus marcas (`post_boot`, `suelo_saturado`).
    """
    raw = leer_crudo(snapshot)
    # Sólo lo medido. Los datos simulados (firmware_version="relleno") viven sólo
    # en el archivo local y entran por dataset.serie_maceta01(); el snapshot de
    # Railway no debería traerlos nunca: el filtro es sólo una defensa.
    raw = raw[(raw.dispositivo == "maceta-01") & (raw.firmware_version != "relleno")]
    b = preparar(raw, leer_episodios(episodios), fuente="real", post_boot_min=post_boot_min)
    if filtrado:
        b = filtrar(b)
        return b[COLUMNAS_SALIDA]
    return b
