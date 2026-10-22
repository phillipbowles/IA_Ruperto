"""Exporta el modelo entrenado a C para la ESP32 (docs/ENTREGA2.md §5.3).

    cd ml && /opt/anaconda3/bin/python -m plantaia_ml.exportar_c

Reentrena el modelo de `modelos.CONFIG_FINAL` con la serie completa de
maceta-01 y escribe tres archivos:

- `firmware/lib/plantaia_ml/modelo_plantaia.h` — el modelo, con la API fija
  de firmware/lib/plantaia_ml/README.md §5.
- `firmware/test/test_modelo/vectores.h` — vectores de la serie (y casos pegados
  a cada umbral) con la clase y las probabilidades que da sklearn; `pio test`
  exige 100 % de coincidencia de clase.
- `firmware/test/test_features/paridad_features.h` — una secuencia cruda del
  snapshot real con reinicios, huecos, faltantes y la sonda saturada, y los
  vectores que da `features.py`, para la paridad de features Python↔C.

Sin dependencias nuevas: numpy, pandas y sklearn.

Formas que sabe exportar: `DecisionTreeClassifier`, `RandomForestClassifier` y
`LogisticRegression` (con `StandardScaler` opcional), siempre dentro del
`Pipeline` de `modelos.py` (primer paso `sel` = subconjunto de features). La
placa arma siempre los 7 features; el remapeo de índices queda adentro de
`plantaia_predecir`.

Umbrales de los árboles en float32
----------------------------------
sklearn convierte X a float32 antes de recorrer el árbol y compara
`x_f32 <= umbral_f64`. Guardar el umbral redondeado al float32 más cercano
puede cambiar decisiones: si el redondeo cae justo en un valor de x, el C
mandaría a la izquierda lo que sklearn manda a la derecha. Por eso cada umbral
se guarda como **el mayor float32 que no supera al umbral float64**: para todo
x float32, `x <= u64` ⟺ `x <= u32`. Los vectores de paridad incluyen, para cada
nodo, x en el umbral y en el float32 inmediatamente arriba y abajo.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from . import CLASES, RAIZ, SNAPSHOT_VIGENTE
from .features import FEATURES, N_FEATURES, calcular_features

RUTA_MODELO = RAIZ / "firmware" / "lib" / "plantaia_ml" / "modelo_plantaia.h"
RUTA_VECTORES = RAIZ / "firmware" / "test" / "test_modelo" / "vectores.h"
RUTA_PARIDAD = RAIZ / "firmware" / "test" / "test_features" / "paridad_features.h"


# ─── Utilidades ───────────────────────────────────────────────────────────
def f32(v) -> str:
    """Literal float de C que reproduce exactamente el float32 de `v`."""
    v = np.float32(v)
    if np.isnan(v):
        return "NAN"
    if np.isinf(v):
        return "INFINITY" if v > 0 else "-INFINITY"
    s = f"{float(v):.9g}"
    if "e" not in s and "." not in s:
        s += ".0"
    return s + "f"


def umbral_f32(u: float) -> np.float32:
    """Mayor float32 ≤ u: con x float32, `x <= u` ⟺ `x <= umbral_f32(u)`."""
    t = np.float32(u)
    if float(t) > u:
        t = np.nextafter(t, np.float32(-np.inf), dtype=np.float32)
    return t


def _partes(modelo: Pipeline):
    cols = tuple(int(c) for c in modelo.named_steps["sel"].columnas)
    esc = modelo.named_steps.get("esc")
    clf = modelo.named_steps["clf"]
    if list(clf.classes_) != [1, 2, 3]:
        raise ValueError(f"se esperaban las clases 1..3, hay {clf.classes_}")
    return cols, esc, clf


def _tablas_arbol(arbol: DecisionTreeClassifier, cols, base_nodo=0, base_hoja=0):
    """Nodos de un árbol en tablas planas. Hoja: feature -1 e izq = índice de hoja."""
    t = arbol.tree_
    feat, umb, izq, der, hojas = [], [], [], [], []
    for i in range(t.node_count):
        if t.children_left[i] == -1:
            v = np.asarray(t.value[i][0], dtype=float)
            v = v / v.sum()
            p32 = v.astype(np.float32)
            if int(np.argmax(p32)) != int(np.argmax(v)):
                raise ValueError(f"hoja {i}: el argmax cambia al pasar a float32")
            feat.append(-1); umb.append(0.0)
            izq.append(base_hoja + len(hojas)); der.append(-1)
            hojas.append(v)
        else:
            feat.append(cols[t.feature[i]])
            umb.append(umbral_f32(t.threshold[i]))
            izq.append(base_nodo + int(t.children_left[i]))
            der.append(base_nodo + int(t.children_right[i]))
    return feat, umb, izq, der, hojas


def umbrales(modelo: Pipeline) -> list[tuple[int, np.float32]]:
    """(feature del contrato, umbral float32) de todos los nodos internos."""
    cols, _, clf = _partes(modelo)
    arboles = clf.estimators_ if isinstance(clf, RandomForestClassifier) else (
        [clf] if isinstance(clf, DecisionTreeClassifier) else [])
    out = []
    for a in arboles:
        f, u, *_ = _tablas_arbol(a, cols)
        out += [(fi, ui) for fi, ui in zip(f, u) if fi >= 0]
    return out


# ─── Cuerpo C por tipo de modelo ──────────────────────────────────────────
_ARGMAX = """\
  // Clase = argmax de proba; con '>' estricto el empate queda en el código menor
  // (como numpy.argmax).
  int mejor = 0;
  for (int k = 1; k < PLANTAIA_N_CLASES; k++) if (p[k] > p[mejor]) mejor = k;
  if (proba != NULL) for (int k = 0; k < PLANTAIA_N_CLASES; k++) proba[k] = p[k];
  return mejor + 1;
}
"""


def _c_tablas(nombre, feat, umb, izq, der, hojas):
    n = len(feat)
    tipo_idx = "int16_t" if max(max(izq), max(der), len(hojas)) < 32767 else "int32_t"
    L = [f"#define PLANTAIA_{nombre}_N_NODOS {n}",
         f"#define PLANTAIA_{nombre}_N_HOJAS {len(hojas)}",
         f"// Nodo interno: x[FEAT] <= UMBRAL → IZQ, si no → DER. Hoja: FEAT = -1 e IZQ = índice en HOJA.",
         f"static const int8_t PLANTAIA_{nombre}_FEAT[{n}] = {{{', '.join(str(int(v)) for v in feat)}}};",
         f"static const float PLANTAIA_{nombre}_UMBRAL[{n}] = {{{', '.join(f32(v) for v in umb)}}};",
         f"static const {tipo_idx} PLANTAIA_{nombre}_IZQ[{n}] = {{{', '.join(str(int(v)) for v in izq)}}};",
         f"static const {tipo_idx} PLANTAIA_{nombre}_DER[{n}] = {{{', '.join(str(int(v)) for v in der)}}};",
         f"// Probabilidades de cada hoja: saludable, estresada, marchita.",
         f"static const float PLANTAIA_{nombre}_HOJA[{len(hojas)}][3] = {{"]
    L += [f"  {{{', '.join(f32(x) for x in h)}}}," for h in hojas]
    L.append("};")
    return L, tipo_idx


def _c_arbol(clf, cols):
    feat, umb, izq, der, hojas = _tablas_arbol(clf, cols)
    L, ti = _c_tablas("ARBOL", feat, umb, izq, der, hojas)
    L += ["",
          "static inline int plantaia_predecir(const float x[PLANTAIA_N_FEATURES], float *proba) {",
          "  // Recorrido iterativo desde la raíz: sin recursión ni memoria dinámica.",
          f"  {ti} i = 0;",
          "  while (PLANTAIA_ARBOL_FEAT[i] >= 0)",
          "    i = (x[PLANTAIA_ARBOL_FEAT[i]] <= PLANTAIA_ARBOL_UMBRAL[i]) ? PLANTAIA_ARBOL_IZQ[i] : PLANTAIA_ARBOL_DER[i];",
          "  const float *p = PLANTAIA_ARBOL_HOJA[PLANTAIA_ARBOL_IZQ[i]];",
          _ARGMAX]
    return L


def _c_bosque(clf, cols):
    feat, umb, izq, der, hojas, raices = [], [], [], [], [], []
    for a in clf.estimators_:
        raices.append(len(feat))
        f, u, l, r, h = _tablas_arbol(a, cols, base_nodo=len(feat), base_hoja=len(hojas))
        feat += f; umb += u; izq += l; der += r; hojas += h
    L, ti = _c_tablas("RF", feat, umb, izq, der, hojas)
    L += [f"#define PLANTAIA_RF_N_ARBOLES {len(raices)}",
          f"static const {ti} PLANTAIA_RF_RAIZ[{len(raices)}] = {{{', '.join(map(str, raices))}}};",
          "",
          "static inline int plantaia_predecir(const float x[PLANTAIA_N_FEATURES], float *proba) {",
          "  // Promedio de las probabilidades de cada árbol (como predict_proba de sklearn).",
          "  float p[PLANTAIA_N_CLASES] = {0.0f, 0.0f, 0.0f};",
          "  for (int a = 0; a < PLANTAIA_RF_N_ARBOLES; a++) {",
          f"    {ti} i = PLANTAIA_RF_RAIZ[a];",
          "    while (PLANTAIA_RF_FEAT[i] >= 0)",
          "      i = (x[PLANTAIA_RF_FEAT[i]] <= PLANTAIA_RF_UMBRAL[i]) ? PLANTAIA_RF_IZQ[i] : PLANTAIA_RF_DER[i];",
          "    for (int k = 0; k < PLANTAIA_N_CLASES; k++) p[k] += PLANTAIA_RF_HOJA[PLANTAIA_RF_IZQ[i]][k];",
          "  }",
          "  for (int k = 0; k < PLANTAIA_N_CLASES; k++) p[k] /= (float)PLANTAIA_RF_N_ARBOLES;",
          _ARGMAX]
    return L


def _c_logreg(clf, cols, esc):
    d = len(cols)
    media = esc.mean_ if esc is not None else np.zeros(d)
    escala = esc.scale_ if esc is not None else np.ones(d)
    L = [f"#define PLANTAIA_LR_D {d}",
         f"static const uint8_t PLANTAIA_LR_COL[{d}] = {{{', '.join(map(str, cols))}}};",
         f"static const float PLANTAIA_LR_MEDIA[{d}] = {{{', '.join(f32(v) for v in media)}}};",
         f"static const float PLANTAIA_LR_ESCALA[{d}] = {{{', '.join(f32(v) for v in escala)}}};",
         f"static const float PLANTAIA_LR_W[3][{d}] = {{"]
    L += [f"  {{{', '.join(f32(v) for v in fila)}}}," for fila in clf.coef_]
    L += ["};",
          f"static const float PLANTAIA_LR_B[3] = {{{', '.join(f32(v) for v in clf.intercept_)}}};",
          "",
          "static inline int plantaia_predecir(const float x[PLANTAIA_N_FEATURES], float *proba) {",
          "  float p[PLANTAIA_N_CLASES], z[PLANTAIA_LR_D];",
          "  for (int j = 0; j < PLANTAIA_LR_D; j++) z[j] = (x[PLANTAIA_LR_COL[j]] - PLANTAIA_LR_MEDIA[j]) / PLANTAIA_LR_ESCALA[j];",
          "  float maximo = -INFINITY;",
          "  for (int k = 0; k < PLANTAIA_N_CLASES; k++) {",
          "    float s = PLANTAIA_LR_B[k];",
          "    for (int j = 0; j < PLANTAIA_LR_D; j++) s += PLANTAIA_LR_W[k][j] * z[j];",
          "    p[k] = s;",
          "    if (s > maximo) maximo = s;",
          "  }",
          "  float suma = 0.0f;",
          "  for (int k = 0; k < PLANTAIA_N_CLASES; k++) { p[k] = expf(p[k] - maximo); suma += p[k]; }",
          "  for (int k = 0; k < PLANTAIA_N_CLASES; k++) p[k] /= suma;",
          _ARGMAX]
    return L


def cuerpo_c(modelo: Pipeline) -> tuple[str, list[str]]:
    cols, esc, clf = _partes(modelo)
    if isinstance(clf, DecisionTreeClassifier):
        if esc is not None:
            raise ValueError("un árbol no lleva escalado")
        return "arbol", _c_arbol(clf, cols)
    if isinstance(clf, RandomForestClassifier):
        return "rf", _c_bosque(clf, cols)
    if isinstance(clf, LogisticRegression):
        return "logreg", _c_logreg(clf, cols, esc)
    raise TypeError(f"no sé exportar {type(clf).__name__}")


def version_modelo(modelo: Pipeline) -> str:
    tipo, cuerpo = cuerpo_c(modelo)
    cols, _, clf = _partes(modelo)
    h = hashlib.sha1("\n".join(cuerpo).encode()).hexdigest()[:6]
    extra = f"-p{clf.max_depth}" if isinstance(clf, DecisionTreeClassifier) else ""
    return f"{tipo}{extra}-f{''.join(map(str, cols))}-{h}"


def generar_header(modelo: Pipeline, metricas: dict, fecha: str | None = None) -> str:
    tipo, cuerpo = cuerpo_c(modelo)
    cols, _, _ = _partes(modelo)
    version = version_modelo(modelo)
    fecha = fecha or _dt.date.today().isoformat()
    usadas = ", ".join(f"{c} {FEATURES[c]}" for c in cols)
    orden = "\n".join(f"//    {i} {n}" for i, n in enumerate(FEATURES))
    met = "\n".join(f"//    {k}: {v}" for k, v in metricas.items())
    cab = f"""\
// ════════════════════════════════════════════════════════════════════════════
//  modelo_plantaia.h — GENERADO — no editar
//
//  Lo escribe ml/plantaia_ml/exportar_c.py ({fecha}). Para regenerarlo:
//    cd ml && /opt/anaconda3/bin/python -m plantaia_ml.exportar_c
//  Elección y evaluación: notebooks/03_modelos.ipynb.
//
//  Modelo: {version}
//  Features que usa (índices del contrato): {usadas}
//  Orden del vector que recibe plantaia_predecir (docs/ENTREGA2.md §4):
{orden}
//  Métricas (partición por episodio, ver el notebook):
{met}
//
//  API fija: devuelve 1 saludable, 2 estresada, 3 marchita = argmax de proba
//  (empate → código menor); si proba != NULL escribe proba[0..2] en ese orden.
//  Precondición: x sin NAN (inferencia.cpp no llama al modelo si el vector
//  está incompleto). Todo static: se incluye desde más de una unidad de
//  compilación en los tests. Parámetros static const → flash. Sin malloc.
// ════════════════════════════════════════════════════════════════════════════
#pragma once

#include <math.h>
#include <stddef.h>
#include <stdint.h>

#define PLANTAIA_N_FEATURES      {N_FEATURES}
#define PLANTAIA_N_CLASES        3
#define PLANTAIA_MODELO_VERSION  "{version}"
"""
    return cab + "\n" + "\n".join(cuerpo)


# ─── Vectores de paridad del modelo ───────────────────────────────────────
def vectores_prueba(modelo: Pipeline, X: np.ndarray, n_base: int = 300, n_por_umbral: int = 12,
                    semilla: int = 0) -> np.ndarray:
    """Filas de la serie + casos con una feature puesta en un umbral y sus vecinos float32."""
    rng = np.random.default_rng(semilla)
    X = np.asarray(X, dtype=np.float32)
    base = X[rng.choice(len(X), size=min(n_base, len(X)), replace=False)]
    extra = []
    vistos = set()
    for f, u in umbrales(modelo):
        if (f, float(u)) in vistos:
            continue
        vistos.add((f, float(u)))
        for v in (np.nextafter(u, np.float32(-np.inf)), u, np.nextafter(u, np.float32(np.inf))):
            filas = X[rng.choice(len(X), size=max(1, n_por_umbral // 3), replace=False)].copy()
            filas[:, f] = v
            extra.append(filas)
    return np.vstack([base] + extra) if extra else base


def generar_vectores(modelo: Pipeline, Xv: np.ndarray) -> str:
    Xv = np.asarray(Xv, dtype=np.float32)
    y = modelo.predict(Xv)
    p = modelo.predict_proba(Xv)
    if not np.array_equal(y, np.asarray(modelo.classes_)[np.argmax(p, axis=1)]):
        raise AssertionError("predict y argmax(predict_proba) no coinciden")
    L = ["// GENERADO por ml/plantaia_ml/exportar_c.py — no editar.",
         "// Vectores de paridad del modelo: features (orden del contrato §4), la clase",
         "// que da sklearn y sus probabilidades. test_modelo exige 100 % de clase.",
         f"// {len(Xv)} vectores: filas de la serie de maceta-01 y casos con una feature",
         "// en cada umbral del modelo y en el float32 inmediatamente arriba y abajo.",
         "#pragma once", "",
         f'#define VEC_MODELO_VERSION "{version_modelo(modelo)}"', "",
         "//      " + "  ".join(FEATURES),
         "static const float VEC_X[][7] = {"]
    L += ["  {" + ", ".join(f32(v) for v in fila) + "}," for fila in Xv]
    L += ["};", "",
          "static const int VEC_Y[] = {" + ", ".join(str(int(v)) for v in y) + "};",
          "static const int VEC_N = (int)(sizeof(VEC_Y) / sizeof(VEC_Y[0]));", "",
          "#define VEC_HAY_PROBA 1",
          "static const float VEC_P[][3] = {"]
    L += ["  {" + ", ".join(f32(v) for v in fila) + "}," for fila in p]
    L.append("};")
    return "\n".join(L) + "\n"


# ─── Paridad de features ──────────────────────────────────────────────────
def secuencia_paridad(snapshot=SNAPSHOT_VIGENTE, semilla: int = 0) -> pd.DataFrame:
    """Secuencia cruda a 5 min, del snapshot real, con los casos difíciles a la vista.

    - El arranque del boot 49 (18/10 23:31) con las dos primeras muestras con
      la sonda saturada (fuera del sustrato) → faltante; como el buffer está
      vacío, no entran.
    - Un cambio de boot_id del 1/10 (corte de ventana).
    - Un hueco de 15 min dentro de un tramo (corte por hueco).
    - Un tramo que arranca con el DHT11 caído 3 muestras y el termistor leyendo:
      no se infiere (el termistor no es respaldo).
    - Faltantes sueltos de suelo, luz, T y HR.
    """
    from .datos_reales import leer_crudo, leer_episodios, preparar
    raw = leer_crudo(snapshot)
    b = preparar(raw[raw.dispositivo == "maceta-01"], leer_episodios())
    b = b.sort_values("ts").reset_index(drop=True)
    cols = ["ts", "dispositivo", "boot_id", "suelo_mv", "luz_mv", "temp_c", "hum_aire_pct",
            "temp_ntc_c", "suelo_saturado"]

    def tramo(desde, n):
        i = int(np.searchsorted(b.ts.values, np.datetime64(pd.Timestamp(desde).tz_convert(None))))
        return b.iloc[i:i + n][cols].copy()

    a = tramo("2026-10-18T23:30Z", 40)                 # arranque del boot 49
    # En el crudo, las 2 lecturas saturadas del arranque quedan en minoría dentro
    # del primer bin de 5 min; acá se fuerzan las dos primeras muestras a la sonda
    # saturada (3124 mV) para ejercitar el camino "saturada → faltante".
    a.iloc[:2, a.columns.get_loc("suelo_saturado")] = True
    a.iloc[:2, a.columns.get_loc("suelo_mv")] = 3124.0
    c = tramo("2026-10-01T14:20Z", 30)                 # cruza un reinicio
    d = tramo("2026-10-20T12:00Z", 50)                 # tramo largo para el hueco
    d = d.drop(d.index[20:23])                         # hueco de 15 min
    e = tramo("2026-10-21T06:00Z", 25)                 # arranque con DHT caído
    e["boot_id"] = 9001                                # reinicio simulado → reset
    e.iloc[:3, e.columns.get_loc("temp_c")] = np.nan
    e.iloc[:3, e.columns.get_loc("hum_aire_pct")] = np.nan
    e["temp_ntc_c"] = e["temp_ntc_c"].fillna(25.0)
    # Cada bloque con su propia hora para que no se pisen: se apilan corridos.
    partes, t0 = [], pd.Timestamp("2030-01-01", tz="UTC")
    for k, p in enumerate([a, c, d, e]):
        p = p.copy()
        p["ts"] = t0 + (p.ts - p.ts.iloc[0])
        p["boot_id"] = p["boot_id"].astype(int) + 10000 * k   # cada bloque, otro arranque
        t0 = p.ts.iloc[-1] + pd.Timedelta(hours=1)
        partes.append(p)
    s = pd.concat(partes, ignore_index=True)
    rng = np.random.default_rng(semilla)
    for col in ("suelo_mv", "luz_mv", "temp_c", "hum_aire_pct"):
        m = rng.random(len(s)) < 0.05
        m[:3] = False
        s.loc[m, col] = np.nan
    # Sonda saturada = faltante (lo mismo que dataset._con_features y main.cpp).
    s["suelo_mv"] = s.suelo_mv.where(~s.suelo_saturado.astype(bool))
    # Los dos lados ven exactamente los mismos números: crudos en float32.
    for col in ("suelo_mv", "luz_mv", "temp_c", "hum_aire_pct", "temp_ntc_c"):
        s[col] = s[col].astype(np.float32).astype(float)
    return s


def generar_paridad(s: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    f = calcular_features(s)
    reset = (f.tramo != f.tramo.shift()).astype(int)
    crudo = s[["suelo_mv", "luz_mv", "temp_c", "hum_aire_pct", "temp_ntc_c"]].to_numpy()
    L = ["// GENERADO por ml/plantaia_ml/exportar_c.py — no editar.",
         "// Paridad de features Python↔C: una secuencia cruda del snapshot real de",
         "// maceta-01 (con reinicios, un hueco, la sonda saturada como faltante, DHT",
         "// caído al arrancar y faltantes sueltos) y lo que da ml/plantaia_ml/features.py.",
         "#pragma once",
         "#include <math.h>", "",
         "// suelo_mv, luz_mv, temp_dht_c, hum_aire_pct, temp_ntc_c; NAN = faltante",
         "static const float PAR_CRUDO[][5] = {"]
    L += ["  {" + ", ".join(f32(v) for v in fila) + "}," for fila in crudo]
    L += ["};",
          "static const int PAR_RESET[] = {" + ", ".join(map(str, reset)) + "};",
          "static const int PAR_OK[] = {" + ", ".join(str(int(v)) for v in f.valido) + "};",
          "static const int PAR_WARMUP[] = {" + ", ".join(str(int(v)) for v in f.warmup) + "};",
          "static const float PAR_X[][7] = {"]
    X = f[FEATURES].to_numpy()
    L += ["  {" + ", ".join(f32(v) for v in fila) + "}," for fila in X]
    L += ["};", f"static const int PAR_N = {len(s)};"]
    return "\n".join(L) + "\n", f


# ─── Entrenamiento y métricas del modelo final ────────────────────────────
def metricas_cv(df: pd.DataFrame) -> dict:
    """CV anidada del tipo elegido (misma partición y grilla que el notebook).

    Además de media ± desvío por fold sobre la serie completa, devuelve las
    métricas sobre las filas reales fuera de fold (con y sin episodios
    dudosos): la serie completa mide sobre todo al simulador.
    """
    from .modelos import CONFIG_FINAL, busqueda, candidatos, particion_externa
    X = df[FEATURES].to_numpy(np.float32)
    y = df.clase_codigo.to_numpy(int)
    g = df.episodio_id.to_numpy(int)
    est, grilla = candidatos()[CONFIG_FINAL["tipo"]]
    f1, ba, rm = [], [], []
    oof = np.zeros(len(y), int)
    for tr, te in particion_externa().split(X, y, g):
        p = busqueda(est, grilla, n_jobs=1).fit(X[tr], y[tr], groups=g[tr]).predict(X[te])
        oof[te] = p
        f1.append(f1_score(y[te], p, average="macro"))
        ba.append(balanced_accuracy_score(y[te], p))
        rm.append(recall_score(y[te], p, labels=[3], average="macro"))
    out = {"f1_macro": (np.mean(f1), np.std(f1)), "exactitud_balanceada": (np.mean(ba), np.std(ba)),
           "recall_marchita": (np.mean(rm), np.std(rm))}
    if "fuente" in df:
        real = (df.fuente == "real").to_numpy()
        for nombre, m in [("reales", real), ("reales sin dudosos", real & ~df.dudoso.to_numpy(bool))]:
            if m.any():
                n_ep = df.loc[m, "episodio_id"].nunique()
                out[f"f1_macro {nombre} fuera de fold ({n_ep} ep.)"] = f1_score(
                    y[m], oof[m], labels=[1, 2, 3], average="macro", zero_division=0)
                out[f"exactitud_balanceada {nombre} fuera de fold ({n_ep} ep.)"] = \
                    balanced_accuracy_score(y[m], oof[m])
    return out


def exportar(modelo: Pipeline, df: pd.DataFrame, metricas: dict | None = None,
             escribir: bool = True) -> dict:
    """Escribe los tres headers. Devuelve un resumen (versión, rutas, tamaños)."""
    X = df[FEATURES].to_numpy(np.float32)
    if metricas is None:
        metricas = metricas_cv(df)
    n_ep = df.episodio_id.nunique()
    met = {(f"{k} ({n_ep} episodios, 5 folds)" if isinstance(v, tuple) else k):
           (f"{v[0]:.3f} ± {v[1]:.3f}" if isinstance(v, tuple) else f"{v:.3f}")
           for k, v in metricas.items()}
    met["filas de entrenamiento"] = f"{len(df)}"
    header = generar_header(modelo, met)
    Xv = vectores_prueba(modelo, X)
    vect = generar_vectores(modelo, Xv)
    par, f = generar_paridad(secuencia_paridad())
    if escribir:
        RUTA_MODELO.write_text(header)
        RUTA_VECTORES.write_text(vect)
        RUTA_PARIDAD.write_text(par)
    return {"version": version_modelo(modelo), "n_vectores": len(Xv), "n_paridad": len(f),
            "paridad_ok": int(f.valido.sum()), "paridad_resets": int((f.tramo != f.tramo.shift()).sum()),
            "metricas": met, "rutas": [RUTA_MODELO, RUTA_VECTORES, RUTA_PARIDAD]}


def main():
    from .dataset import serie_maceta01
    from .modelos import modelo_final
    df = serie_maceta01()
    X = df[FEATURES].to_numpy(np.float32)
    y = df.clase_codigo.to_numpy(int)
    modelo = modelo_final().fit(X, y)
    r = exportar(modelo, df)
    print(f"modelo {r['version']}")
    for k, v in r["metricas"].items():
        print(f"  {k}: {v}")
    print(f"  {r['n_vectores']} vectores de paridad del modelo")
    print(f"  {r['n_paridad']} muestras de paridad de features ({r['paridad_ok']} con vector, "
          f"{r['paridad_resets']} resets)")
    for p in r["rutas"]:
        print(f"  escrito {Path(p).relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
