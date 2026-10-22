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

Restricción de diseño (2026-10-21): el semáforo no puede depender sólo de la sonda
-----------------------------------------------------------------------------------
Todo subconjunto que prueban los candidatos tiene `suelo_mv` (idx 0) **y al
menos una feature ambiental** (`temp_c` 2, `hum_aire_pct` 3, `vpd_kpa` 4,
`luz_mv` 5, `luz_media_1h` 6). `suelo_delta_1h` (1) puede sumarse pero no
cuenta como ambiental: también sale de la sonda. Es una decisión de producto
(el LED tiene que reaccionar al ambiente de la planta, no sólo a la sonda
resistiva, que deriva), no algo que salga de las métricas: el notebook 03
compara contra el modelo sólo-suelo de la ejecución anterior (`rf-f0-c42286`)
y verifica con las filas medidas que la ambiental elegida cambia predicciones.
Los baselines (mayoritaria, umbral único y dos umbrales sobre `suelo_mv`) no
tienen búsqueda y quedan como estaban, como referencia.

X sin metadatos de etiqueta
---------------------------
`matriz_X(df)` arma la matriz de entrada **descartando explícitamente** todas
las columnas de metadatos (clase en texto, `etiqueta_origen`, `dudoso`,
`episodio_id`, `fuente`, `warmup`, `ts`, …) antes de quedarse con las 7 del
contrato §4, y verifica que no quede ninguna otra. Así la procedencia de la
etiqueta (manual, propagada, simulada, dudosa) no puede entrar al modelo.
`episodio_id` se usa sólo como grupo de la partición y `fuente` sólo para
evaluar sobre lo medido.
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

# Subconjuntos que prueba la búsqueda interna. Todos cumplen la restricción de
# diseño (docstring): suelo_mv + al menos una ambiental. Van de lo más simple
# (suelo + una ambiental) a las 7 features del contrato:
#   - suelo + cada ambiental (5),
#   - suelo + delta + cada ambiental (5),
#   - suelo + cada par de ambientales (10),
#   - "sin luz" (suelo, delta, T, HR, VPD) y "todas".
IDX_SUELO = 0
IDX_DELTA = 1
AMBIENTALES = (2, 3, 4, 5, 6)
_CORTO = {2: "temp", 3: "hr", 4: "vpd", 5: "luz", 6: "luz1h"}


def cumple_restriccion(columnas) -> bool:
    """suelo_mv y al menos una ambiental (suelo_delta_1h no cuenta como ambiental)."""
    c = set(int(i) for i in columnas)
    return IDX_SUELO in c and bool(c & set(AMBIENTALES))


def _armar_subconjuntos() -> dict[str, tuple[int, ...]]:
    from itertools import combinations
    subs = {}
    for a in AMBIENTALES:
        subs[f"suelo+{_CORTO[a]}"] = (IDX_SUELO, a)
    for a in AMBIENTALES:
        subs[f"suelo+delta+{_CORTO[a]}"] = (IDX_SUELO, IDX_DELTA, a)
    for a, b in combinations(AMBIENTALES, 2):
        subs[f"suelo+{_CORTO[a]}+{_CORTO[b]}"] = (IDX_SUELO, a, b)
    subs["sin luz"] = (0, 1, 2, 3, 4)
    subs["todas"] = tuple(range(len(FEATURES)))
    assert all(cumple_restriccion(v) for v in subs.values())
    return subs


SUBCONJUNTOS = _armar_subconjuntos()
NOMBRE_SUBCONJUNTO = {v: k for k, v in SUBCONJUNTOS.items()}


def nombre_subconjunto(columnas) -> str:
    """Nombre corto de un subconjunto (también los de los baselines, que no están en la grilla)."""
    c = tuple(int(i) for i in columnas)
    if c in NOMBRE_SUBCONJUNTO:
        return NOMBRE_SUBCONJUNTO[c]
    if c == (IDX_SUELO,):
        return "suelo"
    return "+".join(FEATURES[i] for i in c)


class SeleccionFeatures(BaseEstimator, TransformerMixin):
    """Se queda con las columnas `columnas` (índices del contrato §4)."""

    def __init__(self, columnas=tuple(range(len(FEATURES)))):
        self.columnas = columnas

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return np.asarray(X)[:, list(self.columnas)]


# Columnas de la tabla de modelado que NO son features: identificación, tiempo,
# etiqueta y su procedencia, marcas de calidad. `matriz_X` las descarta todas
# antes de armar X (las que no estén en el DataFrame se ignoran).
COLUMNAS_NO_FEATURES = [
    "ts", "ts_iso", "ts_unix", "dispositivo", "boot_id", "tramo", "muestra_id",
    "clase", "clase_codigo", "etiqueta", "etiqueta_origen", "origen", "dudoso", "nota",
    "episodio_id", "fuente", "warmup", "valido", "post_boot", "suelo_saturado",
    "errores", "marcas", "flags", "temp_ntc_c",
]


def matriz_X(df) -> np.ndarray:
    """X (float32, columnas del contrato §4 en orden) sin ningún metadato de etiqueta.

    Descarta explícitamente `COLUMNAS_NO_FEATURES` y exige que lo que queda sea
    exactamente `FEATURES`: si aparece una columna nueva que no es ni feature ni
    metadato conocido, levanta en vez de dejarla pasar en silencio.
    """
    resto = df.drop(columns=[c for c in COLUMNAS_NO_FEATURES if c in df.columns])
    if set(resto.columns) != set(FEATURES):
        raise ValueError(f"X tendría columnas fuera del contrato §4: {sorted(set(resto.columns) ^ set(FEATURES))}")
    resto = resto[FEATURES]
    assert list(resto.columns) == FEATURES
    return resto.to_numpy(np.float32)


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
    cands = {
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
    # Restricción de diseño: ningún candidato puede elegir un subconjunto sin ambiental.
    for nombre, (_, grilla) in cands.items():
        if not all(cumple_restriccion(c) for c in grilla["sel__columnas"]):
            raise AssertionError(f"{nombre}: hay subconjuntos sin feature ambiental")
    return cands


# ─── Condición de seguridad (agregada después de ver resultados) ─────────
# Decisión de producto del 2026-10-21, tomada DESPUÉS de ver que el criterio de
# §5.3 en el espacio restringido elegía un Naive Bayes que perdía la marchita
# real de octubre (ep. 12). El error caro es no avisar marchita
# (docs/ENTREGA2.md §5.1), así que un modelo para la placa tiene que cumplir,
# sobre las filas reales fuera de fold y sin dudosos:
#   - recall de marchita ≥ MIN_RECALL_MARCHITA, y
#   - el ep. 12 con ≥ MIN_ACIERTO_EP12 de sus filas bien.
# Junto con la compuerta de influencia ambiental (≥ MIN_CAMBIO_PCT % de filas
# reales cambian de clase si las ambientales van a su mediana), también fijada
# después de ver resultados. Se evalúa sobre una grilla explícita de
# configuraciones fijas (`configuraciones_seguridad`), no sobre la búsqueda
# anidada por tipo.
MIN_RECALL_MARCHITA = 0.9
MIN_ACIERTO_EP12 = 0.5
EP_MARCHITA_OCTUBRE = 12
MIN_CAMBIO_PCT = 1.0


def configuraciones_seguridad() -> list[tuple[str, dict]]:
    """Grilla explícita: suelo + cada ambiental y suelo + cada par de ambientales, con
    regresión logística (C 0,01/0,1/1), árbol (prof. 2/3/4, hoja 100), RF chico de 30
    árboles (prof. 3/5, hoja 20/100) y Naive Bayes. 165 configuraciones."""
    from itertools import combinations
    subs = [(IDX_SUELO, a) for a in AMBIENTALES] + [(IDX_SUELO, a, b) for a, b in combinations(AMBIENTALES, 2)]
    out = []
    for s in subs:
        for c in (0.01, 0.1, 1.0):
            out.append(("Regresión logística", {"sel__columnas": s, "clf__C": c}))
        for d in (2, 3, 4):
            out.append(("Árbol de decisión", {"sel__columnas": s, "clf__max_depth": d, "clf__min_samples_leaf": 100}))
        for d in (3, 5):
            for h in (20, 100):
                out.append(("Random Forest", {"sel__columnas": s, "clf__max_depth": d, "clf__min_samples_leaf": h}))
        out.append(("Naive Bayes", {"sel__columnas": s}))
    assert all(cumple_restriccion(p["sel__columnas"]) for _, p in out)
    return out


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
# configuración. Con la restricción de diseño (suelo + al menos una ambiental)
# ese criterio elegía un Naive Bayes `suelo+temp` (`nb-f02-fa0df4`) que perdía la
# marchita real de octubre. Con la condición de seguridad (ver arriba; agregada
# después de ver resultados) y la compuerta de influencia ambiental, la elección
# sale de `configuraciones_seguridad()` en el notebook 03 §5.6: un Random Forest
# de 30 árboles con suelo_mv y vpd_kpa. Antes de la restricción ganaba un RF
# sólo con suelo_mv (`rf-f0-c42286`).
CONFIG_FINAL = {
    "tipo": "Random Forest",
    "params": {"sel__columnas": (0, 4), "clf__max_depth": 5, "clf__min_samples_leaf": 20},
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
