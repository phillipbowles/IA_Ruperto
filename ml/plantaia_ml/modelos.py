"""Candidatos, protocolo de evaluación y costo en la ESP32 (docs/ENTREGA2.md §5).

Lo usa `notebooks/03_modelos.ipynb` y `exportar_c.py`. Lo que vive acá es lo
que tiene que ser igual en los dos lados: la definición de cada candidato, la
partición por episodio, la estimación de costo y la configuración del modelo
que va a la placa.

Protocolo
---------
- Partición **por episodio**: un episodio entero queda en train o en test,
  nunca partido (las filas contiguas comparten etiqueta y están muy
  correlacionadas; ver CLAUDE.md). `StratifiedGroupKFold` k=5. Las métricas se
  calculan sobre las predicciones fuera de fold juntas, con desvío por
  bootstrap de episodios.
- **Se entrena sin los episodios dudosos** (`EPISODIOS_DUDOSOS`) y se evalúa
  con y sin ellos. Con los dudosos en el train el modelo aprende sus etiquetas
  (el ep. 14, `estresada` arrastrada 25 h tras un riego, enseñaba un corte de
  "25 h desde el riego"): decisión del 2026-10-23.
- Hiperparámetros con búsqueda **anidada** (otra partición por episodio, k=3,
  sobre el train). El subconjunto de features es un hiperparámetro más
  (`sel__columnas`): la placa arma siempre los 8 y el modelo usa los que eligió.

Restricción de features (2026-10-23)
------------------------------------
Todo subconjunto lleva `suelo_mv` y **ninguno lleva luz** (`IDX_LUZ`): con la
luz el modelo aprendía "oscuro → marchita" (la hora del observador). Hasta el
2026-10-23 se exigía además una variable del aire (T, HR o VPD); se sacó
porque en los datos el aire casi no varía (18–22 °C, 44–55 % de HR en
octubre) y la exigencia sólo costaba F1 (notebook 03, §5).

X sin metadatos de etiqueta
---------------------------
`matriz_X(df)` descarta explícitamente las columnas de metadatos (clase,
`etiqueta_origen`, `dudoso`, `episodio_id`, `warmup`, `ts`, …) y exige que
quede exactamente el contrato §4. `episodio_id` sólo es el grupo de la
partición y `dudoso` sólo decide qué filas entrenan y cómo se reporta.
"""
from __future__ import annotations

from types import SimpleNamespace

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

IDX_SUELO = 0
IDX_DELTA = 1
IDX_LUZ = (5, 6)
AMBIENTALES = (2, 3, 4)
IDX_RIEGO = 7
_CORTO = {1: "delta", 2: "temp", 3: "hr", 4: "vpd", 5: "luz", 6: "luz1h", 7: "riego"}


def cumple_restriccion(columnas) -> bool:
    """Tiene `suelo_mv` y nada de luz."""
    c = set(int(i) for i in columnas)
    return IDX_SUELO in c and not c & set(IDX_LUZ)


def _armar_subconjuntos() -> dict[str, tuple[int, ...]]:
    """suelo; suelo + una de (delta, T, HR, VPD, riego); suelo + riego + una ambiental;
    "sin luz" (las 6 sin luz). 10 subconjuntos."""
    subs = {"suelo": (IDX_SUELO,)}
    for a in (IDX_DELTA, *AMBIENTALES, IDX_RIEGO):
        subs[f"suelo+{_CORTO[a]}"] = (IDX_SUELO, a)
    for a in AMBIENTALES:
        subs[f"suelo+riego+{_CORTO[a]}"] = (IDX_SUELO, a, IDX_RIEGO)
    subs["sin luz"] = (0, 1, 2, 3, 4, 7)
    assert all(cumple_restriccion(v) for v in subs.values())
    return subs


SUBCONJUNTOS = _armar_subconjuntos()
NOMBRE_SUBCONJUNTO = {v: k for k, v in SUBCONJUNTOS.items()}


def nombre_subconjunto(columnas) -> str:
    """Nombre corto de un subconjunto (también los de los baselines, que no están en la grilla)."""
    c = tuple(int(i) for i in columnas)
    if c in NOMBRE_SUBCONJUNTO:
        return NOMBRE_SUBCONJUNTO[c]
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
    "episodio_id", "warmup", "valido", "post_boot", "suelo_saturado",
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
    """Los candidatos del plan (§5.2) + la regla sonda + riego, con su grilla."""
    cw = "balanced"   # hay ~3 filas saludable/estresada por cada marchita
    cands = {
        "Regla sonda + riego": (
            _pipe(("clf", ReglaSueloRiego())).set_params(sel__columnas=(IDX_SUELO, IDX_RIEGO)), {}),
        "Regresión logística": (
            _pipe(("clf", LogisticRegression(max_iter=3000, class_weight=cw)), escalar=True),
            {"sel__columnas": _SUBS, "clf__C": [0.01, 0.1, 1.0]}),
        "Árbol de decisión": (
            _pipe(("clf", DecisionTreeClassifier(class_weight=cw, random_state=SEMILLA))),
            {"sel__columnas": _SUBS, "clf__max_depth": [2, 3, 4, 6],
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
    for nombre, (est, grilla) in cands.items():
        subs = grilla.get("sel__columnas", [est.named_steps["sel"].columnas])
        if not all(cumple_restriccion(c) for c in subs):
            raise AssertionError(f"{nombre}: hay subconjuntos sin suelo o con luz")
    return cands


# ─── Condición de seguridad (se reporta, ver notebook §5) ─────────────────
# El error caro es no avisar marchita. Se reporta si el elegido cumple, sobre
# las filas fuera de fold sin dudosos: recall de marchita ≥ MIN_RECALL_MARCHITA
# y el ep. 12 (la marchita nocturna del 19/10) con ≥ MIN_ACIERTO_EP12 bien.
MIN_RECALL_MARCHITA = 0.9
MIN_ACIERTO_EP12 = 0.5
EP_MARCHITA_OCTUBRE = 12


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
    """GridSearchCV con partición interna por episodio (hay que pasar `groups` al fit).

    Con tan pocos episodios reales, algún fold interno puede quedar con una sola
    clase en el train: esa configuración puntúa NaN en ese fold en vez de cortar.
    """
    return GridSearchCV(clone(est), grilla, cv=particion_interna(), scoring="f1_macro",
                        n_jobs=n_jobs, error_score=np.nan)


# ─── Regla sonda + riego (candidato, 2026-10-23) ──────────────────────────
class ReglaSueloRiego(ClassifierMixin, BaseEstimator):
    """Dos umbrales sobre la sonda + "poco después de un riego → estresada".

    Entra X con dos columnas: `suelo_mv` y `h_desde_riego` (en ese orden, la
    pipeline hace la selección). La regla, en el orden en que se evalúa:

        h_desde_riego <= h_riego      → estresada (la planta tarda en recuperar
                                        turgencia después de regar)
        suelo_mv <= t1                → saludable
        suelo_mv <= t2                → estresada
        si no                         → marchita

    t1 < t2 son los de `UmbralesOrdenados` sobre el train; `h_riego` se elige
    en `HORAS` por F1 macro en el train (None = sin regla de riego). Expone
    `tree_` con la misma forma que un árbol de sklearn (nodos, umbrales,
    `value` = proporción de clases del train en cada hoja), así el exportador
    a C, los vectores de paridad y el dashboard la tratan como un árbol.
    """

    HORAS = (None, 1.0, 2.0, 3.0, 4.0, 4.5, 5.5, 6.0, 8.0, 12.0)

    def __init__(self, n_cuantiles: int = 37):
        self.n_cuantiles = n_cuantiles

    @property
    def max_depth(self):
        return self.get_depth() if hasattr(self, "tree_") else None

    def get_depth(self):
        return int(self.tree_.max_depth)

    def _regla(self, X, h_riego):
        X = np.asarray(X, dtype=float)
        p = UmbralesOrdenados._regla(X[:, 0], self.t1_, self.t2_)
        if h_riego is not None:
            p = np.where(X[:, 1] <= h_riego, 2, p)
        return p

    def fit(self, X, y):
        self.__dict__.pop("tree_", None)   # un refit no puede recorrer el árbol anterior
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=int)
        self.classes_ = np.array([1, 2, 3])
        base = UmbralesOrdenados(columna=0, n_cuantiles=self.n_cuantiles).fit(X, y)
        self.t1_, self.t2_ = float(base.t1_), float(base.t2_)
        puntajes = [(_f1_macro(y, self._regla(X, h)), h) for h in self.HORAS]
        mejor = max(p for p, _ in puntajes)
        # Entre las que empatan, la sin regla o la de menos horas (la más conservadora).
        self.h_riego_ = next(h for p, h in puntajes if p == mejor)
        self._armar_arbol(X, y)
        return self

    def _armar_arbol(self, X, y):
        # (feature en X, umbral) de los nodos internos y clase de cada hoja, en preorden.
        internos = [] if self.h_riego_ is None else [(1, self.h_riego_)]
        internos += [(0, self.t1_), (0, self.t2_)]
        izq, der, feat, umb, hojas = [], [], [], [], []
        # Cadena: cada nodo interno tiene una hoja a la izquierda y el siguiente a la derecha.
        clases_izq = ([2] if self.h_riego_ is not None else []) + [1, 2]
        nodo = 0
        for k, (f, u) in enumerate(internos):
            feat.append(f); umb.append(u); izq.append(nodo + 1); der.append(nodo + 2)
            hojas.append((nodo + 1, clases_izq[k]))
            feat.append(-2); umb.append(-2.0); izq.append(-1); der.append(-1)
            nodo += 2
        feat.append(-2); umb.append(-2.0); izq.append(-1); der.append(-1)
        hojas.append((nodo, 3))
        # Proporción de clases del train en cada hoja (para proba); la clase de la
        # hoja la fija la regla y tiene que ser la mayoritaria.
        hoja_de = self._hoja(X)
        value = np.zeros((len(feat), 1, 3))
        for i, c in hojas:
            m = hoja_de == i
            cuenta = np.bincount(y[m] - 1, minlength=3).astype(float) if m.any() else np.eye(3)[c - 1]
            if int(np.argmax(cuenta)) != c - 1:
                cuenta = cuenta.copy()
                cuenta[c - 1] = cuenta.max() + 1   # la regla manda: la clase de la hoja gana
            value[i, 0] = cuenta / cuenta.sum()
        self.tree_ = SimpleNamespace(
            node_count=len(feat), children_left=np.array(izq), children_right=np.array(der),
            feature=np.array(feat), threshold=np.array(umb, dtype=float), value=value,
            max_depth=len(internos))

    def _hoja(self, X):
        t = self.tree_ if hasattr(self, "tree_") else None
        X = np.asarray(X, dtype=float)
        if t is None:   # durante _armar_arbol: recorrer la cadena a mano
            internos = ([] if self.h_riego_ is None else [(1, self.h_riego_)]) + [(0, self.t1_), (0, self.t2_)]
            out = np.full(len(X), 2 * len(internos))
            for k in range(len(internos) - 1, -1, -1):
                f, u = internos[k]
                out = np.where(X[:, f] <= u, 2 * k + 1, out)
            return out
        out = np.zeros(len(X), int)
        for r in range(len(X)):
            i = 0
            while t.children_left[i] != -1:
                i = t.children_left[i] if X[r, t.feature[i]] <= t.threshold[i] else t.children_right[i]
            out[r] = i
        return out

    def predict(self, X):
        return self._regla(X, self.h_riego_)

    def predict_proba(self, X):
        return self.tree_.value[self._hoja(X), 0]


# ─── Modelo que va a la placa ─────────────────────────────────────────────
# Lo elige el notebook 03 (snapshot del 23/10, entrenando sin dudosos): §5.3
# (costo; F1 macro fuera de fold sin dudosos dentro de 1 desvío bootstrap del
# mejor; desempate por interpretabilidad). El notebook avisa si esto deja de
# coincidir, y `python -m plantaia_ml.exportar_c` lo reentrena con esta
# configuración. Historia: arbol-p2-f012-58e644 (21/10, sólo hasta el 03/10 y
# 19–21/10) → arbol-p3-f03-ee3419 (23/10 mañana, con la restricción del aire y
# los dudosos en el train) → esta regla.
CONFIG_FINAL = {
    "tipo": "Regla sonda + riego",
    "params": {"sel__columnas": (IDX_SUELO, IDX_RIEGO)},
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
    elif isinstance(clf, (DecisionTreeClassifier, ReglaSueloRiego)):
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
