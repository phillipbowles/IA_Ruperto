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
    assert cumple_restriccion((0,))                  # sólo la sonda: permitido desde el 2026-10-23
    assert cumple_restriccion((0, 7))                # sonda + horas desde el riego
    assert not cumple_restriccion((2, 3, 4))         # sin la sonda
    assert not cumple_restriccion((0, 6))            # luz: proxy de la hora del observador
    assert not cumple_restriccion((0, 4, 5))
    assert set(AMBIENTALES) == {2, 3, 4}


def test_todos_los_subconjuntos_y_candidatos_cumplen():
    assert all(cumple_restriccion(v) for v in SUBCONJUNTOS.values())
    for nombre, (est, grilla) in candidatos().items():
        subs = grilla.get("sel__columnas", [est.named_steps["sel"].columnas])
        assert all(cumple_restriccion(c) for c in subs), nombre


def test_config_final_cumple():
    assert cumple_restriccion(CONFIG_FINAL["params"]["sel__columnas"])


def test_regla_sonda_riego():
    from plantaia_ml.modelos import ReglaSueloRiego
    rng = np.random.default_rng(0)
    suelo = np.r_[rng.uniform(1450, 1700, 300), rng.uniform(1750, 1930, 300), rng.uniform(1950, 2000, 100),
                  rng.uniform(1480, 1530, 60)]
    riego = np.r_[np.full(700, 96.0), rng.uniform(0, 5, 60)]
    y = np.r_[np.full(300, 1), np.full(300, 2), np.full(100, 3), np.full(60, 2)]
    X = np.c_[suelo, riego]
    m = ReglaSueloRiego().fit(X, y)
    assert 1700 <= m.t1_ <= 1760 and 1925 <= m.t2_ <= 1955   # cuantiles dentro de los huecos entre clases
    assert m.h_riego_ is not None and m.h_riego_ >= 5
    assert (m.predict(X) == y).mean() > 0.99
    # tree_ coherente con la regla: misma clase recorriendo los nodos
    assert (m.predict_proba(X).argmax(1) + 1 == m.predict(X)).all()
    assert m.get_depth() == 3


def _tabla(n=4):
    d = {f: np.arange(n, dtype=float) + i for i, f in enumerate(FEATURES)}
    meta = {"ts": pd.date_range("2026-10-01", periods=n, freq="5min", tz="UTC"), "clase": "saludable",
            "clase_codigo": 1, "etiqueta_origen": "manual", "dudoso": False, "episodio_id": 7,
            "warmup": False, "valido": True}
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
