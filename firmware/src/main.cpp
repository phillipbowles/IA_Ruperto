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

// Versión del firmware: viaja en cada muestra para poder separar en el análisis
// los datos tomados antes y después de un cambio de calibración o de lógica.
#define FW_VERSION "1.1.0"

// ─── Pines (fijo, ver CLAUDE.md — no cambiar) ─────────────────────────────
#define PIN_LUZ          34
#define PIN_TERMISTOR    35
#define PIN_SUELO_AO     32
#define PIN_SUELO_VCC    33
#define PIN_DHT           4
#define PIN_LED_VERDE    27
#define PIN_LED_AMARILLO 26
#define PIN_LED_ROJO     25
#define PIN_BOTON        13

// ─── Parámetros generales ──────────────────────────────────────────────────
#define DHT_TYPE           DHT11
#define LCD_ADDR           0x27
#define LCD_COLS           16
#define LCD_ROWS            2
#define INTERVALO_LECTURA  2000UL          // 2 s — actualizar LCD/Serial
#define INTERVALO_ENVIO   30000UL          // 30 s pruebas → 300000 producción
#define TIMEOUT_WIFI      15000UL
#define DEBOUNCE_MS          50UL
#define PULSACION_LARGA    2000UL

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
#define NTC_R_FIJO  10000.0f
#define NTC_R0      10000.0f
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
  int   suelo_raw;  float suelo_mv, suelo_pct;
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

  // NTC — GPIO35
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
  s.suelo_pct = constrain(
    (int)map((long)suelo.mv, SUELO_MV_MOJADO, SUELO_MV_SECO, 100, 0), 0, 100);
}

// ─── Semáforo ─────────────────────────────────────────────────────────────
void actualizar_semaforo() {
  digitalWrite(PIN_LED_VERDE,    condicion == 1);
  digitalWrite(PIN_LED_AMARILLO, condicion == 2);
  digitalWrite(PIN_LED_ROJO,     condicion == 3 || condicion == 0);
}

// ─── LCD ──────────────────────────────────────────────────────────────────
void actualizar_lcd() {
  char l0[17], l1[17];
  if (s.dht_ok)
    snprintf(l0, sizeof(l0), "T:%.1fC H:%.0f%%", s.temp_dht, s.hum_aire);
  else
    snprintf(l0, sizeof(l0), "T:--- H:---     ");
  snprintf(l1, sizeof(l1), "S:%.0f%% %-7s", s.suelo_pct, estado_nube.c_str());

  lcd.setCursor(0, 0); lcd.print(l0);
  lcd.setCursor(0, 1); lcd.print(l1);
}

// ─── WiFi ─────────────────────────────────────────────────────────────────
bool conectar_wifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("WiFi");
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis()-t0 < TIMEOUT_WIFI) {
    delay(500); Serial.print(".");
  }
  Serial.println();
  bool ok = WiFi.status() == WL_CONNECTED;
  if (ok) {
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");   // UTC — ver nota de Hora
    Serial.println("IP: " + WiFi.localIP().toString());
  } else {
    WiFi.disconnect(false);  // detiene intento activo sin crashear al reconectar
    Serial.println("Sin WiFi");
  }
  return ok;
}

// ─── HTTPS → Railway ──────────────────────────────────────────────────────
bool enviar() {
  if (!conectar_wifi()) { estado_nube = "NoWiFi"; return false; }

  WiFiClientSecure client;
  client.setInsecure();   // Railway usa TLS válido; para mayor seguridad cargar CA raíz
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
  doc["suelo_pct"] = (int)s.suelo_pct;
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
      // sin_etiquetar en silencio y el semáforo quedaba en rojo hasta que
      // alguien pasara por la maceta.
      prefs.putInt("condicion", condicion);
      Serial.printf("Cond → %s (manual)\n", ETIQUETAS[condicion]);
      actualizar_semaforo();
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
  prefs.putUInt("boot_id", boot_id);
  Serial.printf("boot_id=%u  n_muestra=%u  condicion=%s\n",
                boot_id, n_muestra, ETIQUETAS[condicion]);

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

  if (ahora - t_lectura >= INTERVALO_LECTURA) {
    t_lectura = ahora;
    leer_sensores();
    actualizar_lcd();
    Serial.printf("[%lu] T:%.1f H:%.0f Luz:%.0f%% Suelo:%.0f%% Cond:%s\n",
      ahora/1000, s.temp_dht, s.hum_aire, s.luz_pct, s.suelo_pct, ETIQUETAS[condicion]);
  }

  if (ahora - t_envio >= INTERVALO_ENVIO || forzar_envio) {
    forzar_envio = false;
    t_envio      = ahora;
    leer_sensores();
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
}
