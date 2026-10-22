// Replay en host: pasa una secuencia cruda real (remuestreada a 5 min) por el
// MISMO código que corre en la placa — lib/plantaia_ml, plantaia_inferir — e
// imprime una línea [INF] por muestra, con el formato del log Serial.
//
//   tools/correr_replay.sh            # regenera docs/entrega2/logs/replay_host.txt
//   pio test -e native -f test_replay -v
//
// Los datos salen de replay_datos.h (tools/generar_replay.py). Si se define la
// variable de entorno PLANTAIA_REPLAY_SALIDA, el log además se escribe ahí.
#include <unity.h>
#include <chrono>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "inferencia.h"
#include "replay_datos.h"

// t_us medido en el host: el número sirve para ver que la cadena funciona, NO
// para estimar el costo en la ESP32 (otro CPU, otra FPU). El de la placa sale
// del log real de M1.
static uint32_t reloj_host_us(void) {
  using namespace std::chrono;
  static const steady_clock::time_point t0 = steady_clock::now();
  return (uint32_t)duration_cast<microseconds>(steady_clock::now() - t0).count();
}

static FILE *salida = NULL;

static void emitir(const char *linea) {
  printf("%s\n", linea);
  if (salida) fprintf(salida, "%s\n", linea);
}

void setUp(void) {}
void tearDown(void) {}

void test_replay_tramos(void) {
  const char *ruta = getenv("PLANTAIA_REPLAY_SALIDA");
  if (ruta && *ruta) {
    salida = fopen(ruta, "w");
    TEST_ASSERT_NOT_NULL_MESSAGE(salida, "no se pudo abrir PLANTAIA_REPLAY_SALIDA");
  }

  char linea[200];
  snprintf(linea, sizeof(linea), "# replay en host — modelo %s — %d muestras de 5 min",
           plantaia_modelo_version(), REPLAY_N);
  emitir(linea);
  emitir("# mismo código que la placa (lib/plantaia_ml); t_us medido en el host, no en la ESP32");

  BufferFeatures buf;
  features_reset(&buf);
  int n_ok = 0, n_warmup = 0, n_etiq = 0, n_coinc = 0, n_fal = 0;
  uint32_t t_max = 0;
  int por_clase[4] = {0, 0, 0, 0};

  for (int i = 0; i < REPLAY_N; i++) {
    const FilaReplay &f = REPLAY[i];
    if (f.corte) {
      // Tramo nuevo, reinicio de la placa o hueco en el dato: la ventana
      // arranca de cero (igual que asignar_tramos() en features.py).
      features_reset(&buf);
      time_t ts = (time_t)f.ts_unix;
      char hora[24];
      strftime(hora, sizeof(hora), "%Y-%m-%dT%H:%MZ", gmtime(&ts));
      snprintf(linea, sizeof(linea), "# corte en %s — tramo %d: %s (boot_id=%u)", hora, f.tramo,
               REPLAY_TRAMOS[f.tramo], (unsigned)f.boot_id);
      emitir(linea);
    }
    MuestraCruda m = {f.suelo_mv, f.luz_mv, f.temp_dht_c, f.hum_aire_pct, f.temp_ntc_c};
    Inferencia inf;
    plantaia_inferir(&buf, &m, true, reloj_host_us, &inf);

    if (plantaia_linea_fal(&inf, linea, sizeof(linea)) > 0) { emitir(linea); n_fal++; }
    plantaia_linea_inf(&inf, "[INF]", linea, sizeof(linea));
    emitir(linea);

    TEST_ASSERT_TRUE(!inf.ok || (inf.clase >= 1 && inf.clase <= 3));
    if (inf.ok) {
      n_ok++;
      por_clase[inf.clase]++;
      if (inf.t_us > t_max) t_max = inf.t_us;
      if (f.etiqueta >= 1 && f.etiqueta <= 3) { n_etiq++; if (f.etiqueta == inf.clase) n_coinc++; }
    }
    if (inf.warmup) n_warmup++;
  }

  snprintf(linea, sizeof(linea),
           "# resumen: %d/%d inferencias, %d en warm-up, %d con faltantes, t_us max=%lu",
           n_ok, REPLAY_N, n_warmup, n_fal, (unsigned long)t_max);
  emitir(linea);
  snprintf(linea, sizeof(linea), "# predichas: saludable=%d estresada=%d marchita=%d",
           por_clase[1], por_clase[2], por_clase[3]);
  emitir(linea);
  snprintf(linea, sizeof(linea),
           "# coincidencia con la condicion que mandó la placa (sin sin_etiquetar): %d/%d",
           n_coinc, n_etiq);
  emitir(linea);
  if (salida) { fclose(salida); salida = NULL; }

  // Con DHT y sondas presentes en la primera muestra de cada corte, todas
  // tienen que inferir.
  TEST_ASSERT_EQUAL_INT(REPLAY_N, n_ok);
  TEST_ASSERT_TRUE_MESSAGE(t_max < 1000, "presupuesto del contrato: < 1 ms por inferencia");
  TEST_ASSERT_TRUE(REPLAY[0].corte);
}

int main(int, char **) {
  UNITY_BEGIN();
  RUN_TEST(test_replay_tramos);
  return UNITY_END();
}
