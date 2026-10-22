"""Candidatos, protocolo de evaluación y costo en la ESP32 (docs/ENTREGA2.md §5).

Lo usa `notebooks/03_modelos.ipynb` y `exportar_c.py`. Lo que vive acá es lo
que tiene que ser igual en los dos lados: la definición de cada candidato, la
partición por episodio, la estimación de costo y la configuración del modelo
que va a la placa.

Protocolo
---------
- Partición **por episodio**: un episodio entero queda en train o en test,
  nunca partido (las filas contiguas comparten etiqueta y están muy
  correlacionadas; ver CLAUDE.md). Se usa `StratifiedGroupKFold`, que es
  `GroupKFold` repartiendo los episodios para que cada fold tenga las tres
  clases: con `GroupKFold` a secas uno de los 5 folds se queda sin ningún
  episodio `marchita` y el recall de esa clase no se puede medir ahí.
- Hiperparámetros con búsqueda **anidada**: adentro de cada fold externo,
  `GridSearchCV` con otra partición por episodio (3 folds) sobre el train.
  El fold externo nunca participa de la elección.
- El subconjunto de features es un hiperparámetro más (`sel__columnas`): la
  placa arma siempre los 7 y el modelo usa los que eligió la búsqueda.
"""
from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin, clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from .features import FEATURES

SEMILLA = 0
K_EXTERNO = 5
K_INTERNO = 3

# Subconjuntos que prueba la búsqueda interna. Van de lo más simple (sólo la
# sonda) a las 7 features del contrato. "sin luz" saca las dos de luz, que son
# las que más arrastran el ciclo día/noche.
SUBCONJUNTOS = {
    "suelo": (0,),
    "suelo+delta": (0, 1),
    "sin luz": (0, 1, 2, 3, 4),
    "todas": tuple(range(len(FEATURES))),
}
NOMBRE_SUBCONJUNTO = {v: k for k, v in SUBCONJUNTOS.items()}


class SeleccionFeatures(BaseEstimator, TransformerMixin):
    """Se queda con las columnas `columnas` (índices del contrato §4)."""

    def __init__(self, columnas=tuple(range(len(FEATURES)))):
        self.columnas = columnas

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return np.asarray(X)[:, list(self.columnas)]


def particion_externa():
    return StratifiedGroupKFold(n_splits=K_EXTERNO, shuffle=True, random_state=SEMILLA)


def particion_interna():
    return StratifiedGroupKFold(n_splits=K_INTERNO, shuffle=True, random_state=SEMILLA + 1)


def _pipe(*pasos, escalar=False):
    p = [("sel", SeleccionFeatures())]
    if escalar:
        p.append(("esc", StandardScaler()))
    p.extend(pasos)
    return Pipeline(p)


_SUBS = list(SUBCONJUNTOS.values())


def candidatos() -> dict[str, tuple[Pipeline, dict]]:
    """Los 7 candidatos del plan (§5.2) con su grilla de hiperparámetros."""
    cw = "balanced"   # la serie tiene ~2 saludable por cada marchita
    return {
        "Regresión logística": (
            _pipe(("clf", LogisticRegression(max_iter=3000, class_weight=cw)), escalar=True),
            {"sel__columnas": _SUBS, "clf__C": [0.01, 0.1, 1.0]}),
        "Árbol de decisión": (
            _pipe(("clf", DecisionTreeClassifier(class_weight=cw, random_state=SEMILLA))),
            {"sel__columnas": _SUBS, "clf__max_depth": [2, 3, 4, 6, 8],
             "clf__min_samples_leaf": [20, 100]}),
        "Random Forest": (
            _pipe(("clf", RandomForestClassifier(n_estimators=30, class_weight=cw,
                                                 random_state=SEMILLA, n_jobs=1))),
            {"sel__columnas": _SUBS, "clf__max_depth": [3, 5, 8],
             "clf__min_samples_leaf": [20, 100]}),
        "Naive Bayes": (
            _pipe(("clf", GaussianNB())),
            {"sel__columnas": _SUBS}),
        "k-NN": (
            _pipe(("clf", KNeighborsClassifier()), escalar=True),
            {"sel__columnas": _SUBS, "clf__n_neighbors": [5, 25, 101]}),
        "SVM RBF": (
            _pipe(("clf", SVC(class_weight=cw, probability=False)), escalar=True),
            {"sel__columnas": _SUBS, "clf__C": [0.1, 1.0, 10.0]}),
        "MLP": (
            _pipe(("clf", MLPClassifier(max_iter=500, early_stopping=True,
                                        random_state=SEMILLA)), escalar=True),
            {"sel__columnas": _SUBS, "clf__hidden_layer_sizes": [(8,), (16, 8)],
             "clf__alpha": [1e-3, 1e-1]}),
    }


# ─── Baselines obligatorios (§5.1) ────────────────────────────────────────
class UmbralesOrdenados(ClassifierMixin, BaseEstimator):
    """Regla escrita a mano sobre una sola columna (por defecto `suelo_mv`).

    `x <= t1` → saludable, `t1 < x <= t2` → estresada, `x > t2` → marchita
    (la sonda es resistiva: más seco = más mV). Lo único que se ajusta son
    t1 < t2, eligiendo entre los cuantiles 5–95 % del train el par que da
    mejor F1 macro en el train. Es lo que haría alguien que mira el
    histograma y pone dos cortes: si un modelo no le gana a esto, no aporta.
    """

    def __init__(self, columna: int = 0, n_cuantiles: int = 37):
        self.columna = columna
        self.n_cuantiles = n_cuantiles

    def fit(self, X, y):
        s = np.asarray(X, dtype=float)[:, self.columna]
        y = np.asarray(y, dtype=int)
        self.classes_ = np.array([1, 2, 3])
        cand = np.unique(np.quantile(s, np.linspace(0.05, 0.95, self.n_cuantiles)))
        mejor = (-1.0, cand[0], cand[-1])
        for i, t1 in enumerate(cand):
            for t2 in cand[i + 1:]:
                f1 = _f1_macro(y, self._regla(s, t1, t2))
                if f1 > mejor[0]:
                    mejor = (f1, t1, t2)
        self.f1_train_, self.t1_, self.t2_ = mejor
        return self

    @staticmethod
    def _regla(s, t1, t2):
        return np.where(s <= t1, 1, np.where(s <= t2, 2, 3))

    def predict(self, X):
        return self._regla(np.asarray(X, dtype=float)[:, self.columna], self.t1_, self.t2_)


def _f1_macro(y, p, clases=(1, 2, 3)) -> float:
    f1 = []
    for c in clases:
        tp = np.sum((p == c) & (y == c))
        den = np.sum(p == c) + np.sum(y == c)
        f1.append(2 * tp / den if den else 0.0)
    return float(np.mean(f1))


def baselines() -> dict[str, tuple[Pipeline, dict]]:
    """Baselines de §5.1, con la misma forma que `candidatos()` (grilla vacía = sin búsqueda).

    - Clase mayoritaria: predice siempre `saludable`.
    - Umbral único sobre `suelo_mv`: un tocón (árbol de profundidad 1). Con un
      solo corte predice dos clases como mucho; es el baseline literal del plan.
    - Dos umbrales sobre `suelo_mv`: la regla ordinal de `UmbralesOrdenados`,
      que sí puede dar las tres clases.
    """
    return {
        "Clase mayoritaria": (_pipe(("clf", DummyClassifier(strategy="most_frequent"))), {}),
        "Umbral único (suelo_mv)": (
            _pipe(("clf", DecisionTreeClassifier(max_depth=1, class_weight="balanced",
                                                 random_state=SEMILLA)))
            .set_params(sel__columnas=(0,)), {}),
        "Dos umbrales (suelo_mv)": (
            _pipe(("clf", UmbralesOrdenados())).set_params(sel__columnas=(0,)), {}),
    }


def busqueda(est: Pipeline, grilla: dict, n_jobs: int = -1) -> GridSearchCV:
    """GridSearchCV con partición interna por episodio (hay que pasar `groups` al fit)."""
    return GridSearchCV(clone(est), grilla, cv=particion_interna(), scoring="f1_macro",
                        n_jobs=n_jobs, error_score="raise")


# ─── Modelo que va a la placa ─────────────────────────────────────────────
# Lo elige el notebook 03 (§5.3: costo, F1 por episodio en la serie completa y
# puntaje sobre los episodios reales; desempate por interpretabilidad) y, dentro
# del tipo, la configuración más simple a 1 desvío de la mejor de la búsqueda
# por episodio sobre la serie completa. El notebook avisa si esto deja de
# coincidir, y `python -m plantaia_ml.exportar_c` lo reentrena con esta
# configuración. Con el relleno v2 (2026-10-21) gana un Random Forest de 30
# árboles sólo con suelo_mv (la versión anterior, con el relleno v1, era un
# árbol de profundidad 2).
CONFIG_FINAL = {
    "tipo": "Random Forest",
    "params": {"sel__columnas": (0,), "clf__max_depth": 5, "clf__min_samples_leaf": 20},
}


def modelo_final() -> Pipeline:
    est, _ = candidatos()[CONFIG_FINAL["tipo"]]
    return clone(est).set_params(**CONFIG_FINAL["params"])


# ─── Costo en la ESP32 ────────────────────────────────────────────────────
# Estimaciones a partir de los parámetros del modelo entrenado, con la forma
# en que los guardaría un header C sin librerías (floats de 4 B en flash).
# Tiempo: ESP32 a 240 MHz con FPU de precisión simple; se cuentan ~10 ciclos
# por operación (carga + operación + control de lazo) y ~1 µs por expf. Es un
# orden de magnitud para comparar, no una medición: la del modelo elegido sale
# del log de la placa (t_us).
_CICLOS_POR_OP = 10
_MHZ = 240
_US_POR_EXP = 1.0


def _nodos_arbol(t):
    tr = t.tree_
    hojas = int((tr.children_left == -1).sum())
    return tr.node_count, hojas, tr.max_depth


def costo_esp32(modelo: Pipeline) -> dict:
    """Flash (B), RAM de inferencia (B), operaciones, exps, µs estimados, exportable."""
    clf = modelo.named_steps["clf"]
    d = len(modelo.named_steps["sel"].columnas)
    esc = 2 * d * 4 if "esc" in modelo.named_steps else 0   # media y desvío
    ops_esc = 2 * d if esc else 0
    if isinstance(clf, DummyClassifier):
        flash, ram, ops, exps = 4, 0, 0, 0
        exportable = "sí (constante)"
    elif isinstance(clf, UmbralesOrdenados):
        flash, ram, ops, exps = 8, 0, 2, 0
        exportable = "sí (dos if)"
    elif isinstance(clf, DecisionTreeClassifier):
        n, h, prof = _nodos_arbol(clf)
        # Por nodo: feature (1 B) + umbral (4) + hijos (2+2); por hoja, 3 probas.
        flash, ram, ops, exps = n * 9 + h * 12, 16, prof * 2, 0
        exportable = "sí (if/else o tablas)"
    elif isinstance(clf, RandomForestClassifier):
        partes = [_nodos_arbol(t) for t in clf.estimators_]
        flash = sum(n * 9 + h * 12 for n, h, _ in partes)
        ram, ops, exps = 28, sum(p * 2 for _, _, p in partes) + 3 * len(partes), 0
        exportable = "sí (tablas)"
    elif isinstance(clf, LogisticRegression):
        k = clf.coef_.shape[0]
        flash = (clf.coef_.size + k) * 4 + esc
        ram, ops, exps = d * 4 + 12, ops_esc + 2 * clf.coef_.size + 3 * k, 3
        exportable = "sí (producto matriz-vector)"
    elif isinstance(clf, GaussianNB):
        flash = (clf.theta_.size + clf.var_.size + len(clf.classes_)) * 4
        ram, ops, exps = 12, 4 * clf.theta_.size + 3, 3
        exportable = "sí (fórmula cerrada)"
    elif isinstance(clf, KNeighborsClassifier):
        n_tr = clf.n_samples_fit_
        flash = n_tr * d * 4 + n_tr + esc       # todo el train + su clase
        ram, ops, exps = clf.n_neighbors * 8 + 16, ops_esc + n_tr * (3 * d + 2), 0
        exportable = "sí, pero guarda todo el train"
    elif isinstance(clf, SVC):
        n_sv = clf.support_vectors_.shape[0]
        flash = (n_sv * d + clf.dual_coef_.size + clf.intercept_.size) * 4 + esc
        ram, ops, exps = 3 * 4 + 16, ops_esc + n_sv * (3 * d + 4), n_sv
        exportable = "sí, pero guarda los vectores soporte"
    elif isinstance(clf, MLPClassifier):
        w = sum(c.size for c in clf.coefs_) + sum(b.size for b in clf.intercepts_)
        ancho = max(c.shape[1] for c in clf.coefs_)
        flash = w * 4 + esc
        ram, ops, exps = 2 * ancho * 4, ops_esc + 2 * w, 3
        exportable = "sí (capas densas)"
    else:
        raise TypeError(type(clf))
    t_us = ops * _CICLOS_POR_OP / _MHZ + exps * _US_POR_EXP
    return {"flash_B": int(flash), "ram_B": int(ram), "ops": int(ops), "exps": int(exps),
            "t_us_est": float(t_us), "exportable": exportable}
