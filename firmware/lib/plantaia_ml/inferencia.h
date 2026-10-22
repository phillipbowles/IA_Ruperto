// PlantaIa — un paso de inferencia: muestra cruda → features → modelo → log.
//
// Es la ÚNICA unidad de compilación del firmware que incluye
// modelo_plantaia.h: main.cpp y el replay en host pasan por acá, así que la
// placa y el host corren exactamente el mismo código (y el modelo, aunque el
// exportador lo genere con funciones no-inline, no se define dos veces en el
// binario del firmware).
#pragma once

#include <stddef.h>
#include <stdint.h>
#include "features.h"

#define PLANTAIA_N_CLASES_API 3   // saludable, estresada, marchita

struct Inferencia {
  bool     ok;          // false → no se pudo armar el vector (ver marcas); clase = 0
  bool     warmup;      // < 1 h de historia: suelo_delta_1h = 0
  bool     empujada;    // true = tick de 5 min (avanzó la ventana); false = consulta
  uint8_t  marcas;      // FEAT_MARCA_* de la muestra
  uint32_t n;           // muestras empujadas al buffer desde el arranque
  float    x[FEAT_N];
  int      clase;       // 1..3; 0 si !ok
  float    proba[PLANTAIA_N_CLASES_API];
  uint32_t t_us;        // duración de plantaia_predecir, en µs
};

// Reloj en microsegundos: micros() en la placa, std::chrono en el host.
typedef uint32_t (*plantaia_reloj_us_t)(void);

// empujar = true  → tick de 5 min: la muestra entra a la ventana.
// empujar = false → consulta (envío forzado): mismo cálculo, la ventana no cambia.
void plantaia_inferir(BufferFeatures *buf, const MuestraCruda *m, bool empujar,
                      plantaia_reloj_us_t reloj_us, Inferencia *out);

// "saludable" | "estresada" | "marchita"; "sin_prediccion" para cualquier otro código.
const char *plantaia_etiqueta(int clase);

// Versión del modelo compilado (PLANTAIA_MODELO_VERSION).
const char *plantaia_modelo_version(void);

// Línea de log parseable, sin '\n'. Con inf->ok:
//   [INF] n=123 warmup=0 x=[1532,-41,20.6,47,1.29,871,850] -> estresada p=[0.10,0.78,0.12] t_us=37
// Sin inferencia (inf->ok == false):
//   [INF] n=0 warmup=1 x=[nan,...] -> sin_prediccion p=[] t_us=0
// `tag` reemplaza "[INF]" (el envío forzado usa "[CON]"). Devuelve lo que
// devolvería snprintf.
int plantaia_linea_inf(const Inferencia *inf, const char *tag, char *dst, size_t tam);

// Línea con los faltantes de la muestra, o dst = "" si no hubo ninguno:
//   [FAL] n=123 suelo_repetido dht_anterior
int plantaia_linea_fal(const Inferencia *inf, char *dst, size_t tam);
