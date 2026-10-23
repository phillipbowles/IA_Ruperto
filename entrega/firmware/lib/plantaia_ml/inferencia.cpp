// PlantaIa — un paso de inferencia. Ver inferencia.h y README.md.
#include "inferencia.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "modelo_plantaia.h"

#if PLANTAIA_N_FEATURES != FEAT_N
#error "modelo_plantaia.h no usa los 8 features del contrato §4 (si es un subconjunto, el exportador remapea adentro de plantaia_predecir)"
#endif

static const char *const ETIQUETAS_MODELO[] = {"sin_prediccion", "saludable", "estresada", "marchita"};

const char *plantaia_etiqueta(int clase) {
  return (clase >= 1 && clase <= 3) ? ETIQUETAS_MODELO[clase] : ETIQUETAS_MODELO[0];
}

const char *plantaia_modelo_version(void) { return PLANTAIA_MODELO_VERSION; }

void plantaia_inferir(BufferFeatures *buf, const MuestraCruda *m, bool empujar,
                      plantaia_reloj_us_t reloj_us, Inferencia *out) {
  memset(out, 0, sizeof(*out));
  bool warmup = true;
  uint8_t marcas = 0;
  bool ok;
  if (empujar) {
    ok     = features_empujar(buf, m, out->x, &warmup);
    marcas = buf->marcas;
  } else {
    ok = features_consultar(buf, m, out->x, &warmup, &marcas);
  }
  out->ok       = ok;
  out->warmup   = warmup;
  out->empujada = empujar;
  out->marcas   = marcas;
  out->n        = buf->total;   // en una consulta queda el n del último tick

  if (!ok) {
    for (int k = 0; k < FEAT_N; k++) if (!isfinite(out->x[k])) out->x[k] = NAN;
    out->clase = 0;
    return;
  }

  // Se cronometra SÓLO el modelo: es el número que se compara con el
  // presupuesto de < 1 ms del contrato §5.3. (En el host la resolución del
  // reloj es de 1 µs, así que un modelo chico puede dar 0 ó 1.)
  uint32_t t0 = reloj_us ? reloj_us() : 0;
  out->clase  = plantaia_predecir(out->x, out->proba);
  uint32_t t1 = reloj_us ? reloj_us() : 0;
  out->t_us   = t1 - t0;
}

// Formatos fijos por feature: los enteros en mV y % sin decimales, T con 1,
// VPD con 2, horas desde el riego con 1. El parser de docs/entrega2 asume exactamente esto.
static int fmt_x(char *dst, size_t tam, const float x[FEAT_N]) {
  return snprintf(dst, tam, "[%.0f,%.0f,%.1f,%.0f,%.2f,%.0f,%.0f,%.1f]",
                  (double)x[0], (double)x[1], (double)x[2], (double)x[3],
                  (double)x[4], (double)x[5], (double)x[6], (double)x[7]);
}

int plantaia_linea_inf(const Inferencia *inf, const char *tag, char *dst, size_t tam) {
  char xs[96];
  fmt_x(xs, sizeof(xs), inf->x);
  if (!inf->ok) {
    return snprintf(dst, tam, "%s n=%lu warmup=%d x=%s -> %s p=[] t_us=0",
                    tag ? tag : "[INF]", (unsigned long)inf->n, inf->warmup ? 1 : 0,
                    xs, plantaia_etiqueta(0));
  }
  return snprintf(dst, tam, "%s n=%lu warmup=%d x=%s -> %s p=[%.2f,%.2f,%.2f] t_us=%lu",
                  tag ? tag : "[INF]", (unsigned long)inf->n, inf->warmup ? 1 : 0, xs,
                  plantaia_etiqueta(inf->clase),
                  (double)inf->proba[0], (double)inf->proba[1], (double)inf->proba[2],
                  (unsigned long)inf->t_us);
}

int plantaia_linea_fal(const Inferencia *inf, char *dst, size_t tam) {
  static const struct { uint8_t bit; const char *nombre; } MARCAS[] = {
    {FEAT_MARCA_SUELO_REPETIDO, "suelo_repetido"},
    {FEAT_MARCA_LUZ_REPETIDA,   "luz_repetida"},
    {FEAT_MARCA_DHT_ANTERIOR,   "dht_anterior"},
    {FEAT_MARCA_SIN_SUELO,      "sin_suelo"},
    {FEAT_MARCA_SIN_LUZ,        "sin_luz"},
    {FEAT_MARCA_SIN_TEMP,       "sin_temp"},
    {FEAT_MARCA_SIN_HUM,        "sin_hum"},
  };
  if (tam == 0) return 0;
  dst[0] = '\0';
  if (inf->marcas == 0) return 0;
  int len = snprintf(dst, tam, "[FAL] n=%lu", (unsigned long)inf->n);
  for (size_t i = 0; i < sizeof(MARCAS) / sizeof(MARCAS[0]); i++) {
    if ((inf->marcas & MARCAS[i].bit) && len >= 0 && (size_t)len < tam)
      len += snprintf(dst + len, tam - (size_t)len, " %s", MARCAS[i].nombre);
  }
  return len;
}
