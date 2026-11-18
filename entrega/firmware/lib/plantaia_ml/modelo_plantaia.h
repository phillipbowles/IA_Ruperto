// ════════════════════════════════════════════════════════════════════════════
//  modelo_plantaia.h — GENERADO — no editar
//
//  Lo escribe ml/plantaia_ml/exportar_c.py (2026-10-23). Para regenerarlo:
//    cd ml && /opt/anaconda3/bin/python -m plantaia_ml.exportar_c
//  Elección y evaluación: notebooks/03_modelos.ipynb.
//
//  Modelo: regla-p3-f07-79b556
//  Features que usa (índices del contrato): 0 suelo_mv, 7 h_desde_riego
//  Orden del vector que recibe plantaia_predecir (docs/ENTREGA2.md §4):
//    0 suelo_mv
//    1 suelo_delta_1h
//    2 temp_c
//    3 hum_aire_pct
//    4 vpd_kpa
//    5 luz_mv
//    6 luz_media_1h
//    7 h_desde_riego
//  Métricas (partición por episodio, ver el notebook):
//    [config. final fija] f1_macro todos, filas fuera de fold juntas (24 ep.): 0.795
//    [config. final fija] exactitud_balanceada todos, filas fuera de fold juntas (24 ep.): 0.786
//    [config. final fija] recall_marchita todos, filas fuera de fold juntas (24 ep.): 0.654
//    [config. final fija] f1_macro sin dudosos, filas fuera de fold juntas (20 ep.): 0.858
//    [config. final fija] exactitud_balanceada sin dudosos, filas fuera de fold juntas (20 ep.): 0.860
//    [config. final fija] recall_marchita sin dudosos, filas fuera de fold juntas (20 ep.): 0.765
//    filas de entrenamiento (sin dudosos): 5171
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

#define PLANTAIA_N_FEATURES      8
#define PLANTAIA_N_CLASES        3
#define PLANTAIA_MODELO_VERSION  "regla-p3-f07-79b556"

#define PLANTAIA_ARBOL_N_NODOS 7
#define PLANTAIA_ARBOL_N_HOJAS 4
// Nodo interno: x[FEAT] <= UMBRAL → IZQ, si no → DER. Hoja: FEAT = -1 e IZQ = índice en HOJA.
static const int8_t PLANTAIA_ARBOL_FEAT[7] = {7, -1, 0, -1, 0, -1, -1};
static const float PLANTAIA_ARBOL_UMBRAL[7] = {5.5f, 0.0f, 1715.99988f, 0.0f, 1939.875f, 0.0f, 0.0f};
static const int16_t PLANTAIA_ARBOL_IZQ[7] = {1, 0, 3, 1, 5, 2, 3};
static const int16_t PLANTAIA_ARBOL_DER[7] = {2, -1, 4, -1, 6, -1, -1};
// Probabilidades de cada hoja: saludable, estresada, marchita.
static const float PLANTAIA_ARBOL_HOJA[4][3] = {
  {0.0696517378f, 0.930348277f, 0.0f},
  {0.981963098f, 0.0180369131f, 0.0f},
  {0.0361010842f, 0.882929325f, 0.0809695721f},
  {0.0f, 0.231839254f, 0.76816076f},
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
