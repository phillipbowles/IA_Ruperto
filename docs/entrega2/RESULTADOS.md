# Resultados de modelos — Tarea 2 (para el informe)

**FINAL, sólo con datos medidos por la placa, con la restricción de diseño "el semáforo no puede depender sólo de la sonda" (2026-10-22).**

- **De dónde salen los números.** De la ejecución commiteada de `notebooks/03_modelos.ipynb` sobre el snapshot de Railway del 21/10 (`data/mediciones_raw_2026-10-21.csv`). Todos están copiados de las salidas del notebook, que además reescribe las tablas en `docs/entrega2/tablas_03_modelos.md` (generado, no se edita).
- **Modelo de la placa:** árbol de decisión de profundidad 2 con **`suelo_mv` y `temp_c`** (`arbol-p2-f012-58e644`). Tres reglas: frío → marchita; si no, la sonda decide entre saludable y estresada.
- **En una línea:** con 11 episodios (7 sin dudosos) nada generaliza bien por episodio. El elegido pierde en F1 contra el baseline de dos umbrales sobre `suelo_mv`, aunque dentro del ruido, y ninguna configuración sin luz cumple la condición de seguridad "no perder la marchita".

## Datos

- **Sólo lo medido.** La serie de `maceta-01` remuestreada a 5 min (mediana por bin), cruzada con los episodios de `data/episodios.csv`. Los días sin registro quedan como huecos: no se completan ni se interpolan.
- **Filtros** (`dataset.serie_maceta01()`): fuera los primeros 60 min tras cada arranque (transitorio de la sonda), la sonda saturada, las filas sin vector completo y las que no caen en ningún episodio. Las features se calculan antes de filtrar, como las calcularía la placa.
- **Dónde hay dato.** Tres ventanas: 13–17/09, 1–3/10 y 19–21/10, con huecos de hasta 15 días entre medio.
- **Episodios perdidos.** El corte de 60 min elimina enteros los ep. 2, 4, 5 y 7 (`AUDITORIA_DATOS.md`, H7).

### Conteos

| | filas (5 min) | episodios | saludable | estresada | marchita |
|---|---|---|---|---|---|
| todos | 1.357 | 11 | 426 filas / 3 ep. | 598 / 5 | 333 / 3 |
| sin dudosos | 865 | 7 | 399 / 2 | 244 / 3 | 222 / 2 |

- Proporción de filas: 31,4 % saludable, 44,1 % estresada y 24,5 % marchita.
- **Episodios dudosos: 8, 9, 11 y 14** (motivo en `data/episodios.csv`):
  - 8: marchita con el sustrato igual que una saludable (~1550 mV), nocturna;
  - 9: estresada con el sustrato en ~1454 mV, el rango de los saludables de octubre;
  - 11: propagada de Preferences 16 días después, contradicha por la observación siguiente;
  - 14: estresada propagada ~25 h después de un riego, sin nadie que la confirme.
- **Las filas no son independientes**: dentro de un episodio todas comparten etiqueta y las contiguas están a 5 min. **El N efectivo son los episodios.**

### Episodios

| ep. | clase | origen | dudoso | filas | desde (UTC) | mediana `suelo_mv` | mediana `temp_c` | mediana `luz_mv` |
|---|---|---|---|---|---|---|---|---|
| 1 | marchita | corregida | | 132 | 13/09 00:55 | 2832 | 8,5 | 189 |
| 3 | estresada | manual | | 24 | 15/09 13:35 | 2767 | 34,2 | 2038 |
| 6 | estresada | manual | | 74 | 16/09 17:55 | 2048 | 14,6 | 2892 |
| 8 | marchita | manual | sí | 111 | 01/10 01:40 | 1518 | 20,6 | 142 |
| 9 | estresada | manual | sí | 52 | 01/10 10:55 | 1454 | 19,0 | 2300 |
| 10 | saludable | manual | | 140 | 02/10 01:55 | 1504 | 18,6 | 1977 |
| 11 | saludable | propagada | sí | 27 | 19/10 00:35 | 1786 | 20,2 | 142 |
| 12 | marchita | manual | | 90 | 19/10 02:50 | 1758 | 20,2 | 142 |
| 13 | estresada | manual | | 146 | 19/10 10:20 | 1927 | 19,4 | 1675 |
| 14 | estresada | propagada | sí | 302 | 19/10 22:40 | 1445 | 19,8 | 920 |
| 15 | saludable | manual | | 259 | 20/10 23:50 | 1453 | 20,2 | 879 |

**Lo que se ve** (`serie_maceta01_modelado.png`):

- **La escala de la sonda se corre entre meses.** En septiembre la marchita (ep. 1) marcaba ~2830 mV y las estresadas 2050–2770 mV. En octubre la marchita observada con el botón (ep. 12) está en ~1758 mV, **por debajo** de la estresada del día siguiente (ep. 13, ~1930 mV).
- **Septiembre tiene otro ambiente.** El ep. 1 es frío (~8,5 °C) y el ep. 3 es sobre el radiador (~34 °C). En octubre la temperatura queda en 19–21 °C.
- **Medianas por clase.** Con todos los episodios, `suelo_mv` no ordena las clases (saludable 1480, estresada 1465, marchita 1764 mV): los dudosos tienen el sustrato de una saludable con la etiqueta de otra clase. Sin dudosos sí (1474 < 1940 < 2802 mV), pero la marchita junta dos escalas (ep. 1 y ep. 12).
- **La marchita sin dudosos es fría** (8,9 °C, VPD 0,45 kPa): es el ep. 1. En el resto, T, HR y VPD casi no cambian entre clases.
- **La luz separa la marchita (142 mV, oscuridad del LDR) del resto**: todas las marchitas se observaron de noche. Es la hora del observador, no la planta (ver "Por qué la luz quedó afuera").

## Protocolo

- **Partición externa por episodio**: `StratifiedGroupKFold` k=5 con `episodio_id` como grupo. Un episodio entero cae en train o en test. Con 11 episodios cada fold de test tiene 2 o 3, así que **ningún fold tiene las tres clases**.
- **Búsqueda anidada de hiperparámetros**: interna k=3, también por episodio, maximizando F1 macro. El subconjunto de features es un hiperparámetro más, **restringido** a `suelo_mv` + al menos una ambiental del aire (10 subconjuntos, ninguno con luz; ver "Restricción de diseño").
- **Métricas sobre las predicciones fuera de fold juntas.** Como un fold de 2–3 episodios no tiene las tres clases, una métrica por fold no se puede promediar. Se juntan las predicciones fuera de fold de los 5 folds (cada fila predicha por un modelo que no vio su episodio) y se calcula una sola vez: exactitud balanceada (azar = 0,33), F1 macro, recall de `marchita` y ROC-AUC OvR cuando hay probabilidades.
- **El desvío sale de un bootstrap por episodio**: se remuestrean los episodios (estratificado por clase, 500 veces) y se recalcula la métrica.
- Cada métrica se reporta **con todos los episodios y sin los dudosos**. La selección usa "sin dudosos".
- **X sin metadatos de etiqueta.** Antes de cualquier `fit`, el notebook arma `X` descartando explícitamente la etiqueta en texto, `etiqueta_origen`, `dudoso`, `episodio_id`, `warmup`, `valido`, `post_boot`, la hora, etc. Un `assert` exige que queden exactamente las 7 columnas del contrato §4, en orden. El exportador usa el mismo resguardo (`modelos.matriz_X`). `episodio_id` se usa sólo como grupo de la partición, y `dudoso` sólo para reportar.
- **Fuga** (Random Forest con las 7 features, exactitud balanceada fuera de fold):

  | partición aleatoria (filas mezcladas) | por episodio |
  |---|---|
  | 0,943 | 0,135 |

  Mismo modelo y mismos datos. Toda la diferencia es fuga: con filas mezcladas el modelo reconoce el episodio, no la condición de la planta.

## Baselines y candidatos, partición por episodio (§4 del notebook)

Fuera de fold, ± desvío bootstrap por episodio. "s/d" = sin dudosos (7 episodios).

| modelo | exactitud bal. todos | F1 macro todos | exactitud bal. s/d | **F1 macro s/d** | recall marchita s/d | ROC-AUC s/d |
|---|---|---|---|---|---|---|
| Clase mayoritaria (baseline) | 0,095 ± 0,080 | 0,074 ± 0,050 | 0,232 ± 0,101 | 0,110 ± 0,054 | 0,000 | 0,423 |
| Umbral único `suelo_mv` (baseline) | **0,300 ± 0,154** | **0,272 ± 0,132** | 0,412 ± 0,188 | 0,388 ± 0,188 | **0,595 ± 0,363** | 0,512 |
| Dos umbrales `suelo_mv` (baseline) | 0,295 ± 0,148 | 0,269 ± 0,131 | **0,416 ± 0,191** | **0,393 ± 0,191** | **0,595 ± 0,363** | n/d |
| Regresión logística | 0,094 ± 0,057 | 0,081 ± 0,045 | 0,128 ± 0,066 | 0,142 ± 0,072 | 0,000 | 0,284 |
| **Árbol de decisión (tipo del elegido)** | 0,207 ± 0,066 | 0,186 ± 0,074 | 0,326 ± 0,046 | 0,316 ± 0,045 | 0,000 | 0,514 |
| Random Forest | 0,147 ± 0,046 | 0,127 ± 0,045 | 0,227 ± 0,059 | 0,213 ± 0,026 | 0,000 | 0,346 |
| Naive Bayes | 0,184 ± 0,069 | 0,172 ± 0,074 | 0,304 ± 0,074 | 0,297 ± 0,057 | 0,000 | 0,545 |
| k-NN | 0,086 ± 0,073 | 0,081 ± 0,050 | 0,141 ± 0,101 | 0,110 ± 0,053 | 0,000 | 0,363 |
| SVM RBF | 0,057 ± 0,059 | 0,052 ± 0,037 | 0,119 ± 0,099 | 0,069 ± 0,035 | 0,000 | n/d |
| MLP | 0,203 ± 0,120 | 0,223 ± 0,114 | 0,395 ± 0,141 | 0,306 ± 0,135 | 0,405 ± 0,363 | 0,563 |

- **Baselines**: clase mayoritaria (siempre `saludable`), umbral único (tocón de profundidad 1) y dos umbrales (`suelo ≤ t1` saludable, `≤ t2` estresada, si no marchita; t1 y t2 elegidos en el train por F1 macro). Usan sólo `suelo_mv` y no son elegibles.
- **Ningún candidato le gana al baseline de dos umbrales.** Sin dudosos, los dos umbrales dan 0,393 ± 0,191 de F1 macro y el mejor candidato (el árbol) 0,316 ± 0,045. Con desvíos de 0,05 a 0,19, todas las diferencias están dentro del ruido.
- **Con todos los episodios, todos quedan por debajo del azar** en exactitud balanceada (≤ 0,30): los dudosos se predicen por su sustrato, que contradice su etiqueta.
- **Recall de marchita fuera de fold ≈ 0 para casi todos.** Cuando una marchita está en test, las otras no se le parecen: 2832 mV con frío, 1758 mV, y 1518 mV en el dudoso. Sólo los umbrales (0,60) y el MLP (0,41) recuperan algo.
- **Las búsquedas eligen subconjuntos distintos en cada fold** (HR, T, VPD, delta): ninguna ambiental se impone.

## Costo estimado en la ESP32 (cada modelo reentrenado con todos los episodios)

Estimación de `costo_esp32` (`modelos.py`): parámetros en `float` de 4 B, RAM de trabajo durante la inferencia, operaciones por predicción y µs a 240 MHz (~10 ciclos por operación, ~1 µs por `expf`). Es un orden de magnitud para comparar.

| modelo | config de la búsqueda sobre todos los episodios | flash (B) | RAM (B) | ops | exp | µs est. | exportable |
|---|---|---|---|---|---|---|---|
| Clase mayoritaria | — | 4 | 0 | 0 | 0 | 0 | sí (constante) |
| Umbral único | suelo | 51 | 16 | 2 | 0 | 0,08 | sí |
| Dos umbrales | suelo | 8 | 0 | 2 | 0 | 0,08 | sí (dos if) |
| Regresión logística | suelo+hr, C=1 | 52 | 20 | 25 | 3 | 4,0 | sí |
| **Árbol de decisión** | **suelo+delta+temp, prof. 2, hoja 100** | **81** | 16 | 4 | 0 | 0,17 | sí (tablas) |
| Random Forest | suelo+hr, prof. 5, hoja 20 | 11.580 | 28 | 390 | 0 | 16,3 | sí (tablas) |
| Naive Bayes | suelo+hr+vpd | 84 | 12 | 39 | 3 | 4,6 | sí (fórmula cerrada) |
| k-NN | suelo+delta+hr, k=25 | 17.665 | 216 | 14.933 | 0 | 622 | guarda todo el train |
| SVM RBF | suelo+hr, C=0,1 | 17.468 | 28 | 10.904 | 1.090 | 1.544 | guarda los vectores soporte |
| MLP | suelo+temp+vpd, (8,) | 260 | 64 | 124 | 3 | 8,2 | sí |

- Todos caben en 32 KB. **Sólo la SVM queda afuera, por tiempo** (~1,5 ms estimados > 1 ms).
- **El modelo final exportado**: **81 B de tablas** en el header (5 nodos y 3 hojas: feature `int8`, umbral `float`, hijos `int16`, 3 × 3 probabilidades `float`; coincide con la estimación). Recorre a lo sumo 2 comparaciones por predicción. Sin memoria dinámica ni recursión.
- **`pio run`** del firmware completo 2.0.0 con este modelo: **flash 73,4 % (962.249 B de 1.310.720)** y **RAM 14,6 % (47.740 B)**. Contra el firmware 1.1.0 (957.897 B / 47.548 B) son +4.352 B de flash y +192 B de RAM, casi todo código de la librería (features, inferencia, log).
- **Paridad Python ↔ C.** `firmware/test/test_modelo/vectores.h` tiene **324 vectores**: filas de la serie y, para cada umbral del árbol, casos en el umbral y en el float32 inmediatamente arriba y abajo. `pio test -e native` da **21/21 tests OK**, con 100 % de coincidencia de clase.
- **Medido en el host** (replay, abajo): `t_us` de 0–1 µs. Falta medir en la placa (no se reflasheó).

## Sensibilidad a los dudosos y al ep. 13 (§5.2)

- **El conflicto del 19/10.**
  - Ep. 12: `marchita`, pulsación de noche con ~1756 mV.
  - Ep. 13: `estresada`, pulsación a la mañana siguiente con ~1796 mV. La mediana del episodio (1927 mV) es más alta porque siguió 11–12 h propagado mientras el sustrato se secaba, hasta el riego.
  - Ninguna regla monótona sobre `suelo_mv` respeta las dos.
- **Por qué el 13 no se marca dudoso.** No hay un motivo independiente de las métricas para hacerlo; se reporta la sensibilidad. El criterio de selección no cambia: usa "sin dudosos".

| F1 macro fuera de fold | todos | sin dudosos | sin el 13 | sin dudosos ni el 13 |
|---|---|---|---|---|
| Dos umbrales (baseline) | 0,269 | 0,393 | 0,311 | **0,481** |
| Umbral único (baseline) | 0,272 | 0,388 | **0,313** | 0,477 |
| Árbol (búsqueda anidada) | 0,186 | 0,316 | 0,137 | 0,250 |
| MLP | 0,223 | 0,306 | 0,160 | 0,219 |
| Naive Bayes | 0,172 | 0,297 | 0,104 | 0,197 |
| Random Forest | 0,127 | 0,213 | 0,123 | 0,226 |
| **Final `arbol-p2-f012-58e644` (config. fija)** | 0,181 | 0,282 | 0,206 | 0,328 |

Las tablas completas (exactitud balanceada y recall de marchita, los 10 modelos) están en `tablas_03_modelos.md`.

## Modelo elegido y justificación

- **Modelo:** `DecisionTreeClassifier`, `max_depth=2`, `min_samples_leaf=100`, `class_weight="balanced"`, con el subconjunto **`suelo_mv` + `suelo_delta_1h` + `temp_c`** (`CONFIG_FINAL` en `ml/plantaia_ml/modelos.py`).
- **Versión:** `PLANTAIA_MODELO_VERSION = "arbol-p2-f012-58e644"`.
- **Qué hace** (`arbol_final.png`):

  | condición | clase | LED |
  |---|---|---|
  | `temp_c` ≤ 10,25 °C | marchita | rojo |
  | `temp_c` > 10,25 °C y `suelo_mv` ≤ 1821,5 mV | saludable | verde |
  | `temp_c` > 10,25 °C y `suelo_mv` > 1821,5 mV | estresada | amarillo |

  - `suelo_delta_1h` está en el subconjunto, pero el árbol no corta por él.
  - Probabilidades de las hojas (saludable / estresada / marchita): frío 0 / 0 / 1; sonda húmeda 0,45 / 0,28 / 0,27; sonda seca 0,03 / 0,97 / 0. La hoja "saludable" es mezclada: ahí caen el ep. 12 y los dudosos.
- **Sonda fuera del rango medido**, con T normal: 900–1140 mV (más mojada que cualquier lectura) → `saludable` 100 %; 3000–3124 mV → `estresada` 100 %. Sin frío nunca da `marchita`.
- **Fuera de fold (configuración fija, mismos folds):**

  | | todos (11 ep.) | sin dudosos (7 ep.) |
  |---|---|---|
  | F1 macro | 0,181 ± 0,091 | 0,282 ± 0,136 |
  | exactitud balanceada | 0,200 ± 0,110 | 0,279 ± 0,136 |
  | recall de marchita | 0,240 ± 0,169 | 0,360 ± 0,220 |
  | ROC-AUC OvR | 0,243 | 0,440 |

  La cabecera de `modelo_plantaia.h` reporta estas métricas de la configuración fija y, en líneas aparte rotuladas "búsqueda anidada del tipo Árbol de decisión", las de la tabla por tipo (0,316 ± 0,045 sin dudosos).

### Paso 1: criterio de §5.3 (pre-registrado) en el espacio restringido

1. **Restricciones duras** (flash < 32 KB, < 1 ms, sin memoria dinámica): queda afuera la SVM.
2. **Rendimiento.** Puntaje = F1 macro fuera de fold sin dudosos. El mejor es el árbol, 0,316 (desvío bootstrap 0,045) → piso 0,272. Pasan el árbol, el MLP (0,306) y Naive Bayes (0,297).
3. **Desempate por interpretabilidad:** gana el árbol.

### Paso 2: configuración final (§5.5)

- Entre las configuraciones de la búsqueda sobre todos los episodios con F1 interno dentro de 1 desvío de la mejor (0,258 ± 0,041), la más simple (menos features, después menos profundidad) **que use la ambiental**.
- **Compuerta de influencia** (agregada después de ver resultados): la ambiental tiene que cambiar la clase de ≥ 1 % de las filas si se la lleva a su mediana.
- Resultado: `suelo+delta+temp`, profundidad 2, hoja 100. Con la temperatura en la mediana cambia la clase del **9,7 %** de las filas: cumple.
- Coincide con `CONFIG_FINAL` y el header exportado está al día (lo verifica el notebook).

### Paso 3: condición de seguridad (§5.6) — nadie la cumple

- **Por qué.** El error caro es no avisar marchita (`docs/ENTREGA2.md` §5.1): un semáforo que no se pone en rojo ante la marchita observada de octubre (ep. 12) no sirve, aunque gane en F1.
- **La condición** (`modelos.py`), sobre las predicciones fuera de fold sin dudosos:
  - recall de `marchita` ≥ 0,9, **y**
  - el ep. 12 con ≥ 50 % de sus filas bien.
- **La grilla** (`modelos.configuraciones_seguridad`): 66 configuraciones fijas, suelo + cada ambiental del aire y suelo + cada par, con regresión logística (C 0,01 / 0,1 / 1), árbol (prof. 2 / 3 / 4, hoja 100), RF de 30 árboles (prof. 3 / 5, hoja 20 / 100) y Naive Bayes.
- **Filtros, en orden:** costo → influencia ≥ 1 % → seguridad. Si ninguna configuración cumple, no se fuerza nada: queda la del paso 2.

| tipo | configuraciones | pasan costo | pasan costo + influencia | pasan seguridad | mejor recall marchita s/d | mejor acierto ep. 12 |
|---|---|---|---|---|---|---|
| Regresión logística | 18 | 18 | 18 | 0 | 0,595 | 0,28 |
| Árbol (prof. 2–4) | 18 | 18 | 11 | 0 | 0,000 | 0,00 |
| Random Forest chico | 24 | 24 | 24 | 0 | 0,000 | 0,00 |
| Naive Bayes | 6 | 6 | 6 | 0 | 0,000 | 0,00 |

- **Ninguna de las 66 la cumple.** Sin luz, nada reconoce la marchita de octubre fuera de fold: con 1758 mV está más húmeda que las estresadas de septiembre y que el ep. 13.
- **Con luz sí pasaban configuraciones**, pero detectan la noche (siguiente sección).
- Por la regla, **`CONFIG_FINAL` queda en la configuración del paso 2.** La tabla completa de las 66 está en `tablas_03_modelos.md`.

### Contra los baselines (§5.4)

| | F1 macro s/d | exactitud bal. (todos / s/d / s/d ni 13) | recall marchita s/d | ep. 12 | flash |
|---|---|---|---|---|---|
| **Árbol `arbol-p2-f012-58e644` (elegido, config. fija)** | 0,282 ± 0,136 | 0,200 / 0,279 / 0,361 | 0,360 | 0 % | 81 B |
| Árbol (búsqueda anidada del tipo) | 0,316 ± 0,045 | 0,207 / 0,326 / 0,277 | 0,000 | — | 81 B |
| Dos umbrales | **0,393 ± 0,191** | **0,295 / 0,416 / 0,567** | **0,595** | 0 % | 8 B |
| Umbral único | 0,388 ± 0,188 | 0,300 / 0,412 / 0,563 | 0,595 | — | 51 B |
| Clase mayoritaria | 0,110 ± 0,054 | 0,095 / 0,232 / 0,082 | 0,000 | — | 4 B |

- **Los dos umbrales le ganan en F1, dentro del ruido.** Con las mismas predicciones fuera de fold, el tipo elegido pierde −0,076 de puntaje contra los dos umbrales y gana en el **46 %** de las remuestras del bootstrap por episodio (contra el umbral único: −0,071, gana en el 45 %). Es un empate con muchísimo ruido.
- Los umbrales también recuperan más marchita (0,60 contra 0,36), pero tampoco aciertan el ep. 12.
- El elegido no se justifica por rendimiento sino por la restricción de producto: los umbrales usan sólo la sonda.

## Restricción de diseño: el semáforo no puede depender sólo de la sonda (§5.7)

### La decisión

- **El problema.** Un modelo sólo con `suelo_mv` deja al LED respondiendo únicamente a la sonda.
- **Por qué está mal como producto.**
  - La sonda es resistiva y deriva: la misma marchita marcaba ~2830 mV en septiembre y ~1758 mV en octubre.
  - La maceta tiene sensores de ambiente que el semáforo ignoraría.
- **La regla.** Todo candidato con selección de features usa `suelo_mv` + al menos una ambiental **del aire**: `temp_c`, `hum_aire_pct` o `vpd_kpa` (`modelos.cumple_restriccion`). `suelo_delta_1h` no cuenta (también sale de la sonda) y **la luz no entra** (`luz_mv`, `luz_media_1h`). Los baselines siguen siendo sólo-suelo, como referencia.
- **Declaración honesta.**
  - La restricción es una **decisión de producto, no un resultado de las métricas**.
  - La **exclusión de la luz se decidió después de ver resultados** (siguiente sección).
  - La **compuerta de influencia** (≥ 1 %) y la **condición de seguridad** también son decisiones de producto tomadas mirando los resultados. Hacen que el elegido no sea necesariamente el de mejor F1, y sus números quedan algo optimistas.

### Qué cuesta la restricción

Mismos folds, configuraciones fijas, sin dudosos:

| modelo | F1 macro s/d | exactitud bal. s/d | recall marchita s/d | ep. 12 | flash (header) |
|---|---|---|---|---|---|
| sólo suelo (RF, `rf-f0-395a04`) | 0,373 ± 0,061 | 0,411 | 0,00 | 0 % | 12.960 B |
| **final (árbol, `arbol-p2-f012-58e644`)** | 0,282 ± 0,136 | 0,279 | **0,36** | 0 % | 81 B |
| dos umbrales (baseline) | **0,393 ± 0,191** | **0,416** | **0,60** | 0 % | 8 B (dos if) |

- **Contra el sólo-suelo.** El RF sólo-suelo tiene mejor F1, pero no recupera ninguna marchita fuera de fold. El final sí, por el frío. En el bootstrap el final gana en el 15 % de las remuestras: la restricción cuesta F1, pero hay mucho ruido.
- **El ep. 12 no lo acierta ninguno.**

### ¿Influye la temperatura? Sí, con una sola regla y un solo episodio de respaldo

- **Importancia por permutación** (1.357 filas, 30 permutaciones; están en el train):

  | feature | caída exactitud bal. | % predicciones que cambian |
  |---|---|---|
  | `suelo_mv` | 0,123 ± 0,009 | 32,4 % |
  | `suelo_delta_1h` | 0 | 0 % |
  | `temp_c` | 0,146 ± 0,007 | 17,7 % |

- **`temp_c` en la mediana.** Cambia la clase del **9,7 % de las filas**: 132 filas, todas del **ep. 1** (13/09, ~8,5 °C), el 91 % de noche. Es la única marchita que el modelo reconoce.
- **Barrido** (`modelo_final_sensibilidad.png`): con `suelo_mv` fijo en valores de octubre (1480, 1619, 1758, 1927 mV) y T en su rango medido (8,1–34 °C), con T ≤ 10,24 °C todo es `marchita`; por encima decide la sonda. **En octubre la temperatura nunca bajó de 10 °C**, así que el modelo se comporta como **un solo umbral sobre la sonda (1821,5 mV)**.
- **¿Proxy de la hora?** V de Cramér con la franja de 3 h:

  | | V |
  |---|---|
  | clase observada | 0,471 |
  | predicción sólo suelo | 0,394 |
  | **predicción final** | **0,373** |
  | predicción final con T en la mediana | 0,211 |
  | `temp_c` en terciles | 0,363 |

  A sustrato fijo y con el ambiente de octubre, la predicción es la misma de día y de noche (1758 y 1619 mV → `saludable` 100 % en ambas franjas). Llevar T a la mediana baja la asociación de 0,37 a 0,21: esa parte viene del ep. 1 (frío y de noche).
- **Conclusión.** El modelo cumple la restricción de diseño: el LED depende de la sonda y de la temperatura. Pero el efecto ambiental es una regla ("frío → marchita") que sale de un solo episodio. Que un lirio de paz se marchite por debajo de ~10 °C es plausible, pero acá está respaldado por N = 1.

## Por qué la luz quedó afuera (§6.3)

- **La clase está atada a la hora del observador.** V de Cramér franja × clase = 0,47 (`clase_por_hora.png`). Todas las marchitas observadas son de noche (luz mediana 142 mV, la oscuridad del LDR), porque es cuando alguien miró la planta y apretó el botón.
- **Con la luz permitida, en la grilla de seguridad las únicas que pasaban eran regresiones logísticas con `luz_media_1h`**: recall de marchita 0,90–0,94 y ep. 12 al 96–100 %. Se reentrenaron y se probaron sobre las noches de los datos nuevos del 22/10, con la planta `saludable`:

  | regresión logística | F1 s/d | recall marchita s/d | ep. 12 | % marchita, datos nuevos de noche | % marchita, datos nuevos de día |
  |---|---|---|---|---|---|
  | suelo + luz_media_1h, C=0,01 | 0,607 | 0,914 | 97 % | **75,8 %** | 0 % |
  | suelo + luz_media_1h, C=0,1 | 0,594 | 0,905 | 96 % | **75,8 %** | 0 % |
  | suelo + luz_media_1h, C=1 | 0,589 | 0,901 | 96 % | **75,8 %** | 0 % |
  | suelo + luz + luz_media_1h, C=0,1 | 0,606 | 0,901 | 96 % | **78,3 %** | 1,6 % |
  | suelo + luz + luz_media_1h, C=1 | 0,621 | 0,937 | 100 % | **82,5 %** | 7,8 % |

- **Predicen `marchita` en el 76–83 % de las noches de una planta sana**: el LED quedaría rojo toda la noche. Aprendieron "oscuro → marchita".
- Por eso la luz quedó fuera del modelo de la placa. **Es una decisión tomada después de ver estos resultados**, y es la razón por la que la condición de seguridad hoy no la cumple nadie: lo único que "reconocía" la marchita de octubre era la noche.

## Análisis de errores

### El modelo final por episodio (§6.1)

| ep. | clase | dudoso | mediana `suelo_mv` | predice (entrenado con todo) | acierto entrenado con todo | acierto fuera de fold |
|---|---|---|---|---|---|---|
| 1 | marchita | | 2832 | 100 % marchita | 1,00 | **0,61** |
| 3 | estresada | | 2767 | 100 % estresada | 1,00 | 0,00 |
| 6 | estresada | | 2048 | 100 % estresada | 1,00 | **0,54** |
| 8 | marchita | sí | 1518 | 100 % saludable | 0,00 | 0,00 |
| 9 | estresada | sí | 1454 | 100 % saludable | 0,00 | 0,00 |
| 10 | saludable | | 1504 | 100 % saludable | 1,00 | **0,89** |
| 11 | saludable | sí | 1786 | 82 % saludable | 0,82 | 0,00 |
| 12 | marchita | | 1758 | 100 % saludable | **0,00** | **0,00** |
| 13 | estresada | | 1927 | 90 % estresada | 0,90 | 0,00 |
| 14 | estresada | sí | 1445 | 100 % saludable | 0,00 | 0,00 |
| 15 | saludable | | 1453 | 100 % saludable | 1,00 | 0,00 |

- **Fuera de fold acierta más de la mitad de las filas en 3 de los 7 no dudosos**: el 1 (frío), el 6 y el 10.
- **Falla el 3**: estresada sobre el radiador, con el sustrato de una marchita de septiembre.
- **Falla el 12**: la marchita de octubre a 1758 mV, que predice `saludable` incluso entrenado con todo.
- **Falla el 13 y el 15** fuera de fold: sin ese episodio en el train, el corte se mueve.
- **Falla todos los dudosos** (8, 9, 11 y 14), cuya etiqueta contradice al sustrato.
- Matrices de confusión fuera de fold (todos y sin dudosos): `matriz_confusion_final.png`; las de los 10 modelos, `matrices_confusion_candidatos.png`.

### La frontera sobre `suelo_mv` y la deriva de la sonda (§6.2)

- **La frontera** es un único corte en ~1821 mV (`fronteras_suelo_mv.png`, `modelo_final_suelo_mv.png`). Entrenado con todo, el ep. 13 queda arriba (estresada) y el 12 abajo (saludable).
- **Deriva de la sonda** (`auditoria_deriva_suelo.png`, `auditoria_suelo_por_clase_y_periodo.png`):

  | clase | septiembre (mediana `suelo_mv`) | octubre |
  |---|---|---|
  | saludable | — (sin episodios tras el filtro) | 1480 mV |
  | estresada | 2064 mV | 1457 mV |
  | marchita | 2832 mV | 1588 mV (con el dudoso 8) |

  El mismo estado de la planta lee ~1000 mV distinto según el mes. El corte de 1821 mV vale para la escala de octubre.

### Análisis secundario: binario *requiere cuidado* (§6.4)

`estresada` ∪ `marchita` contra `saludable`. No es el modelo de la placa; sirve para ver si al menos la pregunta gruesa "¿hay que hacer algo?" se puede contestar. Mismo protocolo por episodio.

| modelo | exactitud bal. todos | exactitud bal. s/d | recall cuidado s/d | ROC-AUC s/d |
|---|---|---|---|---|
| Clase mayoritaria | 0,500 | 0,500 | 1,000 | 0,500 |
| Umbral único | 0,396 | 0,516 | 0,403 | 0,696 |
| Árbol | 0,327 | 0,502 | 0,882 | 0,505 |
| Regresión logística | 0,377 | 0,569 | 0,717 | 0,611 |
| **Naive Bayes** | 0,481 | **0,743** | **1,000** | **0,964** |

- Sale mejor que la de 3 clases, pero con la misma advertencia de N: son 7 episodios no dudosos, 2 saludables contra 5 que requieren cuidado.
- Con todos los episodios todos quedan en ~0,4–0,5: los dudosos 8, 9 y 14 piden cuidado con el sustrato de una saludable.

## Prueba con datos nuevos de Railway (§6.5)

- **Qué es.** El modelo se entrenó con el snapshot del 21/10. La placa siguió mandando, así que el snapshot del 22/10 (`data/mediciones_raw_2026-10-22.csv`) trae muestras **que el modelo nunca vio**. Se pasan por el mismo `serie_maceta01` (remuestreo, features, filtros) y se predicen con el modelo final. No se suman al entrenamiento.
- **184 filas de 5 min**, del 21/10 21:25 al 22/10 12:40 UTC, de día y de noche (`suelo_mv` 1496–1520 mV, T 19,4–22,2 °C, luz 142–2522 mV).
- **Resultado: `saludable` en el 100 % (184/184)**, igual que la etiqueta que mandó la placa (`prueba_railway_nuevos.png`).
- **Límite.** Esas filas no tienen observación manual: la placa las mandó con `saludable` **propagada** de la pulsación del 20/10 (ep. 15) y nadie miró la planta. Es una prueba de estabilidad sobre un tramo `saludable` (y de que el modelo no confunde la noche con marchita), no una evaluación de las tres clases.

## Inferencia en tiempo real: replay en el host

La placa no se reflasheó (sigue con el firmware 1.1.0), así que el log de inferencia sale de un **replay en el host** con el mismo código que corre en la placa (`firmware/lib/plantaia_ml`): `docs/entrega2/logs/replay_host.txt`.

- **Tramo:** `maceta-01` desde el 19/10 14:00 UTC, 150 muestras de 5 min, que cruzan un riego.
- **150/150 inferencias**, 12 en warm-up, 0 con faltantes. **`t_us` máximo 1 µs** (113 en 0 µs, 37 en 1 µs; medido en el host, no en la ESP32).
- **Predichas:** 104 `estresada` (sonda en 1877–1936 mV, arriba del corte de 1821,5) y, desde el riego (`suelo_delta_1h` ≈ −420 mV, ~22:40 UTC), 46 `saludable` (1454–1516 mV). Ninguna `marchita`: T entre 18,6 y 20,6 °C.
- **Coincidencia con la condición que mandó la placa: 104/150.** Las 46 que no coinciden son las posteriores al riego, donde la placa seguía mandando `estresada` propagada (ep. 14, dudoso).
- Ejemplo de línea:

  ```
  [INF] n=105 warmup=0 x=[1516,-420,20.6,53,1.14,1792,1522] -> saludable p=[0.45,0.28,0.27] t_us=1
  ```

### Qué hace el LED

- **Con la temperatura de una habitación** (> 10,25 °C, todo octubre) manda la sonda:
  - **verde** con `suelo_mv` ≤ 1821,5 mV;
  - **amarillo** por encima.
  - **Rojo nunca**, por más seca que esté la sonda (3000–3124 mV da amarillo).
- **Con frío** (DHT11 ≤ 10,25 °C) el LED pasa a **rojo** con cualquier sonda.
- La humedad del aire, el VPD y la luz no cambian nada.
- **Para el demo:** mojar o secar la sonda alrededor de ~1820 mV cambia entre verde y amarillo; enfriar el DHT11 debajo de 10 °C lo pone en rojo. La pulsación larga fuerza una consulta sin esperar los 5 min.

## Figuras (`docs/entrega2/fig/`)

| archivo | qué muestra |
|---|---|
| `serie_maceta01_modelado.png` | La serie de modelado de `maceta-01`: `suelo_mv` por clase (filas a 5 min) y `temp_c`, con los huecos sin datos |
| `comparacion_modelos.png` | Exactitud bal., F1 macro y recall de marchita fuera de fold de los 3 baselines y los 7 candidatos (barra = sin dudosos ± desvío bootstrap; punto = todos) |
| `matrices_confusion_candidatos.png` | Matrices de confusión fuera de fold de los 10 modelos, todos los episodios |
| `rendimiento_vs_costo.png` | F1 macro fuera de fold sin dudosos contra la flash estimada (log), con el límite de 32 KB |
| `arbol_final.png` | El árbol de la placa (`arbol-p2-f012-58e644`), con sus cortes y proporciones por hoja |
| `modelo_final_suelo_mv.png` | El modelo de la placa como función de `suelo_mv` (ambientales en la mediana): probabilidad de cada clase y clase predicha |
| `matriz_confusion_final.png` | El modelo final fuera de fold: todos los episodios y sin dudosos |
| `modelo_final_sensibilidad.png` | Clase predicha y P(marchita) contra `suelo_mv` variando `temp_c`, con los suelos típicos de octubre marcados |
| `fronteras_suelo_mv.png` | Histogramas de `suelo_mv` por clase con el corte del modelo final |
| `clase_por_hora.png` | Proporción de clases por franja horaria local |
| `prueba_railway_nuevos.png` | Datos nuevos del 22/10: `suelo_mv` y clase predicha por el modelo final |

Las figuras `auditoria_*` (`auditoria_deriva_suelo.png`, `auditoria_suelo_por_clase_y_periodo.png`, `auditoria_luz_horaria.png`, `auditoria_hora_por_clase.png`) son de la auditoría de datos (`AUDITORIA_DATOS.md`).

## Hallazgos y limitaciones clave

1. **El N efectivo son los episodios.** El split aleatorio da 0,943 de exactitud balanceada y el split por episodio 0,135. Son 11 episodios (7 sin dudosos), y 1 o 2 deciden el orden entre modelos. Es el resultado principal de esta entrega.
2. **Rendimiento bajo y muy incierto.** Sin dudosos, el F1 macro del elegido es 0,282 ± 0,136, por debajo de los dos umbrales (0,393 ± 0,191), aunque dentro del ruido. Con todos los episodios, la exactitud balanceada es 0,200, por debajo del azar.
3. **No reconoce la marchita de octubre** (ep. 12, 1758 mV). La condición de seguridad (recall de marchita ≥ 0,9 y ep. 12 ≥ 50 %) no la cumple ninguna de las 66 configuraciones sin luz.
4. **La regla ambiental sale de un episodio.** "Frío (≤ 10,25 °C) → marchita" viene sólo del ep. 1. En octubre el modelo es un umbral único sobre la sonda.
5. **El criterio se completó después de ver resultados.** La compuerta de influencia, la condición de seguridad y la exclusión de la luz son decisiones de producto tomadas mirando los resultados.
6. **La hora del observador contamina la etiqueta.** Todas las marchitas se observaron de noche (V de Cramér 0,47). Con la luz, el modelo aprende "oscuro → marchita" (76–83 % de rojo en noches sanas).
7. **La sonda resistiva deriva.** El corte de 1821 mV vale para la escala de octubre y dejará de valer si la sonda sigue corriéndose. Hace falta la calibración semanal (`docs/CALIBRACION.md`).
8. **Conflicto 12/13 del 19/10.** Dos observaciones a pocas horas con la sonda casi igual y clases distintas. Sólo las fotos de la ESP32-CAM lo pueden resolver.
9. **El costo no es la restricción, los datos sí.** El árbol ocupa 81 B de los 32 KB de presupuesto y el firmware completo el 73,4 % de la flash.

## Mejoras posibles

- **Más episodios observados, sobre todo de día y en estados distintos**, con foto de la ESP32-CAM: es lo único que puede romper la confusión clase ↔ hora y dar más de una marchita por escala de sonda.
- **Resolver el 19/10 (ep. 12 vs. 13) con las fotos.**
- **Calibración semanal de la sonda** y una feature normalizada (o una sonda capacitiva): con la escala corregida, los umbrales de septiembre y octubre se podrían juntar.
- **Persistir las predicciones** en el backend (tabla `predicciones`) para evaluar el modelo en línea contra observaciones nuevas.
- **Flashear la placa** y medir `t_us` real en la ESP32.
