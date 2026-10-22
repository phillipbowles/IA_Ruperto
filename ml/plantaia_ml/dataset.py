"""Tabla de modelado de maceta-01: features + clase + episodio, a 5 min.

Es lo que consume `notebooks/03_modelos.ipynb`:

    from plantaia_ml.dataset import serie_maceta01
    df = serie_maceta01()
    X, y, g = df[FEATURES], df.clase_codigo, df.episodio_id   # g → GroupKFold

Hay dos orígenes de filas, los dos con `dispositivo='maceta-01'`:

- `fuente == 'real'`: lo que midió la placa (snapshot de Railway).
- `fuente == 'simulada_relleno'`: **datos simulados (calibrados con lo
  medido)** que completan los tramos sin registro de la placa (ver
  data/README.md). Entran al entrenamiento igual que las demás, sin filtro,
  peso ni marca de dudosa.

Los datos simulados vienen SÓLO del archivo local `data/sintetico/
payloads_relleno.jsonl` (gitignored), con sus episodios de
`episodios_relleno.csv`; nunca se mandan a Railway (docs/ENTREGA2.md §7). El
archivo se convierte al esquema crudo y pasa por el mismo remuestreo a 5 min
que las mediciones. Se reconocen por cualquiera de sus dos marcas:
`firmware_version='relleno'` (la que usa este módulo) y
`etiqueta_origen='simulada'` (valor propio; `corregida` es sólo el
reetiquetado humano desde el front). Si una fila del snapshot de Railway trae
alguna de las dos marcas, `serie_maceta01` levanta un error: no debería pasar.

Para reportar sobre lo medido, filtrar siempre por `fuente`, nunca por
dispositivo. Las features se calculan sobre la serie completa que habría visto
la placa (incluidos los primeros minutos tras cada arranque y las filas sin
episodio) y recién después se filtra: así la ventana de 1 h de cada fila es la
misma que tendría la ESP32.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from . import CODIGO_CLASE, DATOS, SNAPSHOT_VIGENTE
from .datos_reales import (EPISODIOS_DUDOSOS, asignar_episodios, leer_crudo, leer_episodios,
                           preparar)
from .features import FEATURES, calcular_features

# Carpeta del relleno local. Por defecto data/sintetico/; la variable de entorno
# PLANTAIA_SINTETICO la cambia (p. ej. data/sintetico_v2 para probar una versión
# regenerada sin pisar la vigente).
_CARPETA_LOCAL = (Path(os.environ["PLANTAIA_SINTETICO"]).resolve() if os.environ.get("PLANTAIA_SINTETICO")
                  else DATOS / "sintetico")
RUTA_PAYLOADS = _CARPETA_LOCAL / "payloads_relleno.jsonl"
RUTA_EP_COMPLEMENTO = _CARPETA_LOCAL / "episodios_relleno.csv"
FIRMWARE_RELLENO = "relleno"
ORIGEN_SIMULADA = "simulada"
FUENTE_RELLENO = "simulada_relleno"

COLUMNAS = (["ts", "dispositivo", "boot_id", "tramo", "fuente", "episodio_id", "clase",
             "clase_codigo", "etiqueta_origen", "dudoso", "warmup", "valido", "post_boot",
             "suelo_saturado", "errores", "temp_ntc_c", "marcas"] + FEATURES)


def leer_payloads(ruta=RUTA_PAYLOADS) -> pd.DataFrame:
    """JSONL con el esquema de MedicionIn → filas con el esquema del CSV crudo.

    Reproduce lo que hace el backend al guardar: `ts_dispositivo` desde el
    unix epoch y `errores` unidos con "|" (como en el CSV de Railway).
    """
    with open(ruta, encoding="utf-8") as f:
        d = pd.DataFrame([json.loads(linea) for linea in f if linea.strip()])
    ts = pd.to_datetime(d.pop("ts_dispositivo_unix"), unit="s", utc=True)
    d["ts_dispositivo"] = ts.dt.strftime("%Y-%m-%d %H:%M:%S+00:00")
    d["ts_servidor"] = d["ts_dispositivo"]
    d["errores"] = d.errores.map(lambda e: "|".join(e) if e else np.nan)
    d["suelo_pct"] = d.suelo_pct.astype(float)
    d["id"] = d.numero_muestra
    d["ts"] = ts
    return d


def _con_features(b: pd.DataFrame) -> pd.DataFrame:
    # Sonda saturada = faltante para la placa (main.cpp pasa NAN): se repite el
    # valor anterior del buffer en vez de meter 3124 mV en la ventana.
    entrada = b.assign(suelo_mv=b.suelo_mv.where(~b.suelo_saturado))
    f = calcular_features(entrada)
    out = b.drop(columns=[c for c in FEATURES if c in b.columns]).join(f)
    out["clase_codigo"] = out.clase.map(CODIGO_CLASE).astype("Int64")
    return out


def _filtrar(df: pd.DataFrame, incluir_warmup: bool) -> pd.DataFrame:
    m = df.valido & ~df.post_boot & ~df.suelo_saturado & df.episodio_id.notna()
    if not incluir_warmup:
        m &= ~df.warmup
    return df[m]


def _verificar_snapshot_sin_simulados(raw: pd.DataFrame) -> None:
    """El snapshot de Railway sólo tiene mediciones: los datos simulados viven en el archivo local."""
    simuladas = raw.firmware_version.eq(FIRMWARE_RELLENO)
    if "etiqueta_origen" in raw.columns:
        simuladas |= raw.etiqueta_origen.eq(ORIGEN_SIMULADA)
    if simuladas.any():
        raise ValueError(
            f"El snapshot de Railway trae {int(simuladas.sum())} filas marcadas como simuladas "
            f"(firmware_version={FIRMWARE_RELLENO!r} o etiqueta_origen={ORIGEN_SIMULADA!r}). "
            "Los datos simulados no van a Railway (docs/ENTREGA2.md §7): sólo se leen de "
            f"{RUTA_PAYLOADS}.")


def serie_maceta01(snapshot=SNAPSHOT_VIGENTE, episodios=DATOS / "episodios.csv",
                   incluir_complemento: bool = True, filtrado: bool = True,
                   incluir_warmup: bool = True) -> pd.DataFrame:
    """Serie de maceta-01 a 5 min, ordenada, con features, clase y episodio.

    - `incluir_complemento`: suma los datos simulados del archivo local
      (`firmware_version='relleno'`). Con `False`, sólo lo medido.
    - `filtrado`: saca filas sin vector completo, de los primeros 30 min tras
      un arranque, con la sonda saturada y sin episodio. Con `False` vienen
      todas con sus marcas.
    - `incluir_warmup`: si `False`, saca también la primera hora de cada tramo.
    - `dudoso` marca los episodios de etiqueta débil (EPISODIOS_DUDOSOS); se
      reporta con y sin ellos. `etiqueta_origen` no filtra ni marca nada.
    """
    ep = leer_episodios(episodios)
    raw = leer_crudo(snapshot)
    _verificar_snapshot_sin_simulados(raw)
    raw = raw[raw.dispositivo == "maceta-01"]
    if incluir_complemento and RUTA_PAYLOADS.exists():
        raw = pd.concat([raw, leer_payloads()], ignore_index=True)
    if incluir_complemento and RUTA_EP_COMPLEMENTO.exists():
        extra = leer_episodios(RUTA_EP_COMPLEMENTO)
        ep = pd.concat([ep, extra[~extra.episodio_id.isin(ep.episodio_id)]], ignore_index=True)
    raw = asignar_episodios(raw.reset_index(drop=True), ep)
    raw["fuente"] = np.where(raw.firmware_version == FIRMWARE_RELLENO, FUENTE_RELLENO, "real")
    b = preparar(raw, None, fuente="real", dudosos=EPISODIOS_DUDOSOS)
    df = _con_features(b)
    if filtrado:
        df = _filtrar(df, incluir_warmup)
    df = df.sort_values("ts", kind="stable").reset_index(drop=True)
    df["episodio_id"] = df.episodio_id.astype("Int64")
    return df[COLUMNAS]


# Nombre que usa el plan de la entrega (docs/ENTREGA2.md).
cargar_modelado = serie_maceta01
