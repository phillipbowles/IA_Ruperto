// ════════════════════════════════════════════════════════════════════════════
//  modelo_plantaia.h — GENERADO — no editar
//
//  Lo escribe ml/plantaia_ml/exportar_c.py (2026-10-22). Para regenerarlo:
//    cd ml && /opt/anaconda3/bin/python -m plantaia_ml.exportar_c
//  Elección y evaluación: notebooks/03_modelos.ipynb.
//
//  Modelo: arbol-p2-f012-58e644
//  Features que usa (índices del contrato): 0 suelo_mv, 1 suelo_delta_1h, 2 temp_c
//  Orden del vector que recibe plantaia_predecir (docs/ENTREGA2.md §4):
//    0 suelo_mv
//    1 suelo_delta_1h
//    2 temp_c
//    3 hum_aire_pct
//    4 vpd_kpa
//    5 luz_mv
//    6 luz_media_1h
//  Métricas (partición por episodio, ver el notebook):
//    [config. final fija] f1_macro todos, filas fuera de fold juntas (11 ep.): 0.181
//    [config. final fija] exactitud_balanceada todos, filas fuera de fold juntas (11 ep.): 0.200
//    [config. final fija] recall_marchita todos, filas fuera de fold juntas (11 ep.): 0.240
//    [config. final fija] f1_macro sin dudosos, filas fuera de fold juntas (7 ep.): 0.282
//    [config. final fija] exactitud_balanceada sin dudosos, filas fuera de fold juntas (7 ep.): 0.279
//    [config. final fija] recall_marchita sin dudosos, filas fuera de fold juntas (7 ep.): 0.360
//    [búsqueda anidada del tipo Árbol de decisión] f1_macro todos, filas fuera de fold juntas (11 ep.): 0.186
//    [búsqueda anidada del tipo Árbol de decisión] exactitud_balanceada todos, filas fuera de fold juntas (11 ep.): 0.207
//    [búsqueda anidada del tipo Árbol de decisión] recall_marchita todos, filas fuera de fold juntas (11 ep.): 0.000
//    [búsqueda anidada del tipo Árbol de decisión] f1_macro sin dudosos, filas fuera de fold juntas (7 ep.): 0.316
//    [búsqueda anidada del tipo Árbol de decisión] exactitud_balanceada sin dudosos, filas fuera de fold juntas (7 ep.): 0.326
//    [búsqueda anidada del tipo Árbol de decisión] recall_marchita sin dudosos, filas fuera de fold juntas (7 ep.): 0.000
//    filas de entrenamiento: 1357
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

#define PLANTAIA_N_FEATURES      7
#define PLANTAIA_N_CLASES        3
#define PLANTAIA_MODELO_VERSION  "arbol-p2-f012-58e644"

#define PLANTAIA_ARBOL_N_NODOS 5
#define PLANTAIA_ARBOL_N_HOJAS 3
// Nodo interno: x[FEAT] <= UMBRAL → IZQ, si no → DER. Hoja: FEAT = -1 e IZQ = índice en HOJA.
static const int8_t PLANTAIA_ARBOL_FEAT[5] = {2, -1, 0, -1, -1};
static const float PLANTAIA_ARBOL_UMBRAL[5] = {10.25f, 0.0f, 1821.5f, 0.0f, 0.0f};
static const int16_t PLANTAIA_ARBOL_IZQ[5] = {1, 0, 3, 1, 2};
static const int16_t PLANTAIA_ARBOL_DER[5] = {2, -1, 4, -1, -1};
// Probabilidades de cada hoja: saludable, estresada, marchita.
static const float PLANTAIA_ARBOL_HOJA[3][3] = {
  {0.0f, 0.0f, 1.0f},
  {0.447734684f, 0.278801352f, 0.273463935f},
  {0.0296127554f, 0.97038722f, 0.0f},
};

static inline int plantaia_predecir(const float x[PLANTAIA_N_FEATURES], float *proba) {
  // Recorrido iterativo desde la raíz: sin recursión ni memoria dinámica.
  int16_t i = 0;
  while (PLANTAIA_ARBOL_FEAT[i] >= 0)
    i = (x[PLANTAIA_ARBOL_FEAT[i]] <= PLANTAIA_ARBOL_UMBRAL[i]) ? PLANTAIA_ARBOL_IZQ[i] : PLANTAIA_ARBOL_DER[i];
  const float *p = PLANTAIA_ARBOL_HOJA[PLANTAIA_ARBOL_IZQ[i]];
  // Clase = argmax de proba; con '>' estricto el empate queda en el código menor
  // (como numpy.argmax).
  int mejor = 0;
  for (int k = 1; k < PLANTAIA_N_CLASES; k++) if (p[k] > p[mejor]) mejor = k;
  if (proba != NULL) for (int k = 0; k < PLANTAIA_N_CLASES; k++) proba[k] = p[k];
  return mejor + 1;
}
