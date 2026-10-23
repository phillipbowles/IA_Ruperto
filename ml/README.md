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
| `__init__.py` | Rutas del repo (`RAIZ`, `DATOS`, `FIGURAS`), clases y códigos del firmware, `SNAPSHOT_VIGENTE`, `MACETA` y `ALIAS_MACETA` (el identificador viejo con el que quedaron en la base las filas del 03/10 al 18/10) |
| `datos_reales.py` | Carga y limpieza de los snapshots crudos de Railway (§3.1): hora (`ts_dispositivo` o `ts_servidor`), episodio por fila desde `episodios.csv`, remuestreo a 5 min por `boot_id`, marcas `post_boot` / `suelo_saturado` / `dudoso` |
| `features.py` | Las 8 features del contrato §4 (incluida `h_desde_riego`, con el riego que sobrevive a los reinicios) con la misma semántica que el buffer circular de la placa (tramos, faltantes, warm-up). Gemelo de `features.{h,cpp}` |
| `dataset.py` | `serie_maceta01()`: la tabla de modelado a 5 min (features + clase + `episodio_id`), armada sólo con lo que midió la placa |
| `modelos.py` | Candidatos, partición por episodio (`StratifiedGroupKFold`) con búsqueda anidada, estimación de costo en la ESP32 y `CONFIG_FINAL`, el modelo que va a la placa |
| `exportar_c.py` | Reentrena `CONFIG_FINAL` y escribe el header C, los vectores de paridad (ver abajo) y `frontend/src/modelo_placa.json` (versión y nodos del árbol, que dibuja el dashboard) |

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

La versión vigente del modelo exportado está en la cabecera de
`firmware/lib/plantaia_ml/modelo_plantaia.h` (`PLANTAIA_MODELO_VERSION`), y
la configuración elegida (`CONFIG_FINAL`) con sus métricas, en
`docs/entrega2/RESULTADOS.md`. Se entrena y evalúa **sólo con lo que midió la
placa** (`maceta-01`); el N efectivo son los episodios, no las filas.

Cómo se llega a `CONFIG_FINAL` (`modelos.py`, ejecutado en
`notebooks/03_modelos.ipynb` §5):

- **Se entrena sin los episodios dudosos** (`EPISODIOS_DUDOSOS`) y se evalúa
  con y sin ellos.
- **Features**: todo candidato usa `suelo_mv` y ninguno la luz
  (`cumple_restriccion`). Desde el 2026-10-23 no se exige una variable del aire.
- **Candidato propio**: `ReglaSueloRiego`, dos umbrales sobre `suelo_mv` +
  "estresada si `h_desde_riego` ≤ H". Expone `tree_` como un árbol de sklearn,
  así el exportador la escribe como árbol (tipo `regla`).
- **Criterio** (§5.3): flash < 32 KB y < 1 ms; F1 macro sin dudosos dentro de
  1 desvío bootstrap del mejor; desempate por interpretabilidad. Hoy gana la
  regla: `CONFIG_FINAL` es `regla-p3-f07-79b556`. La condición de seguridad
  (recall de marchita ≥ 0,9 y el ep. 12 bien) se reporta y no se cumple.

`matriz_X(df)` arma la entrada descartando explícitamente las columnas de
etiqueta y procedencia (`etiqueta_origen`, `dudoso`, `episodio_id`, …). El
exportador sabe escribir árbol (y la regla), RF, regresión logística y Naive
Bayes gaussiano. La versión es `tipo-f<features>-<hash>`, con un hash del C
generado: cambia si cambian los datos de entrenamiento (por ejemplo, un
snapshot nuevo de Railway).

El exportador entrena con la serie completa de `serie_maceta01()` sobre el
snapshot vigente (`SNAPSHOT_VIGENTE`), sin los episodios dudosos.
