#include "esp_camera.h"
#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "secrets.h"

// Pinout AI-Thinker ESP32-CAM + OV2640.
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22
#define FLASH_LED_GPIO_NUM 4

constexpr unsigned long INTERVALO_FOTO_MS = 5UL * 60UL * 1000UL;
constexpr unsigned long REINTENTO_FOTO_MS = 30UL * 1000UL;
constexpr unsigned long REINTENTO_WIFI_MS = 30UL * 1000UL;
constexpr unsigned long TIMEOUT_WIFI_MS = 20UL * 1000UL;

struct CredencialWifi {
  const char *ssid;
  const char *password;
};

const CredencialWifi REDES[] = {
    {WIFI_SSID_1, WIFI_PASSWORD_1},
    {WIFI_SSID_2, WIFI_PASSWORD_2},
};
constexpr size_t CANTIDAD_REDES = sizeof(REDES) / sizeof(REDES[0]);

Preferences preferencias;
uint64_t proximaFoto = 0;
unsigned long ultimoIntentoWifiMs = 0;
unsigned long ultimoIntentoFotoMs = 0;
unsigned long ultimaFotoExitosaMs = 0;
bool fotoPendiente = true;
bool yaIntentoFoto = false;

bool iniciarCamara() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;

  if (psramFound()) {
    config.frame_size = FRAMESIZE_XGA;  // 1024 x 768
    config.jpeg_quality = 12;
    config.fb_count = 2;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    config.frame_size = FRAMESIZE_VGA;  // 640 x 480
    config.jpeg_quality = 15;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  const esp_err_t resultado = esp_camera_init(&config);
  if (resultado != ESP_OK) {
    Serial.printf("Error iniciando camara: 0x%x\n", resultado);
    return false;
  }
  return true;
}

bool conectarA(const CredencialWifi &red) {
  Serial.printf("Conectando a %s", red.ssid);
  WiFi.begin(red.ssid, red.password);
  const unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < TIMEOUT_WIFI_MS) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.disconnect(true);
    delay(250);
    return false;
  }
  Serial.printf("Wi-Fi conectado | IP: %s | RSSI: %d dBm\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());
  return true;
}

bool conectarWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;

  WiFi.disconnect(true);
  delay(250);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);

  Serial.println("Buscando redes conocidas...");
  const int encontradas = WiFi.scanNetworks(false, true);
  int rssi[CANTIDAD_REDES];
  for (size_t i = 0; i < CANTIDAD_REDES; ++i) rssi[i] = -1000;

  for (int i = 0; i < encontradas; ++i) {
    for (size_t conocida = 0; conocida < CANTIDAD_REDES; ++conocida) {
      if (WiFi.SSID(i) == REDES[conocida].ssid) rssi[conocida] = WiFi.RSSI(i);
    }
  }
  WiFi.scanDelete();

  // Prueba primero la conocida con mejor senal y, si falla, prueba la otra.
  for (size_t intento = 0; intento < CANTIDAD_REDES; ++intento) {
    int mejor = -1;
    for (size_t i = 0; i < CANTIDAD_REDES; ++i) {
      if (rssi[i] > -1000 && (mejor < 0 || rssi[i] > rssi[mejor])) mejor = i;
    }
    if (mejor < 0) break;
    const int valorRssi = rssi[mejor];
    rssi[mejor] = -1000;
    Serial.printf("Red conocida encontrada (%d dBm). ", valorRssi);
    if (conectarA(REDES[mejor])) return true;
  }

  Serial.println("No se pudo conectar a ninguna red conocida");
  return false;
}

camera_fb_t *capturarFoto() {
  // Descarta un cuadro para estabilizar la exposicion tras varios minutos.
  camera_fb_t *previo = esp_camera_fb_get();
  if (previo != nullptr) esp_camera_fb_return(previo);
  delay(150);
  return esp_camera_fb_get();
}

bool subirFoto(camera_fb_t *foto, uint64_t numero) {
  if (foto == nullptr || foto->format != PIXFORMAT_JPEG) return false;

  char numeroTexto[24];
  snprintf(numeroTexto, sizeof(numeroTexto), "%llu",
           static_cast<unsigned long long>(numero));
  String url = String(API_URL) + "?dispositivo=" + DEVICE_ID +
               "&numero_foto=" + numeroTexto +
               "&wifi_rssi=" + String(WiFi.RSSI());

  WiFiClientSecure cliente;
  // HTTPS cifra el trafico. Para este prototipo academico se omite la
  // validacion de CA; las credenciales del Bucket nunca entran en la placa.
  cliente.setInsecure();

  HTTPClient http;
  http.setConnectTimeout(15000);
  http.setTimeout(30000);
  http.setFollowRedirects(HTTPC_FORCE_FOLLOW_REDIRECTS);
  if (!http.begin(cliente, url)) return false;

  http.addHeader("Content-Type", "image/jpeg");
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  http.addHeader("Connection", "close");

  Serial.printf("Subiendo foto %s (%u bytes)...\n", numeroTexto, foto->len);
  const int codigo = http.POST(foto->buf, foto->len);
  const String respuesta = codigo > 0 ? http.getString() : HTTPClient::errorToString(codigo);
  http.end();
  Serial.printf("HTTP %d: %s\n", codigo, respuesta.c_str());
  return codigo == 200 || codigo == 201;
}

bool capturarYSubir() {
  if (!conectarWifi()) return false;
  camera_fb_t *foto = capturarFoto();
  if (foto == nullptr) {
    Serial.println("No se pudo capturar la foto");
    return false;
  }

  const bool ok = subirFoto(foto, proximaFoto);
  esp_camera_fb_return(foto);
  if (!ok) return false;

  ++proximaFoto;
  preferencias.putULong64("next_photo", proximaFoto);
  Serial.println("Foto guardada correctamente");
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\nESP32-CAM iniciando...");
  pinMode(FLASH_LED_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_LED_GPIO_NUM, LOW);

  preferencias.begin("esp32cam", false);
  proximaFoto = preferencias.getULong64("next_photo", 0);

  if (!iniciarCamara()) {
    Serial.println("La camara no inicio; reinicio en 10 segundos");
    delay(10000);
    ESP.restart();
  }
}

void loop() {
  const unsigned long ahora = millis();

  if (WiFi.status() != WL_CONNECTED && ahora - ultimoIntentoWifiMs >= REINTENTO_WIFI_MS) {
    ultimoIntentoWifiMs = ahora;
    conectarWifi();
  }

  const bool tocaIntentar = !yaIntentoFoto ||
      (fotoPendiente && ahora - ultimoIntentoFotoMs >= REINTENTO_FOTO_MS) ||
      (!fotoPendiente && ahora - ultimaFotoExitosaMs >= INTERVALO_FOTO_MS);

  if (tocaIntentar) {
    yaIntentoFoto = true;
    ultimoIntentoFotoMs = ahora;
    fotoPendiente = !capturarYSubir();
    if (!fotoPendiente) ultimaFotoExitosaMs = millis();
  }

  delay(100);
}
