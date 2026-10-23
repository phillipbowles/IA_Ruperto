# plantaia_ml — inferencia en la ESP32

Lógica del clasificador que corre **en la placa** (Tarea 2): buffer de 1 h,
cálculo de features, modelo exportado y formato del log. Es C++ puro, **sin
`Arduino.h`**: el mismo código compila en la ESP32 (`pio run -e esp32dev`) y en
la computadora (`pio test -e native`), que es donde se prueba. El contrato que
manda (nombres, orden, unidades) es [docs/ENTREGA2.md](../../../docs/ENTREGA2.md) §4 y §5.

| archivo | qué hace |
|---|---|
| `features.h/.cpp` | `BufferFeatures` (ventana circular de 13 muestras) y las 7 features |
| `modelo_plantaia.h` | el modelo: `plantaia_predecir()`. **GENERADO** por `ml/plantaia_ml/exportar_c.py`: no se edita a mano |
| `inferencia.h/.cpp` | un paso completo (features → modelo → cronómetro) y las líneas de log `[INF]`/`[FAL]` |

## 1. Ciclo en la placa

Cada **5 min** (`INTERVALO_ENVIO` en `src/main.cpp`), y también en la primera
vuelta del `loop()` tras el arranque:

```
leer_sensores()           mediana de 9 con analogReadMilliVolts, DHT11 con 3 reintentos
  → muestra_cruda()       faltante = NAN (nunca 0); sonda de suelo saturada = NAN
  → plantaia_inferir()    empuja al buffer, arma x[7], llama a plantaia_predecir()
                          y mide su duración con micros()
  → actualizar_semaforo() verde 27 = saludable, amarillo 26 = estresada, rojo 25 = marchita
  → Serial                [FAL] (si hubo faltantes) + [INF]
  → enviar()              POST con prediccion_* y modelo_version
  → LCD                   "Pred:estresada" ('*' al final = warm-up)
```

La inferencia **no depende del WiFi**: se hace antes del POST, así que si el
envío falla (o no hay red) el LED igual se actualiza.

**Sin predicción → los tres LEDs apagados.** Pasa sólo si el vector no se puede
armar (antes de la primera muestra válida, o si el DHT11 no respondió nunca
desde el arranque: la HR no tiene reemplazo). No se usa rojo parpadeando porque
el rojo significa `marchita` y un rojo por falta de datos haría regar una planta
que puede estar bien. Para no confundir "apagado" con "placa muerta", el
arranque hace una prueba de lámparas (los tres 0,5 s) y el LCD dice
`Pred:sin datos`; el POST lleva `prediccion_*` en null y `sin_prediccion` en
`errores`.

**El botón ya no maneja el semáforo.** Pulsación corta: cicla `condicion`
(observación manual, persistida en Preferences, viaja en el POST como siempre)
y la muestra 3 s en el LCD. Pulsación larga (≥ 2 s): **envío forzado**.

### Envío forzado: consulta, no tick

El envío forzado lee, predice y manda, pero **no empuja la muestra a la ventana
ni reinicia el reloj de 5 min**. Usa `features_consultar()`, que arma el vector
"como si" la muestra entrara, sobre una copia del buffer. Motivo: las features
asumen que 12 muestras atrás son 60 min atrás (`suelo_delta_1h`,
`luz_media_1h`). Una muestra extra fuera de cadencia, o reiniciar el tick,
haría que la ventana cubra otro intervalo de tiempo que el del entrenamiento.
Así el LED responde al instante (útil para la demo: mojar la sonda y
pulsación larga) y la serie de 5 min queda intacta. En el log esa línea sale
con prefijo `[CON]` en lugar de `[INF]`, para que el parser de la serie regular
no la cuente.

## 2. Buffer y features (contrato §4)

Ventana circular de **13 muestras** (la actual + 12 anteriores = 1 h a 5 min).
Sólo guarda `suelo_mv` y `luz_mv`; de T y HR alcanza con el último válido.

| idx | feature | cálculo en `features_empujar()` |
|---|---|---|
| 0 | `suelo_mv` | la muestra actual (o la anterior repetida si faltó) |
| 1 | `suelo_delta_1h` | `suelo[t] − suelo[t−12]`; **0 en warm-up** |
| 2 | `temp_c` | último T válido del DHT11 (el termistor **no** es respaldo) |
| 3 | `hum_aire_pct` | último HR válido del DHT11 |
| 4 | `vpd_kpa` | `0.6108·exp(17.27·T/(T+237.3))·(1 − HR/100)` con 2 y 3 |
| 5 | `luz_mv` | la muestra actual (o la anterior repetida) |
| 6 | `luz_media_1h` | media de las ≤ 13 muestras de la ventana, incluida la actual |

**Warm-up.** Mientras haya menos de 12 muestras *anteriores* a la actual (las
primeras 12 tras el arranque, ~55 min), `suelo_delta_1h = 0`, la media de luz
usa lo que haya y el log dice `warmup=1`. La inferencia corre igual. La ventana
vive en RAM: **un reinicio la vacía** y se vuelve a warm-up, coherente con el
Python, que corta los tramos por `boot_id`.

**Faltantes.**

- `suelo_mv` o `luz_mv` en NAN → se repite el valor anterior **dentro del
  buffer** (la repetición queda en la ventana) y se marca. Si es la primera
  muestra y no hay anterior, la muestra **no entra** a la ventana y no se infiere.
- En `main.cpp`, la sonda de suelo saturada contra un riel del ADC (`suelo_raw`
  0 ó 4095 = sonda fuera del sustrato) se pasa como NAN. La luz saturada **no**
  es faltante (es luz fuerte).
- DHT11 en NAN → último T / HR válidos. Si nunca hubo T o HR válidas desde
  el arranque, la muestra entra (suelo y luz) pero no se infiere: el termistor
  no es respaldo (contrato §4; su conversión en el fw 1.1.0 está invertida y
  sin DHT tampoco hay HR).
- Si no se infiere, `x` lleva NAN en lo que falta (todo NAN si la muestra ni
  siquiera entró a la ventana), igual que `features.py`; nunca 0.
- Cada faltante sale en una línea `[FAL]` antes del `[INF]`:
  `suelo_repetido`, `luz_repetida`, `dht_anterior`, `sin_suelo`,
  `sin_luz`, `sin_temp`, `sin_hum`.

## 3. Log

Una línea por tick, parseable (el formato lo arma `plantaia_linea_inf()`, que
usan igual la placa y el replay):

```
[INF] n=123 warmup=0 x=[1532,-41,20.6,47,1.29,871,850] -> estresada p=[0.10,0.78,0.12] t_us=37
```

- `n`: muestras empujadas a la ventana desde el arranque (no es `n_muestra`
  del POST, que sólo avanza si el servidor confirma).
- `x`: los 7 features en orden; mV y % sin decimales, T con 1, VPD con 2.
- `p`: probabilidades saludable/estresada/marchita.
- `t_us`: duración de `plantaia_predecir()` sola, medida con `micros()`.
- Sin predicción: `-> sin_prediccion p=[] t_us=0`.
- Envío forzado: mismo formato con `[CON]`.

## 4. Costo en memoria y CPU

Medido con `pio run -e esp32dev` (2026-10-23) con el modelo final
`arbol-p3-f03-ee3419`: árbol de decisión de profundidad 3
(`min_samples_leaf=20`) con `suelo_mv` y `hum_aire_pct`, entrenado con
los 24 episodios del snapshot del 23/10. Ver la restricción de diseño
y la condición de seguridad en `docs/entrega2/RESULTADOS.md`. El modelo
anterior (`arbol-p2-f012-58e644`, profundidad 2) daba 962 249 B de flash; el
que está flasheado en la placa desde el 22/10 es ése, y midió `t_us=33` en la
ESP32.

| | antes (fw 1.1.0) | después (fw 2.0.0 + `arbol-p3-f03-ee3419`) | diferencia |
|---|---|---|---|
| RAM estática | 47 548 B | 47 740 B (14,6 %) | **+192 B** |
| Flash | 957 897 B | 962 509 B (73,4 % de 1 310 720 B) | **+4 612 B** |

- **RAM estática.** `BufferFeatures` 124 B + `Inferencia` 56 B (+ alineación).
  Sin memoria dinámica. El modelo no suma RAM estática: sus tablas son
  `static const` y quedan en flash.
- **Stack en el tick.**
  - La copia del buffer en `features_consultar()`: 124 B, sólo en el envío
    forzado.
  - La línea de log: 200 B.
  - ~16 B de RAM del modelo durante la predicción (estimación de
    `costo_esp32`, `docs/entrega2/RESULTADOS.md`).
- **Flash del modelo: 81 B de tablas** en el header exportado (igual a la
  estimación de `costo_esp32` y a `exportar_c.bytes_parametros_c`), muy por
  debajo del presupuesto de 32 KB.
  - 5 nodos (2 internos y 3 hojas), profundidad 2: feature `int8`, umbral
    `float`, hijos `int16`.
  - 3 hojas × 3 probabilidades `float`.
  - El resto de la diferencia de flash es el código de la librería
    (`features.cpp`, `inferencia.cpp`), `expf` y el formateo de floats que
    trae libc.
- **CPU por tick.**
  - 13 sumas para la media de luz y un `expf` para el VPD (la placa arma
    siempre los 7 features, aunque el modelo use menos).
  - El modelo: un recorrido iterativo de **≤ 2 comparaciones** hasta la hoja
    y el argmax de 3 probabilidades (`costo_esp32` estima 4 operaciones,
    ~0,17 µs en la ESP32).
  - El presupuesto del contrato (§5.3) es **< 1 ms por inferencia** y
    **< 32 KB de flash** para el modelo.
- **Tiempo medido en el host, no en la placa**
  (`docs/entrega2/logs/replay_host.txt`, 150 inferencias):
  `t_us` de 0–1 µs (113 en 0 µs, 37 en 1 µs; máximo 1 µs).

  El número real de la ESP32 sale del log de la placa (`t_us` en cada
  `[INF]`), pendiente de flashear.

Si se cambia el modelo, actualizar esta tabla con la salida de `pio run`.

## 5. Cómo se reemplaza el modelo

`ml/plantaia_ml/exportar_c.py` sobrescribe **`modelo_plantaia.h`** (en esta
carpeta) y **`firmware/test/test_modelo/vectores.h`**. Nada más cambia: el
firmware y los tests sólo dependen de esta API.

```c
#define PLANTAIA_N_FEATURES 7            // siempre 7: la placa arma el vector completo
#define PLANTAIA_MODELO_VERSION "..."    // viaja en el POST como modelo_version
// Devuelve el código de clase 1..3; si proba != NULL escribe proba[0..2]
// en el orden saludable, estresada, marchita (suman 1).
int plantaia_predecir(const float x[PLANTAIA_N_FEATURES], float *proba);
```

Reglas para el header generado:

1. **Un único header autocontenido**, cabecera `GENERADO — no editar` con
   versión, orden de features y métricas. Sólo `<math.h>`/`<stddef.h>`/`<stdint.h>`;
   nada de `Arduino.h`.
2. **Todo `static` o `static inline`** (funciones y datos). Se incluye desde
   `inferencia.cpp` y desde `test_modelo.cpp`, que se linkean juntos en el host:
   sin `static` habría definiciones duplicadas.
3. Parámetros en arrays **`static const`** (en la ESP32 quedan en flash, no en
   RAM). Sin `malloc`/`new`, sin recursión.
4. La clase devuelta tiene que ser el **argmax de `proba`**, con empate a favor
   del código menor (como `numpy.argmax`). `test_modelo` lo verifica.
5. Si el modelo usa un subconjunto de features, el remapeo de índices va
   **adentro** de `plantaia_predecir`; la firma sigue recibiendo los 7.
6. Si hay estandarización (media/desvío), va adentro también.
7. Para no romper `inferencia.cpp`, `PLANTAIA_N_FEATURES` tiene que valer 7
   (hay un `#error` que lo controla). `PLANTAIA_N_CLASES` es opcional.

### Formato de `test/test_modelo/vectores.h` (paridad de clase)

```c
#pragma once
#define VEC_MODELO_VERSION "..."         // == PLANTAIA_MODELO_VERSION; si no, el test falla
static const float VEC_X[][7] = { {...}, ... };   // features en el orden del contrato
static const int   VEC_Y[]    = { 1, 3, ... };    // clase que da el modelo en Python
static const int   VEC_N      = (int)(sizeof(VEC_Y) / sizeof(VEC_Y[0]));
// Opcional: probabilidades de Python, se comparan con tolerancia 2e-3.
#define VEC_HAY_PROBA 1
static const float VEC_P[][3] = { {...}, ... };
```

`pio test -e native -f test_modelo` exige **100 %** de coincidencia de clase.
Si `vectores.h` no existe, el test de paridad se saltea (no falla). Conviene
que los vectores incluyan casos cerca de los umbrales del modelo (es donde
float32 vs float64 puede cambiar la clase) y escribir los floats con `%.9g`.

### Formato opcional de `test/test_features/paridad_features.h`

Para la paridad `features.py` ↔ C (§5.3). Si existe, `test_features` lo usa:

```c
#pragma once
#include <math.h>
// suelo_mv, luz_mv, temp_dht_c, hum_aire_pct, temp_ntc_c; NAN = faltante
static const float PAR_CRUDO[][5] = { {...}, ... };
static const int   PAR_RESET[]    = { 1, 0, ... };   // 1 = vaciar el buffer antes (boot_id/tramo nuevo)
static const int   PAR_OK[]       = { 1, 1, ... };   // 1 = hay vector (se puede inferir)
static const int   PAR_WARMUP[]   = { 1, 1, ... };
static const float PAR_X[][7]     = { {...}, ... };  // lo que da features.py (si PAR_OK = 0, cualquiera)
static const int   PAR_N          = ...;
```

Tolerancia por componente: `1e-4·|x| + 1e-3`.

## 6. Tests y replay en el host

```bash
cd firmware
pio test -e native                    # test_features, test_modelo, test_replay
pio test -e native -f test_features   # una sola suite
tools/correr_replay.sh                # replay → docs/entrega2/logs/replay_host.txt
```

- `test/test_features`: VPD contra valores calculados en Python, warm-up,
  rampa conocida, wrap del buffer (40 muestras = 3 vueltas), faltantes (suelo,
  luz, DHT; el termistor nunca entra como T), que la consulta no toque el buffer, reset.
- `test/test_modelo`: API fija, clase 1..3 y probas que suman 1 en un barrido
  de 3600 vectores, clase = argmax, paridad con `vectores.h`, formato exacto
  de la línea `[INF]`.
- `test/test_replay`: pasa un tramo real por `plantaia_inferir()` (el mismo
  código que la placa) e imprime las `[INF]`. Exige que todas infieran y que
  `t_us < 1000` (en el host; el número de la ESP32 sale del log de la placa).
  Los datos están en `replay_datos.h`, generado por
  `tools/generar_replay.py` desde un CSV crudo remuestreado a 5 min (mediana
  por bin). Un bin vacío o un cambio de `boot_id` corta la ventana (vacía el
  buffer), igual que `asignar_tramos()` en `ml/plantaia_ml/features.py`. El
  tramo por defecto (19/10 14:00Z, 150 muestras) cruza un riego. Se pueden
  sumar otros tramos medidos repitiendo `--tramo`:

  ```bash
  /opt/anaconda3/bin/python firmware/tools/generar_replay.py \
      --tramo data/mediciones_raw_2026-10-21.csv maceta-01 2026-10-19T14:00Z 150 \
      --tramo data/mediciones_raw_2026-10-21.csv maceta-01 <desde> 150
  firmware/tools/correr_replay.sh
  ```

`test/test_dht` es un sketch `.ino` de diagnóstico, no una suite: está en
`test_ignore`. En `[env:esp32dev]` se ignoran todas las carpetas de `test/`
(las suites son del host y tienen `main()` propio).
