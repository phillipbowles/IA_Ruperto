// PlantaIa — buffer circular y features. Ver features.h y README.md.
#include "features.h"

#include <math.h>
#include <string.h>

static inline bool valido(float v) { return isfinite(v); }

float features_vpd_kpa(float temp_c, float hum_pct) {
  // Presión de saturación (Tetens) por el déficit relativo. Con HR > 100 por
  // ruido del DHT daría negativo: se deja así, igual que en Python, para no
  // tener dos recortes distintos que mantener sincronizados.
  float es = 0.6108f * expf(17.27f * temp_c / (temp_c + 237.3f));
  return es * (1.0f - hum_pct / 100.0f);
}

void features_reset(BufferFeatures *buf) {
  memset(buf, 0, sizeof(*buf));
  buf->temp_ult = NAN;
  buf->hum_ult  = NAN;
}

// Índice de la muestra que está `atras` posiciones detrás de la última
// empujada (atras = 0 → la última). Precondición: atras < buf->n.
static inline uint8_t idx_atras(const BufferFeatures *buf, uint8_t atras) {
  int i = (int)buf->cabeza - 1 - (int)atras;
  while (i < 0) i += FEAT_VENTANA;
  return (uint8_t)i;
}

bool features_empujar(BufferFeatures *buf, const MuestraCruda *m,
                      float x_out[FEAT_N], bool *warmup) {
  uint8_t marcas = 0;

  // ── Suelo y luz: faltante → repetir el anterior del buffer ──────────────
  float suelo = m->suelo_mv;
  float luz   = m->luz_mv;
  if (!valido(suelo)) {
    if (buf->n > 0) { suelo = buf->suelo[idx_atras(buf, 0)]; marcas |= FEAT_MARCA_SUELO_REPETIDO; }
    else            { marcas |= FEAT_MARCA_SIN_SUELO; }
  }
  if (!valido(luz)) {
    if (buf->n > 0) { luz = buf->luz[idx_atras(buf, 0)]; marcas |= FEAT_MARCA_LUZ_REPETIDA; }
    else            { marcas |= FEAT_MARCA_SIN_LUZ; }
  }
  bool suelo_real = !(marcas & (FEAT_MARCA_SUELO_REPETIDO | FEAT_MARCA_SIN_SUELO));
  if (marcas & (FEAT_MARCA_SIN_SUELO | FEAT_MARCA_SIN_LUZ)) {
    // Primera muestra tras el reset y sin suelo o sin luz: no hay con qué
    // rellenar, así que no entra a la ventana (tampoco se actualiza T/HR, para
    // que una muestra descartada no deje rastro). El vector sale todo en NAN,
    // igual que features.py: sin esto el log mostraba x=[0,0,...], que parece
    // una lectura.
    for (int k = 0; k < FEAT_N; k++) x_out[k] = NAN;
    buf->marcas = marcas;
    if (warmup) *warmup = true;
    return false;
  }

  // ── T y HR: último válido del DHT ───────────────────────────────────────
  bool t_ok = valido(m->temp_dht_c);
  bool h_ok = valido(m->hum_aire_pct);
  if (t_ok) { buf->temp_ult = m->temp_dht_c;   buf->hay_temp_dht = true; }
  if (h_ok) { buf->hum_ult  = m->hum_aire_pct; buf->hay_hum      = true; }
  if (!t_ok || !h_ok) marcas |= FEAT_MARCA_DHT_ANTERIOR;

  // Sin respaldo con el termistor (contrato §4): su conversión en el fw 1.1.0
  // está invertida y, sin DHT, tampoco hay HR. m->temp_ntc_c no se lee acá.
  float temp = buf->hay_temp_dht ? buf->temp_ult : NAN;
  if (!buf->hay_temp_dht) marcas |= FEAT_MARCA_SIN_TEMP;
  float hum = buf->hay_hum ? buf->hum_ult : NAN;
  if (!buf->hay_hum) marcas |= FEAT_MARCA_SIN_HUM;
  if (!buf->hay_temp_dht && !buf->hay_hum) marcas &= ~FEAT_MARCA_DHT_ANTERIOR;  // no hay "anterior"

  // ── Riego: caída brusca de una lectura real, fuera de warm-up ───────────
  // (antes de empujar: se compara contra la última muestra de la ventana).
  if (suelo_real && m->ts_unix > 0 && buf->n >= FEAT_LAG_DELTA &&
      buf->suelo[idx_atras(buf, 0)] - suelo >= FEAT_RIEGO_CAIDA_MV) {
    buf->riego_ts = m->ts_unix;
  }
  float h_riego = FEAT_RIEGO_TOPE_H;
  if (buf->riego_ts > 0 && m->ts_unix >= buf->riego_ts) {
    float h = (float)(m->ts_unix - buf->riego_ts) / 3600.0f;   // resta entera: exacta
    h_riego = h < FEAT_RIEGO_TOPE_H ? h : FEAT_RIEGO_TOPE_H;
  }

  // ── Empujar al buffer circular ──────────────────────────────────────────
  buf->suelo[buf->cabeza] = suelo;
  buf->luz[buf->cabeza]   = luz;
  buf->cabeza = (uint8_t)((buf->cabeza + 1) % FEAT_VENTANA);
  if (buf->n < FEAT_VENTANA) buf->n++;
  buf->total++;
  buf->marcas = marcas;

  // ── Warm-up: hacen falta 12 muestras ANTERIORES a la actual ─────────────
  bool en_warmup = buf->n <= FEAT_LAG_DELTA;    // n incluye la actual
  if (warmup) *warmup = en_warmup;

  float delta = en_warmup ? 0.0f : suelo - buf->suelo[idx_atras(buf, FEAT_LAG_DELTA)];

  // Media de luz sobre lo que haya en la ventana (≤ 13, incluida la actual),
  // sumada de la más vieja a la más nueva. Se recalcula entera cada vez en
  // lugar de llevar una suma corrida: 13 sumas no cuestan nada y no acumula
  // error de redondeo en float a lo largo de semanas.
  float suma = 0.0f;
  for (int k = (int)buf->n - 1; k >= 0; k--) suma += buf->luz[idx_atras(buf, (uint8_t)k)];
  float luz_media = suma / (float)buf->n;

  x_out[FEAT_SUELO_MV]       = suelo;
  x_out[FEAT_SUELO_DELTA_1H] = delta;
  x_out[FEAT_TEMP_C]         = temp;
  x_out[FEAT_HUM_AIRE_PCT]   = hum;
  x_out[FEAT_VPD_KPA]        = (valido(temp) && valido(hum)) ? features_vpd_kpa(temp, hum) : NAN;
  x_out[FEAT_LUZ_MV]         = luz;
  x_out[FEAT_LUZ_MEDIA_1H]   = luz_media;
  x_out[FEAT_H_DESDE_RIEGO]  = h_riego;

  return valido(temp) && valido(hum);
}

bool features_consultar(const BufferFeatures *buf, const MuestraCruda *m,
                        float x_out[FEAT_N], bool *warmup, uint8_t *marcas_out) {
  // Copia de ~130 bytes en el stack: garantiza la misma semántica que
  // features_empujar sin duplicar la lógica.
  BufferFeatures copia = *buf;
  bool ok = features_empujar(&copia, m, x_out, warmup);
  if (marcas_out) *marcas_out = copia.marcas;
  return ok;
}
