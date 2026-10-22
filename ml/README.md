# ml — paquete `plantaia_ml` (Tarea 2)

Código Python compartido entre los notebooks, los tests y el exportador a C.
El contrato que manda (features, orden, unidades, protocolo) está en
[docs/ENTREGA2.md](../docs/ENTREGA2.md); el gemelo en C de las features vive en
[firmware/lib/plantaia_ml/](../firmware/lib/plantaia_ml/README.md).

Python: `/opt/anaconda3/bin/python`, con las versiones fijadas en
`requirements.txt`. No se instalan paquetes nuevos en ese entorno.

## Módulos

| módulo | qué hace |
|---|---|
| `__init__.py` | Rutas del repo (`RAIZ`, `DATOS`, `FIGURAS`), clases y códigos del firmware, `SNAPSHOT_VIGENTE` |
| `datos_reales.py` | Carga y limpieza de los snapshots crudos de Railway (§3.1): hora (`ts_dispositivo` o `ts_servidor`), episodio por fila desde `episodios.csv`, remuestreo a 5 min por `boot_id`, marcas `post_boot` / `suelo_saturado` / `dudoso` |
| `features.py` | Las 7 features del contrato §4 con la misma semántica que el buffer circular de la placa (tramos, faltantes, warm-up). Gemelo de `features.{h,cpp}` |
| `dataset.py` | `serie_maceta01()`: la tabla de modelado a 5 min (features + clase + `episodio_id` + `fuente`). Suma los datos simulados locales de `data/sintetico/` (o de `$PLANTAIA_SINTETICO`) si existen |
| `modelos.py` | Candidatos, partición por episodio (`StratifiedGroupKFold`) con búsqueda anidada, estimación de costo en la ESP32 y `CONFIG_FINAL`, el modelo que va a la placa (Random Forest de 30 árboles, `max_depth=5`, `min_samples_leaf=20`, sólo `suelo_mv`) |
| `exportar_c.py` | Reentrena `CONFIG_FINAL` y escribe el header C y los vectores de paridad (ver abajo) |
| `simulador.py` | **Local, no versionado.** Motor de simulación de `maceta-01` (ambiente, sustrato, planta, sensores) |
| `relleno.py` | **Local, no versionado.** Completa los huecos de la serie real con el simulador, empalmando con los bordes (§3.2) |

## Tests

```bash
cd ml && /opt/anaconda3/bin/python -m pytest -q tests
```

`tests/test_features.py` verifica `features.py` contra el contrato §4 (orden,
warm-up, media de luz, VPD, cortes por hueco y `boot_id`, faltantes, termistor
nunca como respaldo, sonda saturada como faltante). La paridad con el C la
verifica `pio test -e native` en `firmware/`.

## Exportar el modelo a la placa

```bash
cd ml && /opt/anaconda3/bin/python -m plantaia_ml.exportar_c
```

Escribe tres archivos **generados** (no se editan a mano):

- `firmware/lib/plantaia_ml/modelo_plantaia.h` — el modelo, con la API fija
  `plantaia_predecir()`.
- `firmware/test/test_modelo/vectores.h` — paridad de clase Python↔C.
- `firmware/test/test_features/paridad_features.h` — paridad de features.

Después: `cd firmware && pio test -e native` tiene que dar verde. La elección
del modelo y sus métricas están en `notebooks/03_modelos.ipynb` y
`docs/entrega2/RESULTADOS.md`.

El modelo exportado hoy es **`rf-f04-7734f6`**. `CONFIG_FINAL`: Random Forest
de 30 árboles, `max_depth=5`, `min_samples_leaf=20`, con `suelo_mv` y
`vpd_kpa`. Sale de tres reglas de `modelos.py`:

- la **restricción de diseño**: todo candidato usa `suelo_mv` y al menos una
  feature ambiental;
- la **compuerta de influencia**: la ambiental cambia la clase de ≥ 1 % de las
  filas reales;
- la **condición de seguridad** (`configuraciones_seguridad`): recall de
  marchita real ≥ 0,9 y el ep. 12 bien.

Las dos últimas se agregaron después de ver resultados; ver
`docs/entrega2/RESULTADOS.md`. Reemplaza al Naive Bayes `nb-f02-fa0df4` y al
RF sólo-suelo `rf-f0-c42286`.

`matriz_X(df)` arma la entrada descartando explícitamente las columnas de
etiqueta y procedencia (`etiqueta_origen`, `dudoso`, `episodio_id`, `fuente`,
…). El exportador sabe escribir árbol, RF, regresión logística y Naive Bayes
gaussiano. La
versión es `tipo-f<features>-<hash>`, con un hash del C generado: cambia si
cambian los datos de entrenamiento (por ejemplo, los datos simulados).

El exportador entrena con la serie completa de `serie_maceta01()`, que incluye
los datos simulados locales si están en `data/sintetico/` (o en
`$PLANTAIA_SINTETICO`): sin ellos el modelo exportado sale distinto. El modelo
`rf-f04-7734f6` se entrenó con el relleno simulado **v2**, el recalibrado tras
[docs/entrega2/AUDITORIA_DATOS.md](../docs/entrega2/AUDITORIA_DATOS.md).

## Datos simulados: sólo locales

`simulador.py`, `relleno.py` y `data/sintetico/` están en `.gitignore`. Todo lo
que generan lleva `fuente` distinta de `real`, **nunca va a Railway ni al
repo**, y las métricas sobre lo medido se reportan filtrando por
`fuente == 'real'`, nunca por dispositivo. Son **datos simulados** calibrados
con lo medido (curva de la sonda, luz, T/HR, ruido y deriva de `maceta-01`),
no datos reales. Cada fila lleva `firmware_version="relleno"` y
`etiqueta_origen="simulada"` (valor propio: `corregida` es sólo el
reetiquetado humano desde el front); `dataset.py` los lee sólo del archivo
local y levanta un error si el snapshot de Railway trae alguno. Para regenerar el relleno (con los archivos locales
presentes):

```bash
cd ml && /opt/anaconda3/bin/python -m plantaia_ml.relleno
```

Escribe en `data/sintetico/` (`payloads_relleno.jsonl`,
`episodios_relleno.csv`, `relleno_resumen.csv`). Para generar una versión
nueva sin pisar la vigente, usar la variable de entorno `PLANTAIA_SINTETICO`
(opcional) o `--salida`:

```bash
cd ml && PLANTAIA_SINTETICO=../data/sintetico_v3 /opt/anaconda3/bin/python -m plantaia_ml.relleno
```

`dataset.py` lee la misma variable: con `PLANTAIA_SINTETICO` fijada, el
notebook y el exportador usan esa carpeta en lugar de `data/sintetico/`.
