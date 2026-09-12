# PlantaIa — maceta inteligente (Tarea 1, curso de IA)

Una ESP32 muestrea sensores cada 5 min sobre un lirio de paz y los manda a un
backend propio. Con esos datos se entrena un clasificador de 3 clases
(turgente / marchitez transitoria / marchitez franca).

> **Este archivo es la única fuente de verdad** para pines, etiquetas y esquema
> de datos. Si algún otro documento contradice esto, el otro documento está mal.
> El detalle de la arquitectura está en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

## Estructura del repo

```
firmware/   ESP32 (PlatformIO)      backend/   API FastAPI + Alembic (Docker)
frontend/   React + Vite (Docker)   notebooks/ EDA y entrenamiento
docs/       decisiones y calibración
```

Cada servicio corre en su contenedor. Para levantar todo en local:

```bash
cp .env.example .env          # completar DEVICE_TOKEN
docker compose up --build     # db + backend + frontend
```

Backend en `:8000` (Swagger en `/docs`), front en `:5173`, Postgres en `:5432`.
`docker compose down -v` para además borrar los datos.

**El esquema de la base se cambia solo por migración de Alembic.** El entrypoint
del contenedor corre `alembic upgrade head` antes de levantar el servidor, así
que se aplican solas. `create_all()` no existe más: dos mecanismos creando
tablas terminan con el esquema de local y el de producción separados sin que
nadie se entere. Después de tocar `app/models.py`:

```bash
docker compose exec backend alembic revision --autogenerate -m "descripcion"
docker compose exec backend alembic check    # ¿quedó algo sin migrar?
```

## Placa y toolchain

ESP32 DevKit clásico (micro-USB, CP2102 o CH340). Se compila con **PlatformIO**,
con las versiones de librerías fijadas en `firmware/platformio.ini`.

```bash
cd firmware
pio run                      # compilar
pio run -t upload            # subir
pio device monitor           # 115200
```

El puerto se autodetecta; si hay más de una placa, fijarlo en `platformio.ini`.
La placa va enchufada a un cargador de pared, no a la notebook.

## Mapa de pines (fijo, no cambiar)

Verificado contra el cableado físico real el 2026-09-12 (por tacto: se
identificó cuál sensor cambia al humedecerlo/calentarlo con el dedo mirando
el Serial en vivo). Corrige una versión anterior que tenía temperatura y
suelo cruzados entre GPIO32/35, y el botón en 13 en vez de 19.

| Señal | GPIO | Notas |
|---|---|---|
| Luz (LDR Keyestudio KS0028) | 34 | analógico, ADC1, solo entrada |
| Temperatura (termistor KS0033) | 32 | analógico, ADC1 |
| Humedad de suelo — señal | 35 | analógico, ADC1, solo entrada |
| Humedad de suelo — VCC | 33 | alimentada por GPIO **solo durante la lectura** |
| DHT11 | 4 | humedad + temperatura del aire |
| LCD I2C (0x27) — SDA / SCL | 21 / 22 | lógica 3,3 V |
| LED semáforo **rojo** | 25 | con resistencia de 220–330 Ω |
| LED semáforo **amarillo** | 26 | idem |
| LED semáforo **verde** | 27 | idem |
| Botón | 19 | `INPUT_PULLUP`, a GND; marca observación manual |

## Restricciones duras

- Los módulos analógicos Keyestudio están documentados a 5 V, pero el ADC de la
  ESP32 solo tolera 3,3 V → **alimentarlos desde 3V3**, nunca desde 5 V.
- **ADC2 no funciona con WiFi activo** → todo lo analógico en ADC1 (GPIO 32–39).
- GPIO 34–39 son solo entrada: no tienen pull-up interno ni salida.
- **Nada de cámara en esta placa.** El ESP32 clásico no puede ser USB host y la
  OV2640 por DVP se lleva 13–16 GPIOs. El timelapse lo hace un celular aparte;
  los dos loggers son independientes y se cruzan después por timestamp.

## La sonda de suelo es RESISTIVA

Es el punto débil conocido del montaje y condiciona varias decisiones:

- Se alimenta por GPIO 33 **solo mientras se mide**, para limitar la electrólisis.
- El tiempo de estabilización es de 100 ms y **no hay que subirlo**: el divisor
  se asienta en microsegundos, y mientras haya tensión aplicada la lectura deriva
  hacia abajo por migración de iones. Lo que importa es que sea siempre el mismo.
- Seco = alta resistencia = tensión alta. Por eso `SUELO_MV_SECO > SUELO_MV_MOJADO`.
- **Los electrodos se corroen y la calibración se corre a lo largo de semanas.**
  Como la condición de la planta también progresa con el tiempo, la deriva del
  sensor puede producir correlación espuria. Mitigación obligatoria: medir el
  par seco/mojado de referencia una vez por semana y anotarlo en
  [docs/CALIBRACION.md](docs/CALIBRACION.md) para poder corregir a posteriori.

## Convenciones del firmware

- Muestreo cada 5 min en régimen normal; 1 min en las ventanas de recuperación
  (miércoles post-riego, 6 h) y en la prueba de fuego.
- Cada lectura analógica es la **mediana de 9 muestras**, con
  `analogReadMilliVolts()` — no `analogRead()` crudo a secas.
- Guardar **siempre el valor crudo además del convertido** (`*_raw` y `*_mv`
  viajan en cada muestra junto al valor en unidades físicas).
- Si un sensor falla, el campo va en **null**, nunca en 0, y el motivo se suma
  al array `errores`.
- La hora se sincroniza por **NTP en UTC** y viaja como unix epoch
  (`ts_dispositivo_unix`). La conversión a hora local se hace en el front. Sin la
  hora de la placa no se puede cruzar con el timelapse del celular.
- `boot_id` nuevo en cada arranque y `condicion` persistida en Preferences, para
  que un corte de luz no borre la etiqueta en silencio.
- El semáforo refleja el último estado estimado; el botón registra una
  observación manual.

## Etiquetas — el target del clasificador

**Tres clases.** Los nombres del firmware son los canónicos; la columna de la
derecha es el vocabulario botánico que va en el informe:

| código | etiqueta | equivale a |
|---|---|---|
| 1 | `saludable` | turgente |
| 2 | `estresada` | marchitez transitoria |
| 3 | `marchita` | marchitez franca |

`sin_etiquetar` (código 0) **no es una clase**: es ausencia de etiqueta y se
**excluye del entrenamiento**. Nunca entra al `fit` como categoría.

`etiqueta_origen` distingue de dónde salió la etiqueta de cada fila:

- `manual` — la muestra en la que alguien apretó el botón y observó la planta.
- `propagada` — heredó la etiqueta de la última observación manual.
- `corregida` — reetiquetada a posteriori desde el front.

Esto no es cosmético: **las muestras contiguas comparten etiqueta y están
fuertemente correlacionadas.** Un split aleatorio da ~98 % de accuracy por puro
leakage. Hay que partir por **episodios de etiqueta** (`GroupKFold`), y el N
efectivo son los episodios, no las filas.

## Datos

El almacenamiento es **Postgres en Railway**, alimentado por HTTPS desde la
placa (`POST /api/v1/mediciones`, idempotente por `dispositivo + numero_muestra`).
LittleFS en la placa queda como **buffer de reenvío** para cuando se cae el WiFi,
no como almacenamiento principal.

El esquema se separa en cuatro tablas porque tienen ciclos de vida distintos
— hechos inmutables, anotaciones humanas corregibles, y salidas del modelo.
El detalle está en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

El CSV de análisis (`ts_iso, ts_unix, muestra_id, boot_id, luz_raw, luz_mv,
luz_nivel, temp_ntc_c, temp_dht_c, hum_aire_pct, suelo_raw, suelo_pct, etiqueta,
etiqueta_origen, evento, escena_luz, peso_g, foto, nota, flags`) **es una vista,
no una tabla**: sale del join de las cuatro en `GET /api/v1/dataset.csv`.

- `evento`: `riego` | `cambio_luz` | `lampara_on` | `lampara_off`
- `escena_luz`: `velo_abierto` | `velo_cerrado` | `pantalla` | `lampara`
- `peso_g`, `foto` y `nota` los carga Manuel desde el front en las observaciones.

## Secretos

`firmware/include/secrets.h` y `backend/.env` están en `.gitignore` y no se
suben nunca. Hay un `.example` de cada uno como plantilla.
