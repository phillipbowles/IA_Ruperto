# ESP32-CAM

Firmware independiente para la placa AI-Thinker ESP32-CAM. Toma una foto al
arrancar y luego cada 5 minutos, busca cualquiera de dos redes Wi-Fi conocidas
y sube el JPEG al backend de Railway.

## Preparacion

```bash
cd firmware/camera
cp include/secrets.example.h include/secrets.h
# completar include/secrets.h
pio run
```

Para cargar con un USB-TTL: 5V a 5V, GND a GND, TX a U0R, RX a U0T y GPIO0 a
GND solo durante la carga. Despues de `pio run -t upload`, quitar GPIO0 de GND y
reiniciar. Monitor serie: `pio device monitor` a 115200.

Usar una fuente de 5V estable de al menos 1A. Una fuente debil suele producir
reinicios o fotos corruptas cuando se activan Wi-Fi y camara a la vez.
