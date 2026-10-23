#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <time.h>
#include "secrets.h"

// Inferencia en la placa (Tarea 2): C++ puro en lib/plantaia_ml, el mismo
// código que corren los tests y el replay en el host. Ver su README.md.
#include "features.h"
#include "inferencia.h"

// Versión del firmware: viaja en cada muestra para poder separar en el análisis
// los datos tomados antes y después de un cambio de calibración o de lógica.
// 2.0.0: el semáforo pasa a ser la salida del modelo que corre en la placa.
#define FW_VERSION "2.0.0"

// ─── Pines (fijo, ver CLAUDE.md — no cambiar) ─────────────────────────────
#define PIN_LUZ          34
#define PIN_TERMISTOR    32   // cableado real confirmado por tacto 2026-09-12 (antes 35)
#define PIN_SUELO_AO     35   // cableado real confirmado por tacto 2026-09-12 (antes 32)
#define PIN_SUELO_VCC    33
#define PIN_DHT           4
#define PIN_LED_VERDE    27
#define PIN_LED_AMARILLO 26
#define PIN_LED_ROJO     25
#define PIN_BOTON        19   // cableado real confirmado 2026-09-12 (antes 13)

// ─── Parámetros generales ──────────────────────────────────────────────────
#define DHT_TYPE           DHT11
#define LCD_ADDR           0x27
#define LCD_COLS           16
#define LCD_ROWS            2
#define INTERVALO_LECTURA  2000UL          // 2 s — actualizar LCD/Serial
#define INTERVALO_ENVIO  300000UL          // 5 min entre envíos
#define TIMEOUT_WIFI      15000UL
#define DEBOUNCE_MS          50UL
#define PULSACION_LARGA    2000UL
#define MOSTRAR_OBS_MS     3000UL          // cuánto queda en el LCD la observación manual

// ─── Calibración sensores ──────────────────────────────────────────────────
// OJO: el ADC del ESP32 con atenuación 11 dB satura cerca de 3100 mV y la curva
// se aplasta arriba de ~2500 mV, así que luz_pct nunca llega a 100 y está
// comprimido en el extremo de luz fuerte. Es un valor de referencia para el LCD:
// el análisis usa luz_raw y luz_mv, que ahora sí viajan crudos. Ver docs/CALIBRACION.md.
#define LUZ_MV_MAX      3300

// Sonda de suelo RESISTIVA (tipo YL-69/HL-69, dos púas + plaquita LM393).
// Seco = alta resistencia = AO cerca del riel; mojado = AO bajo. Por eso
// SECO > MOJADO. Los dos valores están PENDIENTES de medir con el sustrato real.
#define SUELO_MV_SECO   2800   // PENDIENTE: medir con el sustrato real seco
#define SUELO_MV_MOJADO 1000   // PENDIENTE: medir con el sustrato real saturado

// NO SUBIR este valor. En una sonda resistiva el divisor se asienta en
// microsegundos: los 100 ms son margen de sobra. Lo que sí pasa mientras hay
// tensión aplicada es electrólisis — los iones migran y la lectura deriva hacia
// abajo de forma continua, así que alargar la estabilización empeora el dato y
// corroe más rápido los electrodos. Lo que importa es que el tiempo sea SIEMPRE
// el mismo, para que la deriva sea igual en todas las muestras.
#define SUELO_MS_ESTAB   100

// NTC — divisor: VCC → R_FIJO → VOUT → NTC → GND
// NTC_R0 calibrado en punto único 2026-09-12 contra el DHT11 (21.0C real con
// termistor_mv=1096 en simultáneo, antes daba 41.6C con R0=10000). El R_FIJO
// real de la plaqueta KS0033 no coincide con el nominal de 10k asumido acá;
// en vez de adivinarlo, se ajustó R0 para que la curva pase por ese punto.
// Es calibración de un solo punto: confiable cerca de temperatura ambiente,
// pero para precisión en todo el rango (heladera, sol directo, etc.) hace
// falta un segundo punto de referencia — ver docs/CALIBRACION.md.
#define NTC_R_FIJO  10000.0f
#define NTC_R0       4150.0f
#define NTC_T0        298.15f
#define NTC_BETA     3950.0f
#define NTC_VCC      3300.0f

// ─── Hora ─────────────────────────────────────────────────────────────────
// La placa sincroniza NTP en UTC (offset 0) y el timestamp viaja como unix
// epoch. La conversión a hora local se hace recién en el front. Mezclar horas
// locales entre placa, servidor y el timelapse del celular es fuente de errores
// al cruzar las series.
#define EPOCH_MINIMO_VALIDO 1735689600UL   // 2025-01-01 — corte de cordura

// ─── Objetos globales ──────────────────────────────────────────────────────
DHT              dht(PIN_DHT, DHT_TYPE);
LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);
Preferences      prefs;

// ─── Estructuras ──────────────────────────────────────────────────────────
struct LectADC { uint16_t mv; int raw; };

struct Sensores {
  float temp_dht, hum_aire;
  int   luz_raw;    float luz_mv,   luz_pct;
  int   ntc_raw;    float ntc_mv,   temp_ntc;
  int   suelo_raw;  float suelo_mv;
  bool  dht_ok, ntc_ok;
};

// ─── Estado global ────────────────────────────────────────────────────────
const char* ETIQUETAS[] = {"sin_etiquetar", "saludable", "estresada", "marchita"};
const int   N_COND = 4;

int           condicion    = 0;
uint32_t      boot_id      = 0;
uint32_t      n_muestra    = 0;
bool          forzar_envio = false;
// Distingue la muestra donde Manuel realmente observó la planta (manual) de las
// que heredan esa etiqueta hasta la próxima pulsación (propagada). Sin esto, en
// el análisis no se puede saber qué filas son observación y cuáles son relleno.
bool          etiqueta_nueva = false;
unsigned long t_lectura    = 0;
unsigned long t_envio      = 0;
unsigned long t_boton_down = 0;
bool          boton_prev   = false;
String        estado_nube  = "---";
Sensores      s;

// ─── Estado de la inferencia ──────────────────────────────────────────────
// La ventana de 1 h vive en RAM: un reinicio la vacía y se vuelve a warm-up,
// igual que el Python que corta los tramos por boot_id.
BufferFeatures buf_feat;
Inferencia     inf_ult;              // última predicción (tick o consulta)
bool           hay_inf      = false; // ¿ya se intentó inferir al menos una vez?
bool           primer_tick  = true;  // inferir ya en el primer loop, sin esperar 5 min
unsigned long  t_msg_obs    = 0;     // momento en que se mostró la observación manual
bool           msg_obs      = false;
bool           lcd_pagina   = false; // alterna la 2da línea: suelo/nube ↔ T/H

// ─── Hora sincronizada? ───────────────────────────────────────────────────
bool hora_valida() {
  return time(nullptr) > (time_t)EPOCH_MINIMO_VALIDO;
}

// ─── ADC: mediana de 9 muestras ──────────────────────────────────────────
LectADC mediana9(uint8_t pin) {
  uint16_t mv[9]; int raw[9];
  for (int i = 0; i < 9; i++) {
    raw[i] = analogRead(pin);
    mv[i]  = (uint16_t)analogReadMilliVolts(pin);
    delay(2);
  }
  for (int i = 0; i < 8; i++)
    for (int j = 0; j < 8-i; j++)
      if (mv[j] > mv[j+1]) {
        uint16_t tm = mv[j]; mv[j] = mv[j+1]; mv[j+1] = tm;
        int      tr = raw[j]; raw[j] = raw[j+1]; raw[j+1] = tr;
      }
  return {mv[4], raw[4]};
}

// ─── Lectura de sensores ──────────────────────────────────────────────────
void leer_sensores() {
  // DHT11: readHumidity(force=true) hace la lectura hardware y cachea T+H.
  // readTemperature() sin force usa ese mismo cache — una sola lectura física.
  // Con fuerza en temperatura se dispara una segunda lectura inmediata → falla.
  float h = NAN, t = NAN;
  for (int i = 0; i < 3; i++) {
    if (i > 0) delay(2000);       // DHT11 necesita ≥1 s entre lecturas
    h = dht.readHumidity(true);   // fuerza lectura hardware → cachea T y H
    t = dht.readTemperature();    // usa cache del readHumidity anterior
    if (!isnan(h) && !isnan(t)) break;
  }
  s.dht_ok   = !isnan(h) && !isnan(t);
  s.hum_aire = s.dht_ok ? h : NAN;
  s.temp_dht = s.dht_ok ? t : NAN;

  // LDR — GPIO34
  LectADC luz = mediana9(PIN_LUZ);
  s.luz_raw = luz.raw;
  s.luz_mv  = luz.mv;
  s.luz_pct = constrain((int)((float)luz.mv * 100 / LUZ_MV_MAX), 0, 100);

  // NTC — GPIO32
  LectADC ntc = mediana9(PIN_TERMISTOR);
  s.ntc_raw = ntc.raw;
  s.ntc_mv  = ntc.mv;
  if (ntc.mv > 0 && ntc.mv < (uint16_t)NTC_VCC) {
    float r    = NTC_R_FIJO * ntc.mv / (NTC_VCC - ntc.mv);
    float tk   = 1.0f / (1.0f/NTC_T0 + log(r/NTC_R0)/NTC_BETA);
    s.temp_ntc = tk - 273.15f;
    s.ntc_ok   = !isnan(s.temp_ntc);
  } else {
    s.ntc_ok   = false;
    s.temp_ntc = NAN;
  }

  // Sonda de suelo — alimentar GPIO33 solo mientras se mide
  digitalWrite(PIN_SUELO_VCC, HIGH);
  delay(SUELO_MS_ESTAB);
  LectADC suelo = mediana9(PIN_SUELO_AO);
  digitalWrite(PIN_SUELO_VCC, LOW);
  s.suelo_raw = suelo.raw;
  s.suelo_mv  = suelo.mv;
  // suelo_pct queda sin calcular hasta calibrar SUELO_MV_SECO/MOJADO con el
  // sustrato real (ver docs/CALIBRACION.md) — mandar un % inventado es peor
  // que no mandar nada.
}

// ─── Muestra para el modelo ───────────────────────────────────────────────
// Traduce la lectura a lo que entra al buffer. Faltante = NAN, nunca 0.
// La sonda de suelo saturada contra un riel del ADC (suelo_raw 0 ó 4095) es la
// sonda fuera del sustrato: se trata como faltante y el buffer repite el valor
// anterior (el Python descarta esas filas por la misma razón). La luz saturada
// NO es faltante: es luz fuerte de verdad. Sin DHT11 válido desde el arranque
// no se infiere: el termistor no es respaldo de T (y tampoco habría HR).
MuestraCruda muestra_cruda() {
  MuestraCruda m;
  bool suelo_sat = s.suelo_raw <= 0 || s.suelo_raw >= 4095;
  m.suelo_mv     = suelo_sat ? NAN : s.suelo_mv;
  m.luz_mv       = s.luz_mv;
  m.temp_dht_c   = s.dht_ok ? s.temp_dht : NAN;
  m.hum_aire_pct = s.dht_ok ? s.hum_aire : NAN;
  m.temp_ntc_c   = s.ntc_ok ? s.temp_ntc : NAN;   // no entra a las features (contrato §4)
  return m;
}

static uint32_t reloj_micros() { return (uint32_t)micros(); }

// ─── Semáforo ─────────────────────────────────────────────────────────────
// Refleja la PREDICCIÓN del modelo, no la observación manual (eso es el botón).
// Sin predicción (todavía no se infirió, o el vector quedó incompleto: p. ej.
// nunca respondió el DHT11) quedan los tres APAGADOS. Se eligió apagado y no
// rojo parpadeando porque el rojo es "marchita": un rojo por falta de datos
// haría regar una planta que puede estar bien. El LCD dice "Pred:sin datos" y
// el arranque hace una prueba de lámparas, así que "apagado" no se confunde
// con "placa muerta".
void actualizar_semaforo() {
  int c = (hay_inf && inf_ult.ok) ? inf_ult.clase : 0;
  digitalWrite(PIN_LED_VERDE,    c == 1);
  digitalWrite(PIN_LED_AMARILLO, c == 2);
  digitalWrite(PIN_LED_ROJO,     c == 3);
}

// ─── Inferencia ───────────────────────────────────────────────────────────
// empujar = true  → tick de 5 min: la muestra entra a la ventana de 1 h.
// empujar = false → envío forzado: se predice con la lectura actual pero la
//                   ventana NO avanza (ver README de lib/plantaia_ml).
// No depende del WiFi: se llama antes del POST y el LED se actualiza aunque
// el envío falle.
void inferir(bool empujar) {
  MuestraCruda m = muestra_cruda();
  plantaia_inferir(&buf_feat, &m, empujar, reloj_micros, &inf_ult);
  hay_inf = true;
  actualizar_semaforo();

  char linea[200];
  if (plantaia_linea_fal(&inf_ult, linea, sizeof(linea)) > 0) Serial.println(linea);
  // [INF] = tick de 5 min (serie regular, la que se parsea); [CON] = consulta
  // por envío forzado, mismo formato pero con otro prefijo para no mezclarlas.
  plantaia_linea_inf(&inf_ult, empujar ? "[INF]" : "[CON]", linea, sizeof(linea));
  Serial.println(linea);
}

// ─── LCD ──────────────────────────────────────────────────────────────────
// Línea 0: la predicción del modelo ('*' al final = warm-up, < 1 h de historia).
// Línea 1: alterna cada refresco entre suelo + estado de la nube y T/H.
void actualizar_lcd() {
  // Mientras se muestra la observación manual recién marcada, no pisarla.
  if (msg_obs && millis() - t_msg_obs < MOSTRAR_OBS_MS) return;
  msg_obs = false;

  char l0[17], l1[17], tmp[17];
  if (!hay_inf)          snprintf(tmp, sizeof(tmp), "Pred:---");
  else if (!inf_ult.ok)  snprintf(tmp, sizeof(tmp), "Pred:sin datos");
  else                   snprintf(tmp, sizeof(tmp), "Pred:%s%s", plantaia_etiqueta(inf_ult.clase),
                                  inf_ult.warmup ? "*" : "");
  snprintf(l0, sizeof(l0), "%-16s", tmp);

  if (lcd_pagina) {
    if (s.dht_ok) snprintf(tmp, sizeof(tmp), "T:%.1fC H:%.0f%%", s.temp_dht, s.hum_aire);
    else          snprintf(tmp, sizeof(tmp), "T:--- H:---");
  } else {
    snprintf(tmp, sizeof(tmp), "S:%.0fmv %-6s", s.suelo_mv, estado_nube.c_str());
  }
  snprintf(l1, sizeof(l1), "%-16s", tmp);
  lcd_pagina = !lcd_pagina;

  lcd.setCursor(0, 0); lcd.print(l0);
  lcd.setCursor(0, 1); lcd.print(l1);
}

// Muestra la condición manual recién elegida con el botón (no toca el semáforo).
void mostrar_obs_manual() {
  char l1[17];
  snprintf(l1, sizeof(l1), "%-16s", ETIQUETAS[condicion]);
  lcd.setCursor(0, 0); lcd.print("Obs manual:     ");
  lcd.setCursor(0, 1); lcd.print(l1);
  t_msg_obs = millis();
  msg_obs   = true;
}

// ─── WiFi ─────────────────────────────────────────────────────────────────
// Un intento contra una red, con el mismo timeout para cada una.
bool intentar_red(const char* ssid, const char* pass) {
  WiFi.begin(ssid, pass);
  Serial.printf("WiFi %s", ssid);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis()-t0 < TIMEOUT_WIFI) {
    delay(500); Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.disconnect(false);  // corta el intento antes de probar la siguiente red
  return false;
}

bool conectar_wifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.mode(WIFI_STA);
  // La placa se mueve entre la red de la casa y el hotspot del celular: se
  // prueban las dos en orden. WIFI_SSID_2 es opcional en secrets.h.
  bool ok = intentar_red(WIFI_SSID, WIFI_PASSWORD);
#ifdef WIFI_SSID_2
  if (!ok) ok = intentar_red(WIFI_SSID_2, WIFI_PASSWORD_2);
#endif
  if (ok) {
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");   // UTC — ver nota de Hora
    Serial.println("IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("Sin WiFi");
  }
  return ok;
}

// ─── HTTPS → Railway ──────────────────────────────────────────────────────
bool enviar() {
  if (!conectar_wifi()) { estado_nube = "NoWiFi"; return false; }

  WiFiClientSecure client;
  client.setInsecure();   // Railway usa TLS válido; para mayor seguridad cargar CA raíz
  // El handshake TLS por defecto espera hasta 120 s: con la red mala eso frena
  // el loop (botón y LCD) mucho más que los 15 s del resto del POST.
  client.setHandshakeTimeout(15);   // en segundos
  HTTPClient http;
  http.begin(client, API_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  http.setTimeout(15000);

  JsonDocument doc;
  doc["dispositivo"]       = "maceta-01";
  doc["numero_muestra"]    = n_muestra;
  doc["boot_id"]           = boot_id;
  doc["firmware_version"]  = FW_VERSION;

  // Hora de la placa: sin esto no se puede cruzar con el timelapse del celular
  // ni detectar el retardo de red. Va en unix epoch UTC.
  if (hora_valida()) doc["ts_dispositivo_unix"] = (uint32_t)time(nullptr);
  else               doc["ts_dispositivo_unix"] = nullptr;

  if (s.dht_ok) {
    doc["temperatura_c"]        = roundf(s.temp_dht * 10) / 10.0f;
    doc["humedad_ambiente_pct"] = roundf(s.hum_aire);
  } else {
    doc["temperatura_c"]        = nullptr;
    doc["humedad_ambiente_pct"] = nullptr;
  }

  // Crudo + convertido para cada canal analógico (CLAUDE.md: guardar siempre los dos)
  doc["luz_raw"]   = s.luz_raw;
  doc["luz_mv"]    = (int)s.luz_mv;
  doc["luz_pct"]   = (int)s.luz_pct;
  doc["suelo_raw"] = s.suelo_raw;
  doc["suelo_mv"]  = (int)s.suelo_mv;
  // suelo_pct no se manda: sin calibrar sería un valor inventado (ver leer_sensores).
  if (s.ntc_ok) {
    doc["termistor_raw"] = s.ntc_raw;
    doc["termistor_mv"]  = (int)s.ntc_mv;
    doc["temp_ntc_c"]    = roundf(s.temp_ntc * 10) / 10.0f;
  } else {
    doc["termistor_raw"] = s.ntc_raw;          // el crudo sirve para diagnosticar
    doc["termistor_mv"]  = (int)s.ntc_mv;
    doc["temp_ntc_c"]    = nullptr;            // celda vacía, nunca 0
  }

  doc["condicion_codigo"]   = condicion;
  doc["condicion_etiqueta"] = ETIQUETAS[condicion];
  doc["etiqueta_origen"]    = etiqueta_nueva ? "manual" : "propagada";
  doc["wifi_rssi"] = WiFi.RSSI();

  // Salida del modelo que corre en la placa (Tarea 2). El backend por ahora la
  // ignora (MedicionIn no la declara y pydantic descarta lo que sobra);
  // persistirla es una mejora pendiente — ver docs/ENTREGA2.md §1.
  bool pred_ok = hay_inf && inf_ult.ok;
  if (pred_ok) {
    doc["prediccion_codigo"]   = inf_ult.clase;
    doc["prediccion_etiqueta"] = plantaia_etiqueta(inf_ult.clase);
    doc["prediccion_proba"]    = roundf(inf_ult.proba[inf_ult.clase - 1] * 1000) / 1000.0f;
  } else {
    doc["prediccion_codigo"]   = nullptr;   // sin predicción: null, nunca 0
    doc["prediccion_etiqueta"] = nullptr;
    doc["prediccion_proba"]    = nullptr;
  }
  doc["modelo_version"] = plantaia_modelo_version();

  // Diagnóstico real: si un sensor falló hay que poder saber por qué, no solo
  // encontrar la celda vacía dos semanas después.
  JsonArray errores = doc["errores"].to<JsonArray>();
  if (!s.dht_ok)      errores.add("dht_sin_respuesta");
  if (!s.ntc_ok)      errores.add("ntc_fuera_de_rango");
  if (!hora_valida()) errores.add("hora_sin_sincronizar");
  // Detecta saturación contra los rieles del ADC (no detecta desconexión: un pin
  // flotante del ESP32 lee ruido, no cero).
  if (s.luz_raw   <= 0 || s.luz_raw   >= 4095) errores.add("luz_saturada");
  if (s.suelo_raw <= 0 || s.suelo_raw >= 4095) errores.add("suelo_saturado");
  if (!pred_ok)       errores.add("sin_prediccion");

  String body;
  serializeJson(doc, body);
  Serial.println("POST " + String(API_URL));
  Serial.println(body);

  int code = http.POST(body);
  http.end();

  if (code == 201 || code == 200) {
    if (code == 201) {
      estado_nube = "OK#" + String(n_muestra);
      Serial.println("201 guardado");
    } else {
      estado_nube = "DUP";
      Serial.println("200 duplicado — avanzando contador");
    }
    prefs.putUInt("n_muestra", ++n_muestra);
    etiqueta_nueva = false;   // la observación manual ya quedó registrada
    return true;
  }
  // 401 token malo | 422 JSON inválido | 5xx error servidor
  estado_nube = "E" + String(code > 0 ? code : -1);
  Serial.printf("HTTP error: %d\n", code);
  return false;
}

// ─── Botón ────────────────────────────────────────────────────────────────
void manejar_boton() {
  bool presionado  = digitalRead(PIN_BOTON) == LOW;
  unsigned long ms = millis();

  if (presionado && !boton_prev) {
    t_boton_down = ms;
  } else if (!presionado && boton_prev) {
    unsigned long dur = ms - t_boton_down;
    if (dur >= DEBOUNCE_MS && dur < PULSACION_LARGA) {
      condicion      = (condicion + 1) % N_COND;
      etiqueta_nueva = true;
      // Persistido: sin esto, cualquier corte de luz devolvía la etiqueta a
      // sin_etiquetar en silencio.
      prefs.putInt("condicion", condicion);
      Serial.printf("Cond → %s (manual)\n", ETIQUETAS[condicion]);
      // Desde 2.0.0 el semáforo es la salida del modelo: la observación manual
      // sólo se muestra en el LCD un momento y viaja en el próximo POST.
      mostrar_obs_manual();
    } else if (dur >= PULSACION_LARGA) {
      Serial.println("Envio forzado por boton");
      forzar_envio = true;
    }
  }
  boton_prev = presionado;
}

// ─── Setup ────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== PlantaIa boot — fw " FW_VERSION " ===");

  pinMode(PIN_LED_VERDE,    OUTPUT);
  pinMode(PIN_LED_AMARILLO, OUTPUT);
  pinMode(PIN_LED_ROJO,     OUTPUT);
  pinMode(PIN_SUELO_VCC,    OUTPUT);
  digitalWrite(PIN_SUELO_VCC, LOW);
  pinMode(PIN_BOTON, INPUT_PULLUP);

  dht.begin();

  Wire.begin(21, 22);
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.print("PlantaIa...");

  prefs.begin("maceta", false);
  n_muestra = prefs.getUInt("n_muestra", 0);
  boot_id   = prefs.getUInt("boot_id",   0) + 1;
  condicion = prefs.getInt("condicion",  0);   // sobrevive a los reinicios
  if (condicion < 0 || condicion >= N_COND) condicion = 0;   // NVS corrupta → índice fuera de ETIQUETAS
  prefs.putUInt("boot_id", boot_id);
  Serial.printf("boot_id=%u  n_muestra=%u  condicion=%s\n",
                boot_id, n_muestra, ETIQUETAS[condicion]);
  Serial.printf("modelo=%s  ventana=%d muestras x 5 min\n",
                plantaia_modelo_version(), FEAT_VENTANA);

  // Ventana de features vacía: arranca en warm-up (1 h hasta tener delta).
  features_reset(&buf_feat);

  // Prueba de lámparas: los tres LEDs medio segundo. Después quedan apagados
  // hasta la primera predicción, así "apagado" no se confunde con placa muerta.
  digitalWrite(PIN_LED_VERDE, HIGH); digitalWrite(PIN_LED_AMARILLO, HIGH); digitalWrite(PIN_LED_ROJO, HIGH);
  delay(500);
  actualizar_semaforo();

  lcd.clear();
  lcd.print("Conectando WiFi");
  bool ok = conectar_wifi();
  lcd.clear();
  lcd.print(ok ? "WiFi OK" : "Sin WiFi");
  delay(1500);
  lcd.clear();
}

// ─── Loop ─────────────────────────────────────────────────────────────────
void loop() {
  unsigned long ahora = millis();
  manejar_boton();

  // Tick de 5 min (y el primero, apenas arranca): leer → buffer → features →
  // predecir → LED → LCD → log → POST. Va ANTES del refresco del LCD para no
  // leer el DHT11 dos veces seguidas en la misma vuelta.
  //
  // Envío forzado (pulsación larga): lee, predice en modo CONSULTA (la ventana
  // no avanza) y manda. NO reinicia t_envio: la ventana de 1 h tiene que avanzar
  // sólo con los ticks de 5 min, si no "12 muestras atrás" dejaría de ser
  // "60 min atrás" y las features no serían las del entrenamiento.
  bool tick = primer_tick || (ahora - t_envio >= INTERVALO_ENVIO);
  if (tick || forzar_envio) {
    if (tick) { t_envio = ahora; primer_tick = false; }
    forzar_envio = false;
    leer_sensores();
    inferir(tick);
    actualizar_lcd();       // la predicción nueva al LCD ANTES del POST, que puede tardar
    t_lectura = millis();   // la lectura recién hecha cuenta como refresco
    bool ok = enviar();

    char buf[17];
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(ok ? "Enviado OK      " : "Error envio     ");
    lcd.setCursor(0, 1);
    snprintf(buf, sizeof(buf), "n=%u boot=%u", n_muestra, boot_id);
    lcd.print(buf);
    delay(2000);   // PENDIENTE: pasar a máquina de estados, bloquea el botón
    lcd.clear();
    actualizar_lcd();
  }

  // millis() de nuevo y no `ahora`: si hubo tick, t_lectura quedó DESPUÉS de
  // `ahora` y la resta sin signo daría la vuelta (lectura extra inmediata).
  unsigned long ahora_lcd = millis();
  if (ahora_lcd - t_lectura >= INTERVALO_LECTURA) {
    t_lectura = ahora_lcd;
    leer_sensores();
    actualizar_lcd();
    Serial.printf("[%lu] T:%.1f H:%.0f Luz:%.0f%% Suelo(raw:%d mv:%.0f) Termistor(raw:%d mv:%.0f %.1fC) Cond:%s Pred:%s\n",
      ahora_lcd/1000, s.temp_dht, s.hum_aire, s.luz_pct, s.suelo_raw, s.suelo_mv,
      s.ntc_raw, s.ntc_mv, s.temp_ntc, ETIQUETAS[condicion],
      plantaia_etiqueta(hay_inf ? inf_ult.clase : 0));
  }
}
