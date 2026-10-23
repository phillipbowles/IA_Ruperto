# Tarea 2 — Modelo supervisado con inferencia en la ESP32

Plan de trabajo y **contrato entre las partes** (datos, modelos, firmware,
informe). Si dos piezas no coinciden en un nombre de feature, un orden o una
unidad, manda lo que dice este archivo; si este archivo está mal, se corrige
acá primero y después en el código.

Fecha de arranque: 2026-10-21. Re-ejecutada el 2026-10-23 con el snapshot que
suma el tramo del 03/10 al 18/10 (§1.1).

---

## 0. Qué pide la consigna y dónde queda cada cosa

| Requisito | Entregable | Dónde |
|---|---|---|
| Usar el dataset de la Tarea 1 | Snapshot real + episodios | `data/mediciones_raw_2026-10-23.csv`, `data/episodios.csv` |
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
| Informe PDF ≤ 3 páginas | Fuente con marcas de figuras, figuras y PDF con carátula | `docs/entrega2/informe_final/` (las versiones anteriores, en `docs/entrega2/historico/`) |
| Logs de inferencia en tiempo real | Replay en host + log de la placa del 22/10 (modelo anterior) | `docs/entrega2/logs/replay_host.txt`, `docs/entrega2/logs/placa_2026-10-22*.txt` |

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

### 1.1 Re-ejecución con el tramo del 03/10 al 18/10 (2026-10-23)

- Snapshot `data/mediciones_raw_2026-10-23.csv` (21.850 filas). Trae
  4.354 filas a 5 min del **03/10 al 18/10**, que antes era un hueco, con 13
  observaciones manuales que pasan a ser los **episodios 16–28**. Es la misma
  maceta: esas filas quedaron en la base con el identificador `maceta-02` por
  error y se unifican al leer (detalle en `data/README.md`).
- Con 24 episodios (20 sin dudosos) el mejor candidato llega a F1 macro 0,78
  por episodio (antes ~0,3). La regla de dos umbrales sobre `suelo_mv` sigue
  siendo la mejor (0,82).
- El criterio de selección **no se tocó** y eligió otro modelo:
  `arbol-p3-f03-ee3419` (árbol de profundidad 3 con `suelo_mv` y
  `hum_aire_pct`), que reemplaza a `arbol-p2-f012-58e644`.

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

### 3.2 Los días sin datos

Hay **una sola maceta**, `maceta-01`, y su serie tiene huecos: el grande es
**17/09 → 01/10** (con algunas filas sueltas el 21–22/09; el del 03/10 →
18/10 se completó con el snapshot del 23/10, ver §1.1),
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
| 7 | `h_desde_riego` | horas desde el último riego detectado; 96 (tope) si no hubo o es más viejo | h |

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
- **Riego** (`h_desde_riego`, agregado el 2026-10-23): si la sonda de la
  muestra es una lectura real (no repetida), la ventana ya tenía 12 muestras
  antes (fuera de warm-up: el transitorio tras un arranque o volver a meter la
  sonda no cuentan) y cayó ≥ 250 mV respecto de la última empujada, se guarda
  la hora NTP de la muestra como último riego. La placa lo persiste en
  Preferences (`riego_ts`) y lo restaura al arrancar; sin hora NTP no se
  registran riegos. Python simula lo mismo: vacía la ventana en cada tramo
  pero conserva el riego.
- Si `suelo_mv` o `luz_mv` faltan en una muestra, se repite la anterior en el
  buffer y se marca en el log. **La sonda saturada (`suelo_raw` 0 o 4095)
  cuenta como faltante**. La luz saturada no: es luz fuerte (u oscuridad
  total con `luz_raw = 0`).

---

## 5. Modelos, export y firmware

### 5.1 Protocolo de evaluación

- **Partición por `episodio_id`** (k=5, `StratifiedGroupKFold`) sobre la
  serie medida. Con 24 episodios cada fold de test tiene 4 o 5 y no siempre
  están las tres clases, así que las métricas se calculan **una vez
  sobre las predicciones fuera de fold juntas**, con el desvío de un
  **bootstrap por episodio** (no media ± desvío por fold).
- **Se entrena sin los episodios dudosos** (8, 9, 11, 14) y las métricas se
  reportan con y sin ellos (decisión del 2026-10-23: con ellos en el train el
  modelo aprendía sus etiquetas).
- Baselines obligatorios: clase mayoritaria y un umbral único sobre `suelo_mv`
  (el notebook suma dos umbrales sobre `suelo_mv`, el rival honesto).
- Métricas: exactitud balanceada, F1 macro, recall de `marchita` (el error caro
  es no avisar), matriz de confusión, ROC-AUC OvR cuando haya probabilidades.

### 5.2 Candidatos

**Regla sonda + riego** (dos umbrales sobre `suelo_mv` + "estresada si pasaron
≤ H horas desde un riego", agregada el 2026-10-23), regresión logística, árbol
de decisión (profundidad ≤ 6), Random Forest chico (30 árboles, profundidad ≤
8), Naive Bayes gaussiano, k-NN, SVM RBF, MLP chico. Hiperparámetros con
búsqueda interna también por grupos. Cada candidato elige su subconjunto de
features: **siempre con `suelo_mv`, nunca con luz** (hasta el 2026-10-23 se
exigía además una variable del aire; se sacó porque no aportaba).

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
  #define PLANTAIA_N_FEATURES 8
  #define PLANTAIA_MODELO_VERSION "..."
  // Devuelve el código de clase 1..3; si proba != NULL escribe proba[0..2]
  // en el orden saludable, estresada, marchita.
  int plantaia_predecir(const float x[PLANTAIA_N_FEATURES], float *proba);
  ```

- **Paridad Python↔C**: el exportador escribe vectores de prueba
  (`firmware/test/test_modelo/vectores.h`) y `pio test -e native` exige 100 %
  de coincidencia de clase. Idem para features: una secuencia cruda pasada por
  el buffer en C tiene que dar los mismos vectores que `features.py`.

### 5.4 Firmware 2.1.0

- `FW_VERSION "2.1.0"` (2.0.0 + `h_desde_riego` con el riego persistido en
  Preferences), cadencia 5 min.
- En cada tick de 5 min: leer → empujar al buffer → features → predecir →
  medir `micros()` → **LEDs según la predicción** → LCD → log → POST.
  La inferencia no depende del WiFi.
- El botón sigue registrando la observación manual (`condicion`), pero ya no
  maneja el semáforo: el semáforo es la salida del modelo. La pulsación
  larga sigue forzando un envío.
- Log por Serial, una línea parseable por inferencia:
  `[INF] n=123 warmup=0 x=[1532,-41,20.6,47,1.29,871,850,96.0] -> estresada p=[0.10,0.78,0.12] t_us=37`
  y `[RIE] riego detectado ts=…` cuando detecta un riego.
- Payload: se agregan `prediccion_codigo`, `prediccion_etiqueta`,
  `prediccion_proba`, `modelo_version`.
- Lógica sin Arduino en `firmware/lib/plantaia_ml/` para poder testearla en el
  host con `[env:native]`.
- **Replay en host**: un test nativo pasa un tramo real (19/10, 200 muestras, cruza un riego)
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
| M1 | Flashear la placa y capturar el log real de inferencia | **Manuel** + agente | hecho el 22/10 con `arbol-p2-f012-58e644` (`t_us=33` en la ESP32); **falta flashear el firmware 2.1.0 con `regla-p3-f07-79b556`** (`firmware/tools/flashear_y_registrar.sh`) |
| A5 | Episodios 16–28 (03/10 → 18/10) + unificar las filas con identificador `maceta-02` | datos | ✅ (2026-10-23) |
| B4 | Re-ejecutar el notebook 03, re-exportar, informe v2 | modelos/informe | ✅ (2026-10-23) |
| B5 | `h_desde_riego` (Python + C + paridad), regla sonda + riego, entrenar sin dudosos, firmware 2.1.0, informe final | modelos/firmware/informe | ✅ (2026-10-23) |
| M2 | Calibración semanal de la sonda (sigue pendiente en CALIBRACION.md) | **Manuel** | ☐ |

### Estado al 2026-10-23

- **Modelo final:** la versión vigente está en
  `firmware/lib/plantaia_ml/modelo_plantaia.h` (`PLANTAIA_MODELO_VERSION`) y
  la configuración en `CONFIG_FINAL` de `ml/plantaia_ml/modelos.py`.
  Métricas, costo y justificación en
  [docs/entrega2/RESULTADOS.md](entrega2/RESULTADOS.md).
  - **`regla-p3-f07-79b556`** (2026-10-23): `h_desde_riego` ≤ 5,5 h →
    estresada; si no, `suelo_mv` ≤ 1716 → saludable, ≤ 1940 → estresada, si
    no → marchita. F1 macro fuera de fold 0,858 ± 0,049 sin dudosos.
    Reemplaza a `arbol-p3-f03-ee3419` (árbol con sonda + HR, entrenado con
    los dudosos: 0,711), que reemplazaba a `arbol-p2-f012-58e644`.
  - **Restricciones de features:** siempre la sonda, nunca la luz (aprende
    "oscuro → marchita"). La exigencia de una variable del aire (2026-10-21)
    se sacó el 2026-10-23: en octubre el aire casi no varió y sólo costaba F1.
  - **Condición de seguridad** (recall de marchita ≥ 0,9 sin dudosos y el
    ep. 12 ≥ 50 %): **no la cumple** (0,77 y 0 %). Se reporta.
  - **Riesgo principal:** el corte de 5,5 h coincide con el horario de las
    observaciones (5–6 h después de cada riego). Ver notebook 03 §7.2.
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
  - Las **272 filas (5 min) de `maceta-01` posteriores al ep. 15**
    (21/10 21:25 → 22/10 20:00 UTC) no tienen observación manual y no
    entran al entrenamiento; se usan sólo como prueba de estabilidad
    (notebook §7.3: 100 % `saludable`).
  - La pulsación `estresada` del 22/10 21:34 (firmware 2.0.0) cayó con la
    sonda saturada y sin filas utilizables después: no abre episodio.

### Lo que sólo puede hacer una persona

Conectar la placa por USB y correr (desde la raíz del repo):

```bash
firmware/tools/flashear_y_registrar.sh          # pio run -t upload + log a docs/entrega2/logs/
```

Después, mojar o secar la sonda para ver cambiar el LED y pegar las líneas
`[INF]` en `docs/entrega2/informe_final/informe.md` (sección 5).

---

## 7. Reglas para quien trabaje en esto

- Python: `/opt/anaconda3/bin/python` (sklearn 1.6.1, pandas 2.2.3). Versiones
  en `ml/requirements.txt`. No instalar paquetes en ese entorno.
- No tocar `backend/` ni `frontend/`. A Railway sólo llega lo que manda la placa.
- No flashear la placa. `pio run` y `pio test -e native` sí.
- Los notebooks se commitean **ejecutados**.
- Español en docs, comentarios y nombres, como el resto del repo.
