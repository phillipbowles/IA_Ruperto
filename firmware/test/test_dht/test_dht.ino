#include <DHT.h>

#define PIN_DHT  4
#define DHT_TYPE DHT11

DHT dht(PIN_DHT, DHT_TYPE);

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("=== Test DHT11 GPIO4 ===");
  dht.begin();
  delay(2000);  // DHT11 necesita 2 s para estabilizarse
}

void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  if (isnan(h) || isnan(t)) {
    Serial.println("ERROR: DHT11 no responde — revisar cableado");
  } else {
    Serial.printf("T: %.1f C   H: %.1f %%\n", t, h);
  }
  delay(2500);
}
