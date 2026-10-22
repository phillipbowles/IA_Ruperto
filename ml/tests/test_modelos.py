"""Tests de modelos.py: restricción de diseño y X sin metadatos de etiqueta.

    /opt/anaconda3/bin/python -m pytest ml/tests
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plantaia_ml.features import FEATURES  # noqa: E402
from plantaia_ml.modelos import (AMBIENTALES, CONFIG_FINAL, SUBCONJUNTOS, candidatos,  # noqa: E402
                                 cumple_restriccion, matriz_X)


def test_regla_de_la_restriccion():
    assert not cumple_restriccion((0,))
    assert not cumple_restriccion((0, 1))          # delta sale de la sonda: no es ambiental
    assert not cumple_restriccion((2, 3, 4))       # sin la sonda
    assert cumple_restriccion((0, 4))
    assert cumple_restriccion((0, 1, 6))
    assert set(AMBIENTALES) == {2, 3, 4, 5, 6}


def test_todos_los_subconjuntos_y_candidatos_cumplen():
    assert all(cumple_restriccion(v) for v in SUBCONJUNTOS.values())
    for nombre, (_, grilla) in candidatos().items():
        assert all(cumple_restriccion(c) for c in grilla["sel__columnas"]), nombre


def test_config_final_usa_ambiental():
    assert cumple_restriccion(CONFIG_FINAL["params"]["sel__columnas"])


def _tabla(n=4):
    d = {f: np.arange(n, dtype=float) + i for i, f in enumerate(FEATURES)}
    meta = {"ts": pd.date_range("2026-10-01", periods=n, freq="5min", tz="UTC"), "clase": "saludable",
            "clase_codigo": 1, "etiqueta_origen": "manual", "dudoso": False, "episodio_id": 7,
            "fuente": "real", "warmup": False, "valido": True}
    # Metadatos primero y features desordenadas: matriz_X tiene que devolver el orden del contrato.
    return pd.DataFrame({**meta, **dict(reversed(list(d.items())))})


def test_matriz_x_descarta_metadatos_y_respeta_el_orden():
    df = _tabla()
    X = matriz_X(df)
    assert X.dtype == np.float32 and X.shape == (4, len(FEATURES))
    np.testing.assert_array_equal(X[:, 0], df.suelo_mv.to_numpy(np.float32))
    np.testing.assert_array_equal(X[:, 6], df.luz_media_1h.to_numpy(np.float32))


def test_matriz_x_rechaza_columnas_desconocidas():
    df = _tabla().assign(hora_local=3)
    with pytest.raises(ValueError):
        matriz_X(df)
