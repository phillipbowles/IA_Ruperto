// PlantaIa — buffer circular y features del modelo (contrato docs/ENTREGA2.md §4)
//
// C++ puro, SIN Arduino.h: compila igual en la ESP32 y en el host
// ([env:native]), que es donde corren los tests y el replay.
//
// El gemelo en Python es ml/plantaia_ml/features.py. Si se toca la semántica
// acá, se toca allá en el mismo commit — el test de paridad lo exige.
#pragma once

#include <stdint.h>
#include <stdbool.h>

// Orden FIJO del vector (contrato §4). No reordenar: el modelo exportado
// indexa por posición.
#define FEAT_SUELO_MV        0   // mV, mediana de 9 de la sonda
#define FEAT_SUELO_DELTA_1H  1   // mV, suelo(t) − suelo(t−12 muestras); 0 en warm-up
#define FEAT_TEMP_C          2   // °C, DHT11 (último válido; sin respaldo)
#define FEAT_HUM_AIRE_PCT    3   // %,  DHT11 (último válido)
#define FEAT_VPD_KPA         4   // kPa, con 2 y 3
#define FEAT_LUZ_MV          5   // mV, mediana de 9 del LDR
#define FEAT_LUZ_MEDIA_1H    6   // mV, media de las últimas ≤13 muestras (incluida la actual)
#define FEAT_N               7

// Ventana de 1 h a 5 min por muestra: la actual + 12 anteriores.
#define FEAT_VENTANA        13
#define FEAT_LAG_DELTA      12   // muestras hacia atrás para suelo_delta_1h

// Marcas de calidad de la última muestra empujada (bits). Viajan al log como
// línea [FAL]; el contrato pide que la repetición de un valor quede a la vista.
#define FEAT_MARCA_SUELO_REPETIDO   0x01  // suelo faltó → se repitió el anterior
#define FEAT_MARCA_LUZ_REPETIDA     0x02  // luz faltó   → se repitió la anterior
#define FEAT_MARCA_DHT_ANTERIOR     0x04  // DHT falló   → último T/HR válido
// 0x08 libre: era el respaldo de T con el termistor, que el contrato §4 sacó.
#define FEAT_MARCA_SIN_SUELO        0x10  // faltó y no hay anterior → no se pudo armar
#define FEAT_MARCA_SIN_LUZ          0x20  // idem luz
#define FEAT_MARCA_SIN_TEMP         0x40  // nunca hubo T válida del DHT
#define FEAT_MARCA_SIN_HUM          0x80  // nunca hubo HR válida

// Lo que entra al buffer en cada tick de 5 min. Un valor faltante va en NAN
// (nunca en 0: 0 mV es una lectura posible y se confundiría con un dato).
struct MuestraCruda {
  float suelo_mv;       // NAN si falta (p. ej. sonda saturada / fuera del sustrato)
  float luz_mv;         // NAN si falta
  float temp_dht_c;     // NAN si el DHT11 no respondió
  float hum_aire_pct;   // NAN si el DHT11 no respondió
  float temp_ntc_c;     // NO entra a las features (contrato §4); queda para el log/POST
};

// Estado completo de la ventana. Vive en RAM: un reinicio de la placa lo vacía
// y la ventana arranca de cero (warm-up), igual que el Python que corta los
// tramos por boot_id. ~130 bytes.
struct BufferFeatures {
  float    suelo[FEAT_VENTANA];   // circular; ya con los faltantes repetidos
  float    luz[FEAT_VENTANA];
  uint8_t  cabeza;                // índice donde va la PRÓXIMA muestra
  uint8_t  n;                     // muestras válidas en la ventana (≤ 13)
  uint32_t total;                 // muestras empujadas desde el reset
  float    temp_ult, hum_ult;     // último T / HR del DHT válidos
  bool     hay_temp_dht;          // hubo alguna vez T válida del DHT
  bool     hay_hum;               // hubo alguna vez HR válida del DHT
  uint8_t  marcas;                // FEAT_MARCA_* de la última muestra
};

// Deja el buffer vacío (equivale a un arranque de la placa).
void features_reset(BufferFeatures *buf);

// Empuja una muestra al buffer y arma el vector de features en x_out[0..6].
//
// Devuelve true si el vector quedó completo (se puede inferir). Devuelve false
// si falta algo que no tiene reemplazo (suelo/luz sin anterior, nunca hubo T o
// HR válidas del DHT; el termistor no es respaldo): en ese caso, si el faltante es suelo o luz la muestra
// NO entra al buffer (no hay con qué rellenarla); si es T/HR, sí entra (suelo y
// luz sirven para las muestras siguientes) pero no se infiere. Si la muestra no
// entra, x_out queda entero en NAN (como features.py).
//
// *warmup (si no es NULL) = true mientras haya menos de 12 muestras previas:
// suelo_delta_1h vale 0 y la media de luz usa lo que haya.
bool features_empujar(BufferFeatures *buf, const MuestraCruda *m,
                      float x_out[FEAT_N], bool *warmup);

// Igual que features_empujar pero SIN modificar el buffer: arma el vector
// "como si" la muestra se empujara. Es lo que usa el envío forzado por botón,
// para no meter una muestra fuera de la cadencia de 5 min en la ventana.
// *marcas_out (si no es NULL) recibe las marcas que habría tenido la muestra.
bool features_consultar(const BufferFeatures *buf, const MuestraCruda *m,
                        float x_out[FEAT_N], bool *warmup, uint8_t *marcas_out);

// Déficit de presión de vapor (kPa), Tetens: 0.6108·exp(17.27·T/(T+237.3))·(1 − HR/100).
float features_vpd_kpa(float temp_c, float hum_pct);
