# Tarea 2 — Modelo supervisado con inferencia en la ESP32

Plan de trabajo y **contrato entre las partes** (datos, modelos, firmware,
informe). Si dos piezas no coinciden en un nombre de feature, un orden o una
unidad, manda lo que dice este archivo; si este archivo está mal, se corrige
acá primero y después en el código.

Fecha de arranque: 2026-10-21.

---

## 0. Qué pide la consigna y dónde queda cada cosa

| Requisito | Entregable | Dónde |
|---|---|---|
| Usar el dataset de la Tarea 1 | Snapshot real + episodios | `data/mediciones_raw_2026-10-21.csv`, `data/episodios.csv` |
| Preparar los datos / feature engineering | Módulo de features compartido | `ml/plantaia_ml/features.py` |
| Codificar el target | 3 clases, códigos 1–3 (ver §2) | `ml/plantaia_ml/` |
| Implementar y comparar clasificadores | Notebook ejecutado + resumen de resultados | `notebooks/03_modelos.ipynb`, `docs/entrega2/RESULTADOS.md`, `docs/entrega2/tablas_03_modelos.md` |
| Visualizar resultados | Figuras en el notebook + PNG exportados | `docs/entrega2/fig/` |
| Calidad de los datos | Auditoría de la base | `docs/entrega2/AUDITORIA_DATOS.md` |
| Elegir modelo compatible con la ESP32 | Tabla rendimiento × costo | notebook §5 |
| Exportar el modelo | Header C generado (versión en `PLANTAIA_MODELO_VERSION`) | `firmware/lib/plantaia_ml/modelo_plantaia.h` |
| Inferencia en tiempo real en la placa | Firmware 2.0.0 | `firmware/src/main.cpp` + `firmware/lib/plantaia_ml/` |
| Actuador físico | Semáforo LED = predicción del modelo | GPIO 25/26/27 |
| Documentar la lógica en el micro | | `firmware/lib/plantaia_ml/README.md` |
| Discusión (ventajas, límites, memoria/CPU, mejoras) | | informe + notebook §7 |
| Informe PDF ≤ 3 páginas | Fuente + PDF | `docs/entrega2/informe/` (fuera del repo) |
| Logs de inferencia en tiempo real | Replay en host (la placa no se reflasheó) | `docs/entrega2/logs/replay_host.txt` |

---

## 1. Punto de partida (honesto)

- Datos reales de `maceta-01` del 12/09 al 21/10: **14.791 filas**, pero la
  cadencia quedó en **30 s** (la placa nunca se reflasheó con los 5 min) y el N
  efectivo son los **episodios de etiqueta**: 10 al 08/10, ~13 con la tanda del
  18–21/10.
- `notebooks/02_analisis_ampliado.ipynb` ya mostró que con `GroupKFold` por
  episodio un Random Forest sobre los datos reales da **5 % de exactitud
  balanceada** (peor que el azar): con tan pocos episodios el modelo aprende a
  qué episodio pertenece una fila, no la condición de la planta. La clase
  además está confundida con la hora del día (V de Cramér 0,70).
- **Conclusión: con tan pocos episodios cualquier métrica fuera de muestra es
  frágil.** Aun así se entrena y evalúa **sólo con lo que midió la placa**:
  partición por episodio, baselines obligatorios, y el N que se reporta son
  los episodios reales. Los días sin datos no se completan (§3.2).

### Decisión de arquitectura que cambia

`docs/ARQUITECTURA.md` §7 ponía la inferencia en el backend (respuesta del
POST). La Tarea 2 exige inferencia **en la ESP32**, así que:

- El modelo corre en la placa y prende el LED aunque no haya WiFi.
- Las features tienen que poder calcularse con un buffer chico en RAM: **ventana
  máxima de 1 h** (13 muestras a 5 min). Nada de medias de 6 h / 24 h.
- La predicción viaja igual en el POST (`prediccion_*`, §5.4). El backend hoy
  ignora esos campos; persistirlos (tabla `predicciones`, migración) queda como
  mejora, **no** es parte de esta entrega.

---

## 2. Target

Multiclase, **3 clases**, códigos del firmware (CLAUDE.md es la fuente):

| código | clase | LED |
|---|---|---|
| 1 | `saludable` | verde (27) |
| 2 | `estresada` | amarillo (26) |
| 3 | `marchita` | rojo (25) |

`sin_etiquetar` (0) se excluye del entrenamiento. Como análisis secundario el
notebook reporta también la versión binaria *requiere cuidado* (`estresada` ∪
`marchita` vs `saludable`), pero **el modelo que va a la placa es el de 3
clases**.

---

## 3. Datos

### 3.1 Reales

1. Snapshot nuevo `data/mediciones_raw_2026-10-21.csv` (ya bajado). Los
   snapshots viejos no se tocan.
2. Extender `data/episodios.csv` con los episodios del 18–21/10 a partir de las
   pulsaciones `manual` (muestras 6920, 6922, 7795, 12208). Ojo: el botón
   cicla `saludable→estresada→marchita`, así que pulsaciones a segundos de
   distancia son una sola observación (la última). Cada episodio con su nota.
3. Limpieza para el modelo (en `ml/plantaia_ml/datos_reales.py`):
   - Hora: `ts_dispositivo` si es ≥ 2026-01-01, si no `ts_servidor` (la fila
     id 1 trae 2025-09-11 con el reloj sin sincronizar).
   - **Remuestrear a 5 min** (mediana por bin de 5 min), para que la ventana de
     1 h signifique lo mismo que en la placa.
   - Descartar los **primeros 60 min tras cada `boot_id` nuevo**: el transitorio
     de la sonda tiene τ de 24–83 min, y a los 30 min queda la mitad
     (`post_boot_min`).
   - Descartar `suelo_saturado` (sonda fuera del sustrato) y filas sin episodio.
   - Marcar los episodios dudosos para reportar con y sin ellos
     (`EPISODIOS_DUDOSOS = {8, 9, 11, 14}`, ver la nota de cada uno).

### 3.2 Los días sin datos de `maceta-01`

Hay **una sola maceta**, `maceta-01`, y su serie tiene huecos: los grandes son
**17/09 → 01/10** (con algunas filas sueltas el 21–22/09) y **03/10 → 18/10**,
más cortes chicos por reinicios y cortes de luz. **Los huecos quedan como
huecos**: no se interpolan ni se completan con datos simulados.

- Las features cortan la ventana en cada hueco y en cada `boot_id` nuevo
  (§4), igual que el buffer de la placa.
- El costo es tener menos episodios de cada clase: el modelo se entrena y se
  evalúa con lo que hay, y la incertidumbre se reporta sobre los episodios
  medidos, no sobre las filas.

### 3.3 Las temperaturas altas no son outliers

La maceta estuvo **sobre un radiador**. Las 547 filas reales con ≥ 26 °C
(15/09, hasta 35,6 °C con HR ~23 % y sustrato seco; 16/09, hasta 31,3 °C) son
condición real de la planta. No se recortan ni se filtran, y están anotadas en
`data/README.md` y en las notas de los episodios.

---

## 4. Contrato de features

Calculadas **cada 5 min** sobre la muestra actual y un buffer circular de las
últimas 13 muestras. Mismo código en Python (`ml/plantaia_ml/features.py`) y
C++ (`firmware/lib/plantaia_ml/features.{h,cpp}`); un test de paridad lo
garantiza.

| idx | nombre | definición | unidad |
|---|---|---|---|
| 0 | `suelo_mv` | mediana de 9 de la sonda | mV |
| 1 | `suelo_delta_1h` | `suelo_mv(t) − suelo_mv(t−60 min)`; 0 si no hay 1 h de historia | mV |
| 2 | `temp_c` | DHT11; si falla, último valor válido | °C |
| 3 | `hum_aire_pct` | DHT11; si falla, último valor válido | % |
| 4 | `vpd_kpa` | `0.6108·exp(17.27·T/(T+237.3))·(1 − HR/100)` con 2 y 3 | kPa |
| 5 | `luz_mv` | mediana de 9 del LDR | mV |
| 6 | `luz_media_1h` | media de `luz_mv` en las muestras de la última hora (incluida la actual) | mV |

Reglas:

- El orden del vector es este y no cambia. Si el modelo final usa un
  subconjunto, el exportador remapea índices; la placa siempre arma el vector
  completo.
- **Fuera a propósito**: hora del día (en el dato real está confundida con el
  horario del observador), `luz_pct` y `suelo_pct` (sin calibrar), termistor
  como feature. **Tampoco como respaldo de T**: la conversión del firmware
  1.1.0 está invertida (marca 38 °C con 8,5 °C reales) y sin DHT no hay HR
  igual.
- **Sin DHT válido desde el arranque no se infiere**: no hay reemplazo para la
  HR y el VPD depende de ella. Inventar una HR por defecto sería meter un dato
  falso en el modelo. En ese caso los LEDs quedan apagados, el LCD muestra
  `Pred:sin datos` y el POST lleva `sin_prediccion` en `errores`. Las fallas
  sueltas del DHT se cubren con el último valor válido.
- *Warm-up*: hasta tener 1 h de historia, `suelo_delta_1h = 0` y la media de luz
  usa lo que haya. La inferencia corre igual pero el log lleva `warmup=1`.
- Si `suelo_mv` o `luz_mv` faltan en una muestra, se repite la anterior en el
  buffer y se marca en el log. **La sonda saturada (`suelo_raw` 0 o 4095)
  cuenta como faltante**. La luz saturada no: es luz fuerte (u oscuridad
  total con `luz_raw = 0`).

---

## 5. Modelos, export y firmware

### 5.1 Protocolo de evaluación

- **Partición por `episodio_id`** (k=5, `StratifiedGroupKFold`) sobre la
  serie medida de `maceta-01`. Con 11 episodios cada fold de test tiene 2 o 3
  y ninguno tiene las tres clases, así que las métricas se calculan **una vez
  sobre las predicciones fuera de fold juntas**, con el desvío de un
  **bootstrap por episodio** (no media ± desvío por fold).
- Las métricas se reportan con y sin los episodios dudosos (8, 9, 11, 14).
- Baselines obligatorios: clase mayoritaria y un umbral único sobre `suelo_mv`
  (el notebook suma dos umbrales sobre `suelo_mv`, el rival honesto).
- Métricas: exactitud balanceada, F1 macro, recall de `marchita` (el error caro
  es no avisar), matriz de confusión, ROC-AUC OvR cuando haya probabilidades.

### 5.2 Candidatos

Regresión logística, árbol de decisión (profundidad ≤ 8), Random Forest chico
(≤ 30 árboles, profundidad ≤ 8), Naive Bayes gaussiano, k-NN, SVM RBF, MLP
chico. Hiperparámetros con búsqueda interna también por grupos.

Para cada uno, además de las métricas: **flash estimada** (bytes de
parámetros/código C), RAM en inferencia, operaciones por predicción y si es
exportable sin librerías. k-NN y SVM RBF necesitan guardar el dataset o los
vectores de soporte: se evalúan para la comparación pero se descartan por costo
salvo que el número diga otra cosa.

### 5.3 Selección y export

- Criterio: mejor F1 macro dentro de 1 desvío del mejor, con **flash < 32 KB,
  sin memoria dinámica, < 1 ms por inferencia**; desempate por
  interpretabilidad.
- Exportador propio `ml/plantaia_ml/exportar_c.py` (sin dependencias nuevas)
  → genera `firmware/lib/plantaia_ml/modelo_plantaia.h` con cabecera
  `GENERADO — no editar`, versión, orden de features y métricas.
- API C fija:

  ```c
  #define PLANTAIA_N_FEATURES 7
  #define PLANTAIA_MODELO_VERSION "..."
  // Devuelve el código de clase 1..3; si proba != NULL escribe proba[0..2]
  // en el orden saludable, estresada, marchita.
  int plantaia_predecir(const float x[PLANTAIA_N_FEATURES], float *proba);
  ```

- **Paridad Python↔C**: el exportador escribe vectores de prueba
  (`firmware/test/test_modelo/vectores.h`) y `pio test -e native` exige 100 %
  de coincidencia de clase. Idem para features: una secuencia cruda pasada por
  el buffer en C tiene que dar los mismos vectores que `features.py`.

### 5.4 Firmware 2.0.0

- `FW_VERSION "2.0.0"`, cadencia 5 min (ya está en el código; **hay que
  flashear**).
- En cada tick de 5 min: leer → empujar al buffer → features → predecir →
  medir `micros()` → **LEDs según la predicción** → LCD → log → POST.
  La inferencia no depende del WiFi.
- El botón sigue registrando la observación manual (`condicion`), pero ya no
  maneja el semáforo: el semáforo es la salida del modelo. La pulsación
  larga sigue forzando un envío.
- Log por Serial, una línea parseable por inferencia:
  `[INF] n=123 warmup=0 x=[1532,-41,20.6,47,1.29,871,850] -> estresada p=[0.10,0.78,0.12] t_us=37`
- Payload: se agregan `prediccion_codigo`, `prediccion_etiqueta`,
  `prediccion_proba`, `modelo_version`.
- Lógica sin Arduino en `firmware/lib/plantaia_ml/` para poder testearla en el
  host con `[env:native]`.
- **Replay en host**: un test nativo pasa un tramo real (19/10, 150 muestras)
  por el mismo código y deja el log en `docs/entrega2/logs/replay_host.txt`.

---

## 6. Tareas, orden y responsables

```
Fase 1 (en paralelo)          Fase 2                 Fase 3
  A. datos ────────────────►  B. modelos + export ─┐
  C. firmware (modelo de prueba) ────────────────── ├─► D. informe + docs
                                                    └─► Integración (pio test, pio run)
```

| # | Tarea | Agente | Estado |
|---|---|---|---|
| A1 | Episodios 11+ del 18–21/10 en `episodios.csv` + `data/README.md` | datos | ✅ |
| A2 | `datos_reales.py`: limpieza, remuestreo, post-boot | datos | ✅ |
| A3 | `features.py` según §4 + tests | datos | ✅ |
| A4 | Documentar los huecos de `maceta-01` (§3.2); se entrena sólo con lo medido | datos | ✅ |
| C1 | `lib/plantaia_ml/` (buffer, features, API del modelo con un modelo de prueba) | firmware | ✅ |
| C2 | `main.cpp` 2.0.0: inferencia cada 5 min, LEDs, LCD, log, payload | firmware | ✅ |
| C3 | `[env:native]` + tests de features + replay | firmware | ✅ |
| B1 | `notebooks/03_modelos.ipynb`: preparación, baselines, 7 modelos, GroupKFold | modelos | ✅ |
| B2 | Evaluación con y sin dudosos, costo en la ESP32, selección justificada | modelos | ✅ |
| B3 | `exportar_c.py` → `modelo_plantaia.h` + vectores de paridad | modelos | ✅ |
| I1 | `pio test -e native` y `pio run` en verde con el modelo real | integración | ✅ |
| D1 | Informe ≤ 3 págs. en PDF + figuras + logs | informe | fuera del repo |
| D2 | Actualizar CLAUDE.md, ARQUITECTURA.md §7, READMEs | integración | ✅ |
| M1 | ~~Flashear la placa y capturar el log real de inferencia~~ | **Manuel** | descartado (2026-10-22): la placa sigue con 1.1.0 |
| M2 | Calibración semanal de la sonda (sigue pendiente en CALIBRACION.md) | **Manuel** | ☐ |

### Estado al 2026-10-21

- **Modelo final:** la versión vigente está en
  `firmware/lib/plantaia_ml/modelo_plantaia.h` (`PLANTAIA_MODELO_VERSION`) y
  la configuración en `CONFIG_FINAL` de `ml/plantaia_ml/modelos.py`.
  Métricas, costo y justificación en
  [docs/entrega2/RESULTADOS.md](entrega2/RESULTADOS.md).
  - **Restricción de diseño (2026-10-21):** el semáforo no puede depender sólo
    de la sonda. Todo candidato usa `suelo_mv` y al menos una ambiental del
    aire (T, HR o VPD). **La luz no entra** (decidido después de ver
    resultados: con luz el modelo aprende "oscuro → marchita").
  - **Condición de seguridad** (recall de marchita ≥ 0,9 sin dudosos y el
    ep. 12 ≥ 50 % fuera de fold): hoy no la cumple ninguna configuración sin
    luz, así que queda la del criterio de §5.3 (árbol de profundidad 2).
- **Sólo datos medidos:** el entrenamiento, la evaluación y el exportador usan
  sólo los episodios reales de `maceta-01` (§3.2).
- **X sin metadatos de etiqueta:** `modelos.matriz_X` y el notebook descartan
  explícitamente `etiqueta_origen`, `dudoso`, `episodio_id`, etc.
  antes de cualquier `fit`.
- **Episodios dudosos:** `EPISODIOS_DUDOSOS = {8, 9, 11, 14}`
  (`ml/plantaia_ml/datos_reales.py`). Las métricas se reportan
  con y sin ellos.
- **Pendientes conocidos que encontró la revisión y no se implementaron:**
  - Firmware 2.0.0 sin **cadencia de 1 min en las ventanas de recuperación**
    (CLAUDE.md): cambiaría el significado de la ventana de 13 muestras
    (`suelo_delta_1h`, `luz_media_1h` asumen 5 min entre muestras).
  - Firmware sin **buffer de reenvío en LittleFS**: no existe, tampoco en
    1.x. Si se cae el WiFi, las muestras de ese lapso no se reenvían (la
    inferencia y el LED siguen funcionando).
  - `GET /api/v1/dataset.csv` da **404**, aunque CLAUDE.md lo menciona; el
    volcado que existe es `/api/v1/mediciones.csv`.
  - Las **184 filas (5 min) posteriores al snapshot** (21/10 21:25 → 22/10
    12:40 UTC, `data/mediciones_raw_2026-10-22.csv`) no tienen observación
    manual y no entran al entrenamiento; se usan sólo como prueba de
    estabilidad (notebook §6.5: 100 % `saludable`).

### Lo que sólo puede hacer una persona

```bash
cd firmware
pio run -t upload            # con la placa por USB
pio device monitor | tee ../docs/entrega2/logs/placa_$(date +%F).txt
```

Dejarla al menos 1 h (para salir del warm-up), mojar/secar la sonda con la
mano para ver cambiar el LED, y pegar 10–20 líneas `[INF]` en el informe.

---

## 7. Reglas para quien trabaje en esto

- Python: `/opt/anaconda3/bin/python` (sklearn 1.6.1, pandas 2.2.3). Versiones
  en `ml/requirements.txt`. No instalar paquetes en ese entorno.
- No tocar `backend/` ni `frontend/`. A Railway sólo llega lo que manda la placa.
- No flashear la placa. `pio run` y `pio test -e native` sí.
- Los notebooks se commitean **ejecutados**.
- Español en docs, comentarios y nombres, como el resto del repo.
