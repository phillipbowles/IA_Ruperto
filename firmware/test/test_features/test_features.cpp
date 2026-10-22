// Tests del buffer circular y las features (contrato docs/ENTREGA2.md §4).
//   pio test -e native -f test_features
#include <unity.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "features.h"

// Paridad Python↔C: test/test_features/paridad_features.h lo genera
// ml/plantaia_ml/exportar_c.py (formato en lib/plantaia_ml/README.md). La misma
// secuencia cruda tiene que dar los mismos vectores que features.py.
#if defined(__has_include)
#  if __has_include("paridad_features.h")
#    include "paridad_features.h"
#    define HAY_PARIDAD_FEATURES 1
#  endif
#endif

static BufferFeatures buf;

static MuestraCruda muestra(float suelo, float luz, float t = 20.0f, float h = 50.0f, float ntc = 21.0f) {
  MuestraCruda m = {suelo, luz, t, h, ntc};
  return m;
}

void setUp(void)    { features_reset(&buf); }
void tearDown(void) {}

// ─── VPD ──────────────────────────────────────────────────────────────────
void test_vpd_valores_conocidos(void) {
  // Referencias calculadas en float64 con la misma fórmula (Python).
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.169141f, features_vpd_kpa(20.0f, 50.0f));
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.267111f, features_vpd_kpa(25.0f, 60.0f));
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 2.970146f, features_vpd_kpa(30.0f, 30.0f));
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 0.206399f, features_vpd_kpa(18.0f, 90.0f));
  TEST_ASSERT_FLOAT_WITHIN(1e-6f, 0.0f,      features_vpd_kpa(22.0f, 100.0f));
}

void test_vpd_entra_al_vector(void) {
  float x[FEAT_N]; bool w;
  MuestraCruda m = muestra(1500, 800, 25.0f, 60.0f);
  TEST_ASSERT_TRUE(features_empujar(&buf, &m, x, &w));
  TEST_ASSERT_FLOAT_WITHIN(1e-4f, 1.267111f, x[FEAT_VPD_KPA]);
  TEST_ASSERT_EQUAL_FLOAT(25.0f, x[FEAT_TEMP_C]);
  TEST_ASSERT_EQUAL_FLOAT(60.0f, x[FEAT_HUM_AIRE_PCT]);
}

// ─── Warm-up ──────────────────────────────────────────────────────────────
void test_warmup_primeras_12_muestras(void) {
  float x[FEAT_N]; bool w;
  for (int i = 0; i < 12; i++) {
    MuestraCruda m = muestra(1000.0f + 10.0f * i, 100.0f * i);
    TEST_ASSERT_TRUE(features_empujar(&buf, &m, x, &w));
    TEST_ASSERT_TRUE_MESSAGE(w, "con < 12 muestras previas tiene que estar en warm-up");
    TEST_ASSERT_EQUAL_FLOAT(0.0f, x[FEAT_SUELO_DELTA_1H]);
    // La media usa lo que haya: 0, 100, ..., 100·i → 50·i
    TEST_ASSERT_FLOAT_WITHIN(1e-3f, 50.0f * i, x[FEAT_LUZ_MEDIA_1H]);
  }
  TEST_ASSERT_EQUAL_UINT8(12, buf.n);
}

// ─── Rampa conocida ───────────────────────────────────────────────────────
void test_rampa_conocida_sale_de_warmup_en_la_13(void) {
  float x[FEAT_N]; bool w = true;
  for (int i = 0; i < 13; i++) {
    MuestraCruda m = muestra(1000.0f + 10.0f * i, 100.0f * i);
    features_empujar(&buf, &m, x, &w);
  }
  TEST_ASSERT_FALSE(w);
  TEST_ASSERT_EQUAL_FLOAT(1120.0f, x[FEAT_SUELO_MV]);
  TEST_ASSERT_EQUAL_FLOAT(120.0f,  x[FEAT_SUELO_DELTA_1H]);   // 1120 − 1000
  TEST_ASSERT_EQUAL_FLOAT(1200.0f, x[FEAT_LUZ_MV]);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 600.0f, x[FEAT_LUZ_MEDIA_1H]);   // media de 0..1200
  TEST_ASSERT_EQUAL_UINT32(13, buf.total);
}

void test_rampa_descendente_da_delta_negativo(void) {
  float x[FEAT_N]; bool w;
  for (int i = 0; i < 20; i++) {
    MuestraCruda m = muestra(2000.0f - 5.0f * i, 500.0f);
    features_empujar(&buf, &m, x, &w);
  }
  TEST_ASSERT_EQUAL_FLOAT(-60.0f, x[FEAT_SUELO_DELTA_1H]);   // 12 pasos de −5
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, 500.0f, x[FEAT_LUZ_MEDIA_1H]);
}

// ─── Wrap del buffer circular ─────────────────────────────────────────────
void test_wrap_del_buffer_circular(void) {
  float x[FEAT_N]; bool w;
  // 40 muestras = más de 3 vueltas a la ventana de 13. Suelo = i², luz = 7·i
  // (no lineales, para que un índice corrido se note).
  for (int i = 0; i < 40; i++) {
    MuestraCruda m = muestra((float)(i * i), 7.0f * i);
    TEST_ASSERT_TRUE(features_empujar(&buf, &m, x, &w));
    if (i >= 12) {
      TEST_ASSERT_FALSE(w);
      TEST_ASSERT_EQUAL_FLOAT((float)(i * i - (i - 12) * (i - 12)), x[FEAT_SUELO_DELTA_1H]);
      float media = 0;
      for (int k = i - 12; k <= i; k++) media += 7.0f * k;
      media /= 13.0f;
      TEST_ASSERT_FLOAT_WITHIN(1e-3f, media, x[FEAT_LUZ_MEDIA_1H]);
    }
  }
  TEST_ASSERT_EQUAL_UINT8(FEAT_VENTANA, buf.n);
  TEST_ASSERT_EQUAL_UINT32(40, buf.total);
  TEST_ASSERT_EQUAL_UINT8(40 % FEAT_VENTANA, buf.cabeza);
}

// ─── Faltantes ────────────────────────────────────────────────────────────
void test_suelo_y_luz_faltantes_repiten_el_anterior(void) {
  float x[FEAT_N]; bool w;
  MuestraCruda a = muestra(1500, 900);
  features_empujar(&buf, &a, x, &w);
  MuestraCruda b = muestra(NAN, NAN);
  TEST_ASSERT_TRUE(features_empujar(&buf, &b, x, &w));
  TEST_ASSERT_EQUAL_FLOAT(1500.0f, x[FEAT_SUELO_MV]);
  TEST_ASSERT_EQUAL_FLOAT(900.0f,  x[FEAT_LUZ_MV]);
  TEST_ASSERT_BITS_HIGH(FEAT_MARCA_SUELO_REPETIDO | FEAT_MARCA_LUZ_REPETIDA, buf.marcas);
  TEST_ASSERT_EQUAL_UINT32(2, buf.total);   // la muestra SÍ entra (repetida)
  // La repetición queda en la ventana: la siguiente la ve como anterior.
  MuestraCruda c = muestra(NAN, 1000);
  features_empujar(&buf, &c, x, &w);
  TEST_ASSERT_EQUAL_FLOAT(1500.0f, x[FEAT_SUELO_MV]);
  TEST_ASSERT_FLOAT_WITHIN(1e-3f, (900.0f + 900.0f + 1000.0f) / 3.0f, x[FEAT_LUZ_MEDIA_1H]);
}

void test_primera_muestra_sin_suelo_no_entra(void) {
  float x[FEAT_N] = {0}; bool w;
  MuestraCruda m = muestra(NAN, 800);
  TEST_ASSERT_FALSE(features_empujar(&buf, &m, x, &w));
  TEST_ASSERT_TRUE(w);
  TEST_ASSERT_BITS_HIGH(FEAT_MARCA_SIN_SUELO, buf.marcas);
  TEST_ASSERT_EQUAL_UINT32(0, buf.total);
  TEST_ASSERT_EQUAL_UINT8(0, buf.n);
  // El vector sale todo en NAN (como features.py), no en 0: un 0 en el log
  // [INF] parecería una lectura.
  for (int k = 0; k < FEAT_N; k++) TEST_ASSERT_TRUE(isnan(x[k]));
}

void test_dht_faltante_usa_ultimo_valido(void) {
  float x[FEAT_N]; bool w;
  MuestraCruda a = muestra(1500, 800, 22.0f, 55.0f);
  features_empujar(&buf, &a, x, &w);
  MuestraCruda b = muestra(1510, 810, NAN, NAN, 30.0f);   // el termistor nunca se usa
  TEST_ASSERT_TRUE(features_empujar(&buf, &b, x, &w));
  TEST_ASSERT_EQUAL_FLOAT(22.0f, x[FEAT_TEMP_C]);
  TEST_ASSERT_EQUAL_FLOAT(55.0f, x[FEAT_HUM_AIRE_PCT]);
  TEST_ASSERT_FLOAT_WITHIN(1e-5f, features_vpd_kpa(22.0f, 55.0f), x[FEAT_VPD_KPA]);
  TEST_ASSERT_BITS_HIGH(FEAT_MARCA_DHT_ANTERIOR, buf.marcas);
  TEST_ASSERT_BITS_LOW(FEAT_MARCA_SIN_TEMP | FEAT_MARCA_SIN_HUM, buf.marcas);
}

void test_sin_dht_nunca_no_infiere_aunque_haya_termistor(void) {
  // Contrato §4: el termistor NO es respaldo de T. Sin DHT válido desde el
  // reset no hay T ni HR y no se infiere, aunque el termistor lea bien.
  float x[FEAT_N]; bool w;
  MuestraCruda m = muestra(1500, 800, NAN, NAN, 21.5f);
  TEST_ASSERT_FALSE(features_empujar(&buf, &m, x, &w));
  TEST_ASSERT_TRUE(isnan(x[FEAT_TEMP_C]));
  TEST_ASSERT_TRUE(isnan(x[FEAT_HUM_AIRE_PCT]));
  TEST_ASSERT_TRUE(isnan(x[FEAT_VPD_KPA]));
  TEST_ASSERT_BITS_HIGH(FEAT_MARCA_SIN_TEMP | FEAT_MARCA_SIN_HUM, buf.marcas);
  TEST_ASSERT_EQUAL_UINT32(1, buf.total);   // suelo y luz sí entran a la ventana
  // Cuando aparece el DHT, se infiere normalmente y el delta ve la historia.
  MuestraCruda d = muestra(1520, 820, 20.0f, 50.0f);
  TEST_ASSERT_TRUE(features_empujar(&buf, &d, x, &w));
  TEST_ASSERT_EQUAL_FLOAT(20.0f, x[FEAT_TEMP_C]);
  TEST_ASSERT_EQUAL_UINT8(0, buf.marcas);
}

void test_hum_valida_sin_temp_no_infiere(void) {
  // Caso borde: HR válida pero T del DHT nunca. Antes salía T del termistor;
  // ahora no hay T y no se infiere.
  float x[FEAT_N]; bool w;
  MuestraCruda m = muestra(1500, 800, NAN, 50.0f, 21.5f);
  TEST_ASSERT_FALSE(features_empujar(&buf, &m, x, &w));
  TEST_ASSERT_TRUE(isnan(x[FEAT_TEMP_C]));
  TEST_ASSERT_EQUAL_FLOAT(50.0f, x[FEAT_HUM_AIRE_PCT]);
  TEST_ASSERT_BITS_HIGH(FEAT_MARCA_SIN_TEMP, buf.marcas);
  TEST_ASSERT_BITS_LOW(FEAT_MARCA_SIN_HUM, buf.marcas);
}

void test_sin_dht_ni_termistor_no_infiere(void) {
  float x[FEAT_N]; bool w;
  MuestraCruda m = muestra(1500, 800, NAN, NAN, NAN);
  TEST_ASSERT_FALSE(features_empujar(&buf, &m, x, &w));
  TEST_ASSERT_BITS_HIGH(FEAT_MARCA_SIN_TEMP, buf.marcas);
}

// ─── Consulta (envío forzado) ─────────────────────────────────────────────
void test_consultar_no_modifica_el_buffer(void) {
  float x[FEAT_N], xc[FEAT_N]; bool w, wc; uint8_t marcas;
  for (int i = 0; i < 15; i++) {
    MuestraCruda m = muestra(1000.0f + 3.0f * i, 50.0f * i);
    features_empujar(&buf, &m, x, &w);
  }
  BufferFeatures antes;
  memcpy(&antes, &buf, sizeof(buf));   // copia byte a byte, padding incluido
  MuestraCruda q = muestra(1777, NAN, NAN, NAN);
  TEST_ASSERT_TRUE(features_consultar(&buf, &q, xc, &wc, &marcas));
  TEST_ASSERT_EQUAL_MEMORY(&antes, &buf, sizeof(buf));
  // Y da lo mismo que empujar de verdad.
  TEST_ASSERT_TRUE(features_empujar(&buf, &q, x, &w));
  TEST_ASSERT_EQUAL_FLOAT_ARRAY(x, xc, FEAT_N);
  TEST_ASSERT_EQUAL(w, wc);
  TEST_ASSERT_EQUAL_UINT8(buf.marcas, marcas);
}

void test_reset_vacia_el_buffer(void) {
  float x[FEAT_N]; bool w;
  for (int i = 0; i < 20; i++) { MuestraCruda m = muestra(1500, 500); features_empujar(&buf, &m, x, &w); }
  features_reset(&buf);
  TEST_ASSERT_EQUAL_UINT8(0, buf.n);
  TEST_ASSERT_EQUAL_UINT32(0, buf.total);
  TEST_ASSERT_FALSE(buf.hay_temp_dht);
  MuestraCruda m = muestra(1600, 600);
  features_empujar(&buf, &m, x, &w);
  TEST_ASSERT_TRUE(w);   // un reinicio vuelve a warm-up
}

// ─── Paridad con features.py ──────────────────────────────────────────────
void test_paridad_con_python(void) {
#ifdef HAY_PARIDAD_FEATURES
  float x[FEAT_N]; bool w;
  for (int i = 0; i < PAR_N; i++) {
    if (PAR_RESET[i]) features_reset(&buf);
    MuestraCruda m = {PAR_CRUDO[i][0], PAR_CRUDO[i][1], PAR_CRUDO[i][2], PAR_CRUDO[i][3], PAR_CRUDO[i][4]};
    bool ok = features_empujar(&buf, &m, x, &w);
    char msg[48];
    snprintf(msg, sizeof(msg), "fila %d", i);
    TEST_ASSERT_EQUAL_MESSAGE(PAR_OK[i] != 0, ok, msg);
    if (!ok) continue;
    TEST_ASSERT_EQUAL_MESSAGE(PAR_WARMUP[i] != 0, w, msg);
    for (int k = 0; k < FEAT_N; k++) {
      // float32 vs float64: tolerancia relativa chica + absoluta mínima.
      float tol = 1e-4f * fabsf(PAR_X[i][k]) + 1e-3f;
      TEST_ASSERT_FLOAT_WITHIN_MESSAGE(tol, PAR_X[i][k], x[k], msg);
    }
  }
#else
  TEST_FAIL_MESSAGE("falta test/test_features/paridad_features.h: regenerarlo con python -m plantaia_ml.exportar_c");
#endif
}

int main(int, char **) {
  UNITY_BEGIN();
  RUN_TEST(test_vpd_valores_conocidos);
  RUN_TEST(test_vpd_entra_al_vector);
  RUN_TEST(test_warmup_primeras_12_muestras);
  RUN_TEST(test_rampa_conocida_sale_de_warmup_en_la_13);
  RUN_TEST(test_rampa_descendente_da_delta_negativo);
  RUN_TEST(test_wrap_del_buffer_circular);
  RUN_TEST(test_suelo_y_luz_faltantes_repiten_el_anterior);
  RUN_TEST(test_primera_muestra_sin_suelo_no_entra);
  RUN_TEST(test_dht_faltante_usa_ultimo_valido);
  RUN_TEST(test_sin_dht_nunca_no_infiere_aunque_haya_termistor);
  RUN_TEST(test_hum_valida_sin_temp_no_infiere);
  RUN_TEST(test_sin_dht_ni_termistor_no_infiere);
  RUN_TEST(test_consultar_no_modifica_el_buffer);
  RUN_TEST(test_reset_vacia_el_buffer);
  RUN_TEST(test_paridad_con_python);
  return UNITY_END();
}
