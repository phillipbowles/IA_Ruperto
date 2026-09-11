# PlantaIa — firmware del logger (Tarea 1, curso de IA)

Logger de una maceta inteligente: una ESP32 muestrea sensores cada 5 min y
guarda un CSV para entrenar un clasificador de 3 clases (turgente / marchitez
transitoria / marchitez franca) sobre un lirio de paz.

## Placa y toolchain

- ESP32 DevKit clásico (micro-USB = conversor USB-serie CP2102 o CH340).
- FQBN: `esp32:esp32:esp32` (si es DOIT DevKit V1: `esp32:esp32:esp32doit-devkit-v1`).
- Se edita acá y se compila/sube con arduino-cli desde esta carpeta:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 .
arduino-cli upload -p /dev/cu.usbserial-0001 --fqbn esp32:esp32:esp32 .
arduino-cli monitor -p /dev/cu.usbserial-0001 -c baudrate=115200
```

El puerto puede ser `/dev/cu.usbserial-*`, `/dev/cu.SLAB_USBtoUART` (CP2102) o
`/dev/cu.wchusbserial*` (CH340). Confirmar con `arduino-cli board list`.
La placa va enchufada a un cargador de pared, no a la notebook.

## Mapa de pines (fijo, no cambiar)

| Señal | GPIO | Notas |
|---|---|---|
| Luz (LDR Keyestudio KS0028) | 34 | analógico, ADC1, solo entrada |
| Temperatura (termistor KS0033) | 35 | analógico, ADC1, solo entrada |
| Humedad de suelo — señal | 32 | analógico, ADC1 |
| Humedad de suelo — VCC | 33 | alimentada por GPIO **solo durante la lectura** |
| DHT11 | 4 | humedad + temperatura del aire |
| LEDs semáforo | 25 / 26 / 27 | verde / amarillo / rojo |
| Botón | 13 | `INPUT_PULLUP`, marca observación manual |

## Restricciones duras

- Los módulos analógicos Keyestudio están documentados a 5 V, pero el ADC de la
  ESP32 solo tolera 3,3 V → **alimentarlos desde 3V3**, nunca desde 5 V.
- **ADC2 no funciona con WiFi activo** → todo lo analógico en ADC1 (GPIO 32–39).
- GPIO 34–39 son solo entrada: no tienen pull-up interno ni salida.
- **Nada de cámara en esta placa.** El ESP32 clásico no puede ser USB host y la
  OV2640 por DVP se lleva 13–16 GPIOs. El timelapse lo hace un celular aparte;
  los dos loggers son independientes y se cruzan después por timestamp.

## Convenciones del firmware

- Muestreo cada 5 min en régimen normal; 1 min en las ventanas de recuperación
  (miércoles post-riego, 6 h) y en la prueba de fuego.
- Cada lectura analógica es la **mediana de 9 muestras**, con
  `analogReadMilliVolts()` — no `analogRead()` crudo a secas.
- Guardar **siempre el valor crudo además del convertido**.
- Si un sensor falla, la celda va **vacía**, nunca 0.
- La sonda de suelo se alimenta por GPIO 33 solo mientras se lee, para que no se
  electrolice; esperar a que se estabilice antes de medir.
- Almacenamiento: **LittleFS en modo append** + hora por **NTP** + endpoint HTTP
  `/datos.csv` para bajar el archivo, y una página de estado con la hora de la
  placa a la vista (se le saca foto para chequear que los relojes coincidan).
- `boot_id` nuevo en cada arranque, para detectar reinicios en el análisis.
- El semáforo refleja el último estado estimado; el botón registra una
  observación manual (`etiqueta_origen = manual`).

## Esquema del CSV (el orden importa)

```
ts_iso, ts_unix, muestra_id, boot_id, luz_raw, luz_mv, luz_nivel, temp_ntc_c,
temp_dht_c, hum_aire_pct, suelo_raw, suelo_pct, etiqueta, etiqueta_origen,
evento, escena_luz, peso_g, foto, nota, flags
```

- `etiqueta_origen`: `manual` | `propagada` | `corregida`
- `evento`: `riego` | `cambio_luz` | `lampara_on` | `lampara_off`
- `escena_luz`: `velo_abierto` | `velo_cerrado` | `pantalla` | `lampara`
- `peso_g`, `foto` y `nota` los completa Manuel a mano en las observaciones.
