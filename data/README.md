# data — el dataset del proyecto

Tres tipos de archivo con roles distintos. La separación es la misma que describe
[docs/ARQUITECTURA.md](../docs/ARQUITECTURA.md) §3: hechos inmutables por un
lado, anotaciones humanas corregibles por otro.

| Archivo | Qué es | Quién lo escribe |
|---|---|---|
| `mediciones_raw_<fecha>.csv` | Volcado crudo de la base de Railway, 23 columnas. Lo que la placa midió. | `curl` a `/api/v1/mediciones.csv` |
| `episodios.csv` | Capa de etiquetas: intervalos `[ts_inicio, ts_fin)` con la condición de la planta. | **A mano** |
| `dataset.csv` | El dataset de análisis: el crudo limpio, cruzado con los episodios. **Es el entregable.** | `notebooks/01_eda.ipynb` |

## El snapshot crudo no se toca ni se sobreescribe

Lleva la fecha en el nombre a propósito. El notebook analiza un archivo concreto
y no "lo que haya hoy en la base", así que los resultados del informe se pueden
reproducir meses después aunque la placa haya seguido midiendo. Para traer datos
nuevos se baja un snapshot nuevo:

```bash
curl -o data/mediciones_raw_$(date +%F).csv https://backend-production-a379.up.railway.app/api/v1/mediciones.csv
```

y se apunta el notebook al archivo nuevo, dejando el viejo donde está.

## `episodios.csv` es el archivo que se edita

La verdad de campo no es un valor por fila: es un **intervalo** durante el cual
la planta estuvo en un estado. Guardarla así hace que corregir un día entero sea
editar una línea en vez de 300 filas.

| Columna | Qué va |
|---|---|
| `episodio_id` | Entero único. Es la unidad independiente para analizar las etiquetas |
| `dispositivo` | `maceta-01` |
| `ts_inicio` / `ts_fin` | ISO-8601 **en UTC** (`2026-09-16T15:47:29Z`). Intervalo semiabierto: `ts_fin` no entra |
| `clase` | `saludable` \| `estresada` \| `marchita` |
| `origen` | `manual` \| `propagada` \| `corregida` — ver abajo |
| `autor`, `nota` | Quién y por qué. La nota importa más de lo que parece |

Dos episodios del mismo dispositivo **no pueden pisarse en el tiempo**. No hay
nada que lo valide todavía (en la base lo haría la constraint `EXCLUDE USING
gist` de ARQUITECTURA.md §3.2), así que por ahora es responsabilidad de quien
edita.

### `origen` dice cuánto hay que creerle a cada etiqueta

- **`manual`** — hubo una pulsación del botón dentro del episodio: alguien miró
  la planta y la clasificó en ese momento. Es la única evidencia directa.
- **`propagada`** — la placa arrancó con la etiqueta anterior guardada en
  `Preferences` y la siguió mandando. Nadie observó nada.
- **`corregida`** — se reconstruyó a posteriori. **Hay que justificarlo en la
  `nota`**, y el notebook reporta las conclusiones con y sin estos episodios.

En `episodios.csv`, `manual` significa que una observación directa ancla ese
episodio. Al materializar `dataset.csv`, sólo la fila exacta de la pulsación
conserva `etiqueta_origen = manual`; las filas posteriores del mismo episodio
quedan como `propagada`. En el dataset actual hay exactamente 4 filas manuales.

Marcar bien el origen no es burocracia: el episodio 1 es `corregida`, tiene
1542 filas —la mitad del dataset— y por sí solo triplica el tamaño de efecto
aparente de la temperatura. Sin la marca, esa distorsión sería invisible.

## Qué hay hoy

Snapshot del 2026-09-20, con datos del 12 al 17/09/2026:

- **3011 filas crudas** → 3007 después de descartar las 4 con el reloj roto.
- **25,7 h de medición efectiva** (la cadencia quedó en 30 s en vez de 5 min).
- **7 episodios** y **4 observaciones manuales**. Ese es el N que vale.
- La ventana de registro cierra el 17/09 a las 18:59.

## Tanda del 1 al 3/10

Snapshot `mediciones_raw_2026-10-08.csv`: 6.523 filas de la placa real (`maceta-01`,
del 11/09 al 3/10).

- 3.489 filas del 1 al 3/10 y 3 episodios nuevos (8 a 10) anclados en las
  pulsaciones de las muestras 3034, 4242 y 4877. El 8 es una etiqueta a revisar
  con las fotos: `marchita` con el sustrato igual que `saludable`. Las 9
  pulsaciones del 21–22/9 eran pruebas del botón y no tienen episodio.
- **La cadencia sigue en 30 s**, no en los 5 min del protocolo: el código del
  firmware dice 5 min desde el 29/9, pero la placa no se volvió a flashear.
  Todas las filas de la base llegan cada 30 s.
- Una fila (id 1) trae la hora de la placa en 2025 (reloj sin sincronizar). El
  dashboard la ubica con `ts_servidor`.

## Tanda del 18 al 21/10

Snapshot `mediciones_raw_2026-10-21.csv`: 14.791 filas de `maceta-01` (del 12/09
al 21/10). Las 6.523 primeras son idénticas al snapshot del 08/10.

- **8.268 filas nuevas**, del 18/10 23:31 al 21/10 21:21 UTC, todas en un solo
  arranque (`boot_id` 49). En este snapshot, entre el 03/10 20:35 y el 18/10
  23:31 no hay **ninguna** fila (ese tramo se cargó después: ver el snapshot
  del 23/10). Los `id` saltan de 6523 a 12213 porque
  la base tuvo filas de otro dispositivo que se borraron; `numero_muestra` sigue
  correlativo (6522 → 6523).
- **La cadencia sigue en 30 s y el firmware en 1.1.0** (99,6 % de los intervalos).
  Hay algunos cortes de 2,5 a 9 min (WiFi), ninguno más largo.
- **Episodios 11 a 15** (ver las notas en `episodios.csv`):

  | id | clase | origen | desde → hasta (UTC) | filas a 5 min* |
  |---|---|---|---|---|
  | 11 | saludable | propagada | 18/10 23:31 → 19/10 02:51 | 33 |
  | 12 | marchita | manual (6920 + 6922) | 19/10 02:51 → 10:18 | 90 |
  | 13 | estresada | manual (7795) | 19/10 10:18 → 22:41 | 146 |
  | 14 | estresada | propagada | 19/10 22:41 → 20/10 23:50 | 302 |
  | 15 | saludable | manual (12208) | 20/10 23:50 → 21/10 21:21 | 259 |

  \* después de descartar los primeros 30 min tras el arranque.

  - Las pulsaciones 6920 (`saludable`) y 6922 (`marchita`) están a 60 s: el
    botón cicla, así que es **una** observación y vale la última. La 6920 queda
    dentro del 11.
  - El 11 es `propagada` como el 2 y el 4: la placa arrancó con `saludable` en
    Preferences desde el 2/10 y nadie miró la planta hasta 3 h después, cuando
    la observación dijo `marchita`. Se marca como dudoso.
  - El **riego** del 19/10 a las 22:41 (muestra 9214) se ve solo: el sustrato
    salta de 1935 a 1512 mV en una muestra, la luz cae a 589 mV por la sombra de
    quien riega y la HR sube 5 puntos. Ahí se corta el 13 y empieza el 14, que
    es la etiqueta `estresada` arrastrada ~25 h después del riego sin que nadie
    la confirme, con el sustrato ya en el rango de los `saludable` de octubre.
    También se marca como dudoso.
- **Sustrato**: ~1750 mV en la marchita nocturna del 19/10, sube a ~1950 mV
  durante el día (se seca), ~1400–1500 mV después del riego. En septiembre la
  marchita marcaba ~2800 mV: la escala de la sonda se encogió (corrosión), y
  por eso hay que seguir con la calibración semanal de `docs/CALIBRACION.md`.
- **Transitorio post-arranque**: 2 filas `suelo_saturado` (3124 mV, sonda
  todavía fuera del sustrato) y después 2244 → ~1750 mV en ~3 h. Ajustando una
  exponencial a los 7 arranques largos de la base sale una amplitud de 200–480
  mV y una constante de 24–83 min (42 min en este). **Los 30 min que descarta
  `ml/plantaia_ml/datos_reales.py` dejan todavía ~la mitad del transitorio**;
  descartar 2 h sería más seguro, a costa de perder filas.
- **Luz**: las 2.976 filas con `luz_saturada` de esta tanda son todas de
  **oscuridad** (luz_raw = 0 → 142 mV), no del techo del ADC: el aviso se
  dispara en los dos extremos. De 19 a 22 h local hay una lámpara (~1780 mV
  constante), así que "luz alta" no siempre es sol.
- **Aire**: 17,8–21,4 °C y 40–58 % de HR, sin fallas del DHT11.
- **Termistor**: `temp_ntc_c` se mueve al revés que el DHT11 (25 °C cuando el
  DHT marca 20, 38 °C cuando marca 8,5). Ver la sección del radiador.

## Snapshot del 23/10: el tramo del 03/10 al 18/10

Snapshot `mediciones_raw_2026-10-23.csv`: **21.850 filas**, todas de la misma
maceta. Las 16.616 primeras son idénticas al snapshot del 22/10.

**Hay una sola maceta.** Las 4.354 filas del 03/10 20:40 al 18/10 23:25 UTC
quedaron en la base con el identificador `maceta-02` por error; son la misma
planta y la misma serie que `maceta-01`. Al leer un snapshot,
`ml/plantaia_ml/datos_reales.unificar_maceta` las pasa a `maceta-01` (y
renumera sus `boot_id` 1–4 a 1001–1004 para que no choquen con los arranques
1–4 de septiembre). En `episodios.csv` ya figuran como `maceta-01`.

### Del 03/10 al 18/10 (episodios 16 a 28)

- Cubre lo que antes era el hueco del 03/10 20:35 al 18/10 23:31. Firmware
  1.1.0, cadencia de **5 min exactos** (300 ± 1 s) con la hora alineada al
  minuto, 4 arranques.
- **13 pulsaciones manuales**, una por episodio, todas `manual` y ninguna
  dudosa: el sustrato acompaña a la etiqueta en todos (saludable ~1500–1610 mV,
  estresada ~1840–1870 mV, marchita ~1940–1960 mV).
- **Tres ciclos casi iguales** de ~5 días: saludable → estresada (el sustrato
  se seca) → marchita (12 h, **de día**) → **riego** a las 18:00 UTC (el
  sustrato cae ~435 mV en una muestra) → estresada 5–6 h de recuperación →
  saludable. Los episodios 19, 23 y 27 son esa recuperación: `estresada` con
  el sustrato ya mojado (~1490–1520 mV), la planta tarda en recuperar turgencia.
- Ambiente estable: 18,5–21,3 °C, 44–55 % de HR. 1.103 filas `luz_saturada`
  (oscuridad, `luz_mv = 142`).
- **Carga en la base**: estas filas tienen `id` 23186–27539, posteriores a la
  fila recibida el 22/10 21:34 (id 23185), aunque su `ts_servidor` diga
  03/10–18/10: se cargaron después. El análisis usa `ts_dispositivo`.

### Del 21/10 21:21 al 22/10 21:34

- 2.740 filas más del boot 49 (hasta el 22/10 20:02), todas `saludable`
  **propagada** de la pulsación del 20/10 (ep. 15). Nadie observó la planta:
  **no se les asigna episodio** y el notebook 03 las usa sólo como prueba sin
  etiqueta (§6.5), igual que en la versión anterior.
- **9 filas con firmware 2.0.0** (boots 55–58, 22/10 21:05 → 21:34): la placa
  se flasheó. Casi todas con la sonda saturada (3124 mV, fuera del sustrato) y
  `sin_prediccion`, tres con `hora_sin_sincronizar`. La última (muestra 17495)
  es una pulsación `estresada` con la sonda saturada: no alcanza para abrir un
  episodio (no hay ninguna fila utilizable después).

## El radiador del 15 y 16/09 (no son outliers)

Hay 547 filas con `temperatura_c ≥ 26 °C` y **son reales**: la maceta estuvo
sobre un radiador. No se recortan, no se filtran y no se tratan como error del
sensor.

| día | tramo (UTC) | T mediana / máx. | HR | sustrato | episodios |
|---|---|---|---|---|---|
| 15/09 | 12:35 → 15:34 | 33,8 / 35,6 °C | ~23 % | ~2780 mV (seco) | 2, 3 |
| 16/09 | 15:42 → 16:51 y 19:25 → 20:30 | 27,1 / 31,3 °C | ~24 % | ~1810–1980 mV (recién regado) | 4, 5, 6 |

El 16/09 la maceta se bajó del radiador entre las 17:00 y las 19:10 (~14 °C) y
volvió a subir; se cuenta como un mismo período. El VPD en esas filas llega a
4 kPa, tres veces el de un día normal en interior: es la condición de más
demanda de agua de todo el dataset.

El termistor, en cambio, marca 9 °C sobre el radiador y 38 °C en la noche fría
del 13/09. `termistor_mv` sube con la temperatura (+32 mV/°C), lo que indica que
el NTC está del lado de VCC del divisor y no del de GND como asume la fórmula de
`main.cpp`: la conversión refleja la temperatura alrededor de ~25 °C. Hasta
corregirlo, `temp_ntc_c` no sirve como temperatura (ni como respaldo del DHT11).

## Huecos de la serie

La serie tiene tramos sin registro de la placa (reinicios, cortes de luz y las
dos semanas del 17/09 al 01/10). El tramo del 03/10 al 18/10, que en los
snapshots anteriores era un hueco, ya está en la base (ver el snapshot del
23/10). **Los huecos quedan como huecos**: no se completan ni se interpolan.
Las features cortan la ventana en
cada hueco y en cada cambio de `boot_id` (contrato de ENTREGA2.md §4), igual
que el buffer de la placa, y el modelo se entrena y evalúa sólo con lo medido.
