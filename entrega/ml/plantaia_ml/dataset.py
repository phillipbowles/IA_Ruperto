"""Tabla de modelado de maceta-01: features + clase + episodio, a 5 min.

Es lo que consume `notebooks/03_modelos.ipynb`:

    from plantaia_ml.dataset import serie_maceta01
    df = serie_maceta01()
    X, y, g = df[FEATURES], df.clase_codigo, df.episodio_id   # g → GroupKFold

Son las mediciones de la placa (snapshot de Railway), nada más. Las filas que
llegaron con el identificador viejo "maceta-02" se unifican al leer
(`datos_reales.unificar_maceta`).

Las features se calculan sobre la serie completa que habría visto
la placa (incluidos los primeros minutos tras cada arranque y las filas sin
episodio) y recién después se filtra: así la ventana de 1 h de cada fila es la
misma que tendría la ESP32.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import CODIGO_CLASE, DATOS, MACETA, SNAPSHOT_VIGENTE
from .datos_reales import EPISODIOS_DUDOSOS, leer_crudo, leer_episodios, preparar
from .features import FEATURES, calcular_features

COLUMNAS = (["ts", "dispositivo", "boot_id", "tramo", "episodio_id", "clase",
             "clase_codigo", "etiqueta_origen", "dudoso", "warmup", "valido", "post_boot",
             "suelo_saturado", "errores", "temp_ntc_c", "marcas"] + FEATURES)


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


def serie_maceta01(snapshot=SNAPSHOT_VIGENTE, episodios=DATOS / "episodios.csv",
                   filtrado: bool = True, incluir_warmup: bool = True) -> pd.DataFrame:
    """Serie de la maceta a 5 min, ordenada, con features, clase y episodio.

    - `filtrado`: saca filas sin vector completo, de los primeros 60 min tras
      un arranque, con la sonda saturada y sin episodio. Con `False` vienen
      todas con sus marcas.
    - `incluir_warmup`: si `False`, saca también la primera hora de cada tramo.
    - `dudoso` marca los episodios de etiqueta débil (EPISODIOS_DUDOSOS); se
      reporta con y sin ellos. `etiqueta_origen` no filtra ni marca nada.
    """
    raw = leer_crudo(snapshot)
    raw = raw[raw.dispositivo == MACETA]
    b = preparar(raw, leer_episodios(episodios), dudosos=EPISODIOS_DUDOSOS)
    df = _con_features(b)
    if filtrado:
        df = _filtrar(df, incluir_warmup)
    df = df.sort_values("ts", kind="stable").reset_index(drop=True)
    df["episodio_id"] = df.episodio_id.astype("Int64")
    return df[COLUMNAS]


# Nombre que usa el plan de la entrega (docs/ENTREGA2.md).
cargar_modelado = serie_maceta01
