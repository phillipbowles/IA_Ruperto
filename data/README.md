# data — el dataset del proyecto

Cuatro tipos de archivo con roles distintos. La separación es la misma que describe
[docs/ARQUITECTURA.md](../docs/ARQUITECTURA.md) §3: hechos inmutables por un
lado, anotaciones humanas corregibles por otro.

| Archivo | Qué es | Quién lo escribe |
|---|---|---|
| `mediciones_raw_<fecha>.csv` | Volcado crudo de la base de Railway, 23 columnas. Lo que la placa midió. | `curl` a `/api/v1/mediciones.csv` |
| `episodios.csv` | Capa de etiquetas: intervalos `[ts_inicio, ts_fin)` con la condición de la planta. | **A mano** |
| `dataset.csv` | El dataset de análisis: el crudo limpio, cruzado con los episodios. **Es el entregable.** | `notebooks/01_eda.ipynb` |
| `simulados_<desde>_a_<hasta>.csv` | Mediciones **simuladas** (`maceta-sim`) para practicar. **No son datos medidos.** | generado con un script que no se versiona |

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

## Tanda del 1 al 3/10 y datos simulados

Snapshot `mediciones_raw_2026-10-08.csv`: 6.523 filas, **solo de la placa real**
(`maceta-01`, del 11/09 al 3/10). Las filas `maceta-sim` que hubiera en la base se
excluyeron del archivo: lo simulado vive en su propio CSV.

- **Real nuevo.** 3.489 filas del 1 al 3/10 y 3 episodios (8 a 10) anclados en
  las pulsaciones de las muestras 3034, 4242 y 4877. El 8 es una etiqueta a
  revisar con las fotos: `marchita` con el sustrato igual que `saludable`.
  Las 9 pulsaciones del 21–22/9 eran pruebas del botón y no tienen episodio.
- **Simulado.** `maceta-sim`, 4.248 filas en dos ventanas (23/9 12:00 a 1/10 00:30
  y 3/10 21:00 a 8/10 20:00) que no pisan lo medido, con 48 episodios
  (ids 11 a 58, autor `simulado`, nota que empieza con `SIMULADO:`). Se generó con un script local (semilla fija) que no se versiona: el CSV es la fuente.
- **Regla de oro.** Ninguna conclusión sobre la planta puede apoyarse en filas
  `maceta-sim`. Sirven para probar métodos (validación por episodio, ruido de
  etiquetas arrastradas), no para aprender sobre el lirio de paz.
- Para borrar las simuladas de la base (están marcadas `dispositivo = 'maceta-sim'`, `firmware_version = 'sim-1.0'`):
  `DELETE FROM mediciones WHERE dispositivo = 'maceta-sim';`
