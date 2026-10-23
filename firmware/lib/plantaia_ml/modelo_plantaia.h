// ════════════════════════════════════════════════════════════════════════════
//  modelo_plantaia.h — GENERADO — no editar
//
//  Lo escribe ml/plantaia_ml/exportar_c.py (2026-10-23). Para regenerarlo:
//    cd ml && /opt/anaconda3/bin/python -m plantaia_ml.exportar_c
//  Elección y evaluación: notebooks/03_modelos.ipynb.
//
//  Modelo: arbol-p3-f03-ee3419
//  Features que usa (índices del contrato): 0 suelo_mv, 3 hum_aire_pct
//  Orden del vector que recibe plantaia_predecir (docs/ENTREGA2.md §4):
//    0 suelo_mv
//    1 suelo_delta_1h
//    2 temp_c
//    3 hum_aire_pct
//    4 vpd_kpa
//    5 luz_mv
//    6 luz_media_1h
//  Métricas (partición por episodio, ver el notebook):
//    [config. final fija] f1_macro todos, filas fuera de fold juntas (24 ep.): 0.651
//    [config. final fija] exactitud_balanceada todos, filas fuera de fold juntas (24 ep.): 0.669
//    [config. final fija] recall_marchita todos, filas fuera de fold juntas (24 ep.): 0.590
//    [config. final fija] f1_macro sin dudosos, filas fuera de fold juntas (20 ep.): 0.711
//    [config. final fija] exactitud_balanceada sin dudosos, filas fuera de fold juntas (20 ep.): 0.737
//    [config. final fija] recall_marchita sin dudosos, filas fuera de fold juntas (20 ep.): 0.690
//    [búsqueda anidada del tipo Árbol de decisión] f1_macro todos, filas fuera de fold juntas (24 ep.): 0.711
//    [búsqueda anidada del tipo Árbol de decisión] exactitud_balanceada todos, filas fuera de fold juntas (24 ep.): 0.719
//    [búsqueda anidada del tipo Árbol de decisión] recall_marchita todos, filas fuera de fold juntas (24 ep.): 0.625
//    [búsqueda anidada del tipo Árbol de decisión] f1_macro sin dudosos, filas fuera de fold juntas (20 ep.): 0.779
//    [búsqueda anidada del tipo Árbol de decisión] exactitud_balanceada sin dudosos, filas fuera de fold juntas (20 ep.): 0.792
//    [búsqueda anidada del tipo Árbol de decisión] recall_marchita sin dudosos, filas fuera de fold juntas (20 ep.): 0.731
//    filas de entrenamiento: 5663
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
#define PLANTAIA_MODELO_VERSION  "arbol-p3-f03-ee3419"

#define PLANTAIA_ARBOL_N_NODOS 15
#define PLANTAIA_ARBOL_N_HOJAS 8
// Nodo interno: x[FEAT] <= UMBRAL → IZQ, si no → DER. Hoja: FEAT = -1 e IZQ = índice en HOJA.
static const int8_t PLANTAIA_ARBOL_FEAT[15] = {0, 0, 0, -1, -1, 0, -1, -1, 0, 3, -1, -1, 3, -1, -1};
static const float PLANTAIA_ARBOL_UMBRAL[15] = {1743.5f, 1488.25f, 1445.75f, 0.0f, 0.0f, 1716.5f, 0.0f, 0.0f, 1936.5f, 47.75f, 0.0f, 0.0f, 43.5f, 0.0f, 0.0f};
static const int16_t PLANTAIA_ARBOL_IZQ[15] = {1, 2, 3, 0, 1, 6, 2, 3, 9, 10, 4, 5, 13, 6, 7};
static const int16_t PLANTAIA_ARBOL_DER[15] = {8, 5, 4, -1, -1, 7, -1, -1, 12, 11, -1, -1, 14, -1, -1};
// Probabilidades de cada hoja: saludable, estresada, marchita.
static const float PLANTAIA_ARBOL_HOJA[8][3] = {
  {0.0436476171f, 0.956352353f, 0.0f},
  {0.424763799f, 0.394871145f, 0.180365041f},
  {0.817953765f, 0.0829260349f, 0.0991201848f},
  {0.344684482f, 0.655315518f, 0.0f},
  {0.0220529344f, 0.62452358f, 0.353423476f},
  {0.0112650255f, 0.988734961f, 0.0f},
  {0.0f, 1.0f, 0.0f},
  {0.0f, 0.0616629757f, 0.938337028f},
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
