// Tests del modelo exportado (API fija de docs/ENTREGA2.md §5.3).
//   pio test -e native -f test_modelo
//
// Valen igual para el dummy y para el modelo real que genere el exportador:
// sólo miran la API, no los umbrales.
#include <unity.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "modelo_plantaia.h"
#include "inferencia.h"

// Vectores de paridad Python↔C, generados por ml/plantaia_ml/exportar_c.py.
// Si no existen, el test de paridad FALLA: regenerarlos con el exportador.
#if defined(__has_include)
#  if __has_include("vectores.h")
#    include "vectores.h"
#    define HAY_VECTORES 1
#  endif
#endif

void setUp(void) {}
void tearDown(void) {}

void test_api_fija(void) {
  TEST_ASSERT_EQUAL_INT(7, PLANTAIA_N_FEATURES);
  TEST_ASSERT_TRUE(strlen(PLANTAIA_MODELO_VERSION) > 0);
  TEST_ASSERT_EQUAL_STRING(PLANTAIA_MODELO_VERSION, plantaia_modelo_version());
}

// Barrido grueso del espacio de features que puede ver la placa: siempre una
// clase válida y probabilidades que suman 1, con o sin puntero de proba.
void test_clase_1_a_3_y_probas_suman_1(void) {
  const float suelos[] = {900, 1200, 1500, 1700, 1900, 2100, 2400, 2800, 3124};
  const float deltas[] = {-400, -40, 0, 40, 400};
  const float temps[]  = {5, 15, 22, 30, 40};
  const float hums[]   = {15, 45, 70, 95};
  const float luces[]  = {140, 900, 2000, 3124};
  int n = 0;
  for (float s : suelos) for (float d : deltas) for (float t : temps)
  for (float h : hums)   for (float l : luces) {
    float x[PLANTAIA_N_FEATURES] = {s, d, t, h, 0.6108f * expf(17.27f * t / (t + 237.3f)) * (1 - h / 100), l, l * 0.9f};
    float p[3] = {-1, -1, -1};
    int c = plantaia_predecir(x, p);
    TEST_ASSERT_TRUE(c >= 1 && c <= 3);
    float suma = 0;
    for (int k = 0; k < 3; k++) { TEST_ASSERT_TRUE(p[k] >= 0.0f && p[k] <= 1.0f); suma += p[k]; }
    TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.0f, suma);
    // La clase devuelta es la de mayor probabilidad (empate → menor código).
    int arg = 0;
    for (int k = 1; k < 3; k++) if (p[k] > p[arg]) arg = k;
    TEST_ASSERT_EQUAL_INT(arg + 1, c);
    TEST_ASSERT_EQUAL_INT(c, plantaia_predecir(x, NULL));   // proba es opcional
    n++;
  }
  TEST_ASSERT_TRUE(n > 1000);
}

void test_paridad_con_python(void) {
#ifdef HAY_VECTORES
  TEST_ASSERT_EQUAL_STRING_MESSAGE(PLANTAIA_MODELO_VERSION, VEC_MODELO_VERSION,
      "vectores.h es de otro modelo: regenerarlo con exportar_c.py junto con modelo_plantaia.h");
  TEST_ASSERT_TRUE(VEC_N > 0);
  int aciertos = 0;
  for (int i = 0; i < VEC_N; i++) {
    float p[3];
    int c = plantaia_predecir(VEC_X[i], p);
    if (c == VEC_Y[i]) aciertos++;
    else printf("paridad: fila %d esperaba %d y dio %d\n", i, VEC_Y[i], c);
#ifdef VEC_HAY_PROBA
    char msg[32];
    snprintf(msg, sizeof(msg), "proba fila %d", i);
    for (int k = 0; k < 3; k++) TEST_ASSERT_FLOAT_WITHIN_MESSAGE(2e-3f, VEC_P[i][k], p[k], msg);
#endif
  }
  TEST_ASSERT_EQUAL_INT_MESSAGE(VEC_N, aciertos, "la paridad de clase tiene que ser 100 %");
#else
  TEST_FAIL_MESSAGE("falta test/test_modelo/vectores.h: regenerarlo con python -m plantaia_ml.exportar_c");
#endif
}

// La cadena completa (inferencia.cpp) arma la línea [INF] en el formato fijo.
static uint32_t reloj_falso(void) { static uint32_t t = 0; return t += 37; }

void test_linea_inf_formato(void) {
  BufferFeatures buf;
  features_reset(&buf);
  MuestraCruda m = {1532.0f, 871.0f, 20.6f, 47.0f, 21.0f};
  Inferencia inf;
  plantaia_inferir(&buf, &m, true, reloj_falso, &inf);
  TEST_ASSERT_TRUE(inf.ok);
  TEST_ASSERT_EQUAL_UINT32(1, inf.n);
  TEST_ASSERT_EQUAL_UINT32(37, inf.t_us);
  char linea[160];
  plantaia_linea_inf(&inf, "[INF]", linea, sizeof(linea));
  char esperado[160];
  snprintf(esperado, sizeof(esperado),
           "[INF] n=1 warmup=1 x=[1532,0,20.6,47,1.29,871,871] -> %s p=[%.2f,%.2f,%.2f] t_us=37",
           plantaia_etiqueta(inf.clase), (double)inf.proba[0], (double)inf.proba[1], (double)inf.proba[2]);
  TEST_ASSERT_EQUAL_STRING(esperado, linea);
}

void test_sin_inferencia_y_consulta(void) {
  BufferFeatures buf;
  features_reset(&buf);
  Inferencia inf;
  MuestraCruda sin_hum = {1500.0f, 800.0f, NAN, NAN, NAN};
  plantaia_inferir(&buf, &sin_hum, true, reloj_falso, &inf);
  TEST_ASSERT_FALSE(inf.ok);
  TEST_ASSERT_EQUAL_INT(0, inf.clase);
  TEST_ASSERT_EQUAL_STRING("sin_prediccion", plantaia_etiqueta(inf.clase));
  char fal[96];
  plantaia_linea_fal(&inf, fal, sizeof(fal));
  TEST_ASSERT_EQUAL_STRING("[FAL] n=1 sin_temp sin_hum", fal);

  // Consulta: no avanza n ni la ventana.
  MuestraCruda ok = {1500.0f, 800.0f, 21.0f, 50.0f, 21.0f};
  plantaia_inferir(&buf, &ok, false, reloj_falso, &inf);
  TEST_ASSERT_TRUE(inf.ok);
  TEST_ASSERT_FALSE(inf.empujada);
  TEST_ASSERT_EQUAL_UINT32(1, inf.n);
  TEST_ASSERT_EQUAL_UINT32(1, buf.total);
}

int main(int, char **) {
  UNITY_BEGIN();
  RUN_TEST(test_api_fija);
  RUN_TEST(test_clase_1_a_3_y_probas_suman_1);
  RUN_TEST(test_paridad_con_python);
  RUN_TEST(test_linea_inf_formato);
  RUN_TEST(test_sin_inferencia_y_consulta);
  return UNITY_END();
}
