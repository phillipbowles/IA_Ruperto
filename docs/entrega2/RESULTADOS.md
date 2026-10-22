# Resultados de modelos — Tarea 2 (para el informe)

**FINAL, con la restricción de diseño "el semáforo no puede depender sólo de la sonda" y la condición de seguridad "no perder la marchita real" (2026-10-21).**

- **De dónde salen los números.** De la ejecución commiteada de `notebooks/03_modelos.ipynb` con el relleno simulado **v2** (`data/sintetico/payloads_relleno.jsonl`, 2026-10-21 23:58 UTC, la fecha de modificación de los archivos actuales de `data/sintetico/`). Todos están copiados de las salidas del notebook, que además reescribe las tablas en `docs/entrega2/tablas_03_modelos.md`.
- **Modelo de la placa:** Random Forest de 30 árboles con **`suelo_mv` y `vpd_kpa`** (`rf-f04-7734f6`).
- **Historia:**
  1. Sin restricción ganaba el RF sólo-suelo `rf-f0-c42286`.
  2. Con la restricción, el criterio pre-registrado elegía un Naive Bayes `suelo+temp` (`nb-f02-fa0df4`) que no reconocía la marchita real de octubre.
  3. La condición de seguridad, agregada **después de ver resultados**, lleva al modelo actual.

## Datos simulados

- **Qué es simulado.** Sólo los huecos de la serie real de `maceta-01`:

  | Hueco (UTC) | Duración |
  |---|---|
  | 13/09 11:54 → 15/09 12:28 | 48,6 h |
  | 15/09 15:34 → 16/09 15:37 | 24,1 h |
  | 17/09 00:09 → 17/09 18:01 | 17,9 h |
  | 17/09 18:59 → 21/09 23:56 | 101 h |
  | 22/09 → 01/10 | 216,5 h |
  | 01/10 15:12 → 02/10 00:50 | 9,6 h |
  | 02/10 03:04 → 02/10 11:13 | 8,1 h |
  | 02/10 15:41 → 03/10 12:36 | 20,9 h |
  | 03/10 20:35 → 18/10 23:31 | 362,9 h, la placa desenchufada |

  Hay además 3 cortes chicos (< 6 h) rellenados dentro del episodio real que los contiene. Las filas reales no se tocan. El relleno es local (`.gitignore`) y nunca se manda a Railway.
- **Cómo se calibró.** El simulador sigue la fracción de agua del sustrato θ, que se seca por evaporación y transpiración, con riegos. La clase sale de umbrales de θ. Los sensores se calibraron con lo medido:
  - Curva θ → mV de la sonda por fecha. Septiembre como en lo real. Octubre anclada en lo medido: marchita desde ~1745 mV, lo más seco ~1960 mV, recién regado ~1405 mV.
  - Riegos de 360–500 mV (el real medido fue de −418 mV) y deriva nocturna de la sonda.
  - Perfil horario de luz con las medianas reales; temperatura y HR del DHT11 cuantizadas como en lo real; un ciclo de radiador y uno de freezer.
  - Cada hueco empalma con la última y la primera muestra real.
- **Decisión de etiquetas.** Para la marchita de octubre se le creyó a la observación manual del ep. 12. El detalle está en `data/sintetico/README.md` y `docs/entrega2/AUDITORIA_DATOS.md`.
- **Las métricas principales se reportan sobre los episodios medidos** (`fuente == 'real'`): fuera de fold y en la transferencia simulado → real. Las de la serie completa (88 % simulada) se muestran sólo como referencia.

## Conteos

| | filas (5 min) | episodios | saludable | estresada | marchita |
|---|---|---|---|---|---|
| real (placa) | 1.321 | 11 | 423 filas / 3 ep. | 576 / 5 | 322 / 3 |
| relleno simulado | 9.730 | 45* | 5.178 / 10 | 2.112 / 20 | 2.440 / 15 |
| serie completa | 11.051 | 47 | 5.601 / 12 | 2.688 / 20 | 2.762 / 15 |

\* Incluye 9 episodios reales con filas simuladas en cortes chicos. Puramente simulados son 36.

- Proporción de filas: 50,7 % saludable, 24,3 % estresada y 25,0 % marchita.
- **Episodios dudosos: 8, 9, 11 y 14.** Sin dudosos quedan 7 reales: 1, 3, 6, 10, 12, 13 y 15.

## Protocolo

- `StratifiedGroupKFold` k=5 por `episodio_id`.
- Búsqueda anidada de hiperparámetros: interna k=3, también por episodio, con F1 macro. El subconjunto de features es un hiperparámetro.
- **Espacio de features restringido** (`modelos.SUBCONJUNTOS`, 22 subconjuntos): suelo + cada ambiental, suelo + delta + cada ambiental, suelo + cada par de ambientales, "sin luz" y "todas". `suelo_delta_1h` no cuenta como ambiental. Los baselines siguen usando sólo `suelo_mv`.
- **X sin metadatos de etiqueta.**
  - Antes de cualquier `fit`, el notebook arma `X` con `df.drop(columns=[...])`, descartando explícitamente la etiqueta en texto, `etiqueta_origen`, `dudoso`, `episodio_id`, `fuente`, `warmup`, `valido`, `post_boot`, `ts`, etc. Un `assert` exige que queden exactamente las 7 columnas del contrato §4, en orden.
  - El exportador usa el mismo resguardo (`modelos.matriz_X`, con test en `ml/tests/test_modelos.py`).
  - `episodio_id` se usa sólo como grupo de la partición; `fuente` y `dudoso`, sólo para evaluar.
- **Condición de seguridad y compuerta de influencia** (agregadas después de ver resultados; ver "Modelo elegido"): recall de marchita real ≥ 0,9 sin dudosos, ep. 12 ≥ 50 % fuera de fold, y la ambiental cambia ≥ 1 % de las predicciones reales. Se evalúan sobre 165 configuraciones fijas explícitas (`modelos.configuraciones_seguridad`).
- **Fuga** (Random Forest con 7 features, exactitud balanceada):

  | Datos | Partición aleatoria | Por episodio |
  |---|---|---|
  | Serie completa | 0,887 ± 0,009 | 0,681 ± 0,133 |
  | Sólo reales | 0,947 ± 0,012 | 0,291 ± 0,356 |

## Serie completa, CV por episodio (47 episodios; referencia, dominada por el simulador)

| modelo | exactitud bal. | F1 macro | recall marchita | ROC-AUC OvR |
|---|---|---|---|---|
| Clase mayoritaria (baseline) | 0,333 ± 0,000 | 0,232 ± 0,036 | 0,000 ± 0,000 | 0,500 ± 0,000 |
| Umbral único `suelo_mv` (baseline) | 0,601 ± 0,060 | 0,523 ± 0,058 | 0,823 ± 0,183 | 0,760 ± 0,089 |
| Dos umbrales `suelo_mv` (baseline) | **0,751 ± 0,118** | **0,749 ± 0,123** | 0,811 ± 0,184 | n/d |
| Regresión logística | 0,614 ± 0,142 | 0,606 ± 0,157 | 0,422 ± 0,266 | 0,834 ± 0,065 |
| Árbol de decisión | 0,728 ± 0,136 | 0,706 ± 0,183 | 0,775 ± 0,171 | 0,817 ± 0,090 |
| **Random Forest (tipo del elegido)** | 0,688 ± 0,123 | 0,664 ± 0,150 | 0,797 ± 0,181 | 0,820 ± 0,103 |
| Naive Bayes (criterio original) | 0,556 ± 0,110 | 0,534 ± 0,109 | 0,415 ± 0,282 | 0,771 ± 0,123 |
| k-NN | 0,671 ± 0,124 | 0,652 ± 0,144 | 0,687 ± 0,261 | 0,821 ± 0,085 |
| SVM RBF | 0,600 ± 0,163 | 0,601 ± 0,165 | 0,487 ± 0,233 | n/d |
| MLP | 0,625 ± 0,176 | 0,628 ± 0,174 | 0,457 ± 0,244 | 0,793 ± 0,091 |

- **Ningún candidato le gana al baseline de dos umbrales.** Con la restricción, el RF cae de 0,744 a 0,664 de F1.
- **Las búsquedas eligen subconjuntos distintos en cada fold** (luz media, luz, HR, T, VPD): ninguna ambiental se impone.
- Las filas son la búsqueda anidada de cada tipo. **La configuración final fija** (RF `suelo+vpd`, prof. 5, hoja 20) da exactitud bal. 0,728 ± 0,135, F1 0,720 ± 0,141, recall de marchita 0,733 ± 0,288 y AUC 0,808 ± 0,093.
- El Naive Bayes del criterio original (`suelo+temp`, fijo) da F1 0,589 ± 0,156.

## Costo estimado en la ESP32 (cada modelo reentrenado con toda la serie)

| modelo | config de la búsqueda sobre toda la serie | flash estimada (B, `costo_esp32`, parámetros en float) | RAM (B) | ops | exp | µs est. | exportable |
|---|---|---|---|---|---|---|---|
| Dos umbrales | suelo | 8 | 0 | 2 | 0 | 0,08 | sí (dos if) |
| Umbral único | suelo | 51 | 16 | 2 | 0 | 0,08 | sí |
| Regresión logística | suelo+delta+luz1h, C=0,01 | 72 | 24 | 33 | 3 | 4,4 | sí |
| Árbol | suelo+delta+luz1h, prof. 4, hoja 100 | 441 | 16 | 8 | 0 | 0,33 | sí |
| **Random Forest** | suelo+luz1h, prof. 5, hoja 100 (final: **suelo+vpd, prof. 5, hoja 20: 23.730 B**) | 17.790 | 28 | 390 | 0 | 16,3 | sí (tablas) |
| Naive Bayes | suelo+luz1h (criterio original: suelo+temp, mismo costo) | 60 | 12 | 27 | 3 | 4,1 | sí (fórmula cerrada) |
| k-NN | suelo+delta+luz1h, k=5 | 143.687 | 56 | 121.567 | 0 | 5.065 | guarda todo el train |
| SVM RBF | suelo+delta+luz1h, C=1 | 117.956 | 28 | 76.654 | 5.896 | 9.090 | guarda los vectores soporte |
| MLP | suelo+delta+luz1h, (8,) | 260 | 64 | 124 | 3 | 8,2 | sí |

- **El modelo final** (`rf-f04-7734f6`, 1570 nodos y 800 hojas) ocupa:
  - 23.730 B estimados (`costo_esp32`);
  - **23.790 B en las tablas del header exportado** (60 B más por el arreglo de raíces de los 30 árboles), el 73 % del límite de 32 KB.

  Hace ~390 operaciones, ~16 µs estimados.
- **El Naive Bayes del criterio original** (`suelo+temp`): 60 B estimados con parámetros en float. Exportado ocupa **122 B**, porque el header guarda 15 `double` + 2 índices para que la paridad con sklearn sea exacta.
- **Paridad Python ↔ C del modelo final.** `firmware/test/test_modelo/vectores.h` tiene **5.208 vectores**: filas de la serie y, para cada umbral de los árboles, casos en el umbral y en el float32 inmediatamente arriba y abajo. `pio test -e native` exige 100 % de coincidencia de clase y probabilidades a ±2e-3. También pasan las 142 muestras de paridad de features (137 con vector, 6 reinicios).
- **Medido en el host.** El replay da `t_us` de 0–2 µs (26 µs en la primera llamada). Falta medir en la placa (M1).
- **`pio run`.** Flash 75,2 % (986.097 B) y RAM 14,6 % (47.740 B) del firmware completo. Con el RF sólo-suelo era 75,3 %; con el Naive Bayes, 73,5 %.

## Control con datos reales (filas reales agrupadas)

Exactitud balanceada (F1 macro entre paréntesis). Búsqueda anidada de cada tipo, en el espacio restringido. La configuración final fija está en la tabla de "Restricción de diseño".

| modelo | reales fuera de fold | ídem sin dudosos | sim → real | ídem sin dudosos | sólo reales | ídem sin dudosos |
|---|---|---|---|---|---|---|
| Clase mayoritaria | 0,333 (0,162) | 0,333 (0,213) | 0,333 (0,162) | 0,333 (0,213) | 0,092 (0,072) | 0,232 (0,106) |
| Umbral único | 0,534 (0,388) | 0,664 (0,550) | 0,442 (0,351) | 0,664 (0,557) | 0,144 (0,130) | 0,212 (0,225) |
| Dos umbrales | 0,536 (0,389) | 0,666 (0,551) | 0,536 (0,389) | 0,666 (0,551) | 0,314 (0,320) | 0,495 (0,479) |
| Regresión logística | 0,452 (0,374) | 0,575 (0,564) | 0,433 (0,365) | 0,549 (0,539) | 0,311 (0,313) | 0,534 (0,488) |
| Árbol | 0,411 (0,328) | 0,561 (0,502) | 0,532 (0,386) | 0,654 (0,542) | 0,202 (0,195) | 0,371 (0,299) |
| Random Forest | 0,408 (0,329) | 0,546 (0,483) | 0,436 (0,323) | 0,544 (0,462) | 0,089 (0,082) | 0,143 (0,115) |
| Naive Bayes | 0,524 (0,476) | 0,731 (0,731) | 0,488 (0,416) | 0,641 (0,634) | 0,219 (0,205) | 0,407 (0,335) |
| k-NN | 0,413 (0,332) | 0,537 (0,481) | 0,556 (0,436) | 0,717 (0,654) | 0,104 (0,089) | 0,159 (0,141) |
| SVM RBF | 0,414 (0,370) | 0,575 (0,571) | 0,415 (0,331) | 0,542 (0,499) | 0,164 (0,144) | 0,238 (0,224) |
| MLP | 0,460 (0,363) | 0,570 (0,540) | 0,489 (0,365) | 0,602 (0,514) | 0,166 (0,176) | 0,232 (0,175) |

Cómo se arma cada columna:

- **Reales fuera de fold**: predicciones de la CV de la serie completa, restringidas a las filas reales.
- **sim → real** (transferencia): entrenado con los 36 episodios puramente simulados (9.228 filas), evaluado en todas las filas reales.
- **Sólo reales**: el mismo protocolo con los 11 episodios reales nada más.

- La búsqueda anidada del RF elige por F1 de la serie y queda última sobre lo real. La configuración fija de la condición de seguridad da 0,557 / 0,723 fuera de fold.
- El recall de marchita real del Naive Bayes es 0,407 (0,604 sin dudosos). El del modelo final y el de los dos umbrales es 0,674 (1,000 sin dudosos).

### Sensibilidad al ep. 13 (conflicto del 19/10)

- **El conflicto.**
  - Ep. 12: marchita, pulsación de noche con 1756 mV.
  - Ep. 13: estresada, pulsación a la mañana con 1796 mV; la mediana de 1930 mV sale de ~11 h propagadas sobre un sustrato más seco.
  - Ninguna regla monótona sobre `suelo_mv` respeta las dos. El relleno v2 se calibró creyéndole al 12, y la condición de seguridad también le da prioridad al 12.
- **Por qué el 13 no se marca dudoso.** Sería circular; se reporta la sensibilidad.

| Exactitud balanceada (configuraciones fijas) | todos | sin dudosos | sin el 13 | sin dudosos ni el 13 |
|---|---|---|---|---|
| **Final `rf-f04-7734f6`, reales fuera de fold** | 0,557 | 0,723 | 0,565 | 0,809 |
| **Final, sim → real** | 0,556 | 0,720 | 0,563 | 0,802 |
| Naive Bayes `nb-f02-fa0df4`, reales fuera de fold | 0,529 | 0,741 | 0,451 | 0,555 |
| Sólo suelo `rf-f0-c42286`, reales fuera de fold | 0,487 | 0,644 | 0,494 | 0,724 |
| Dos umbrales | 0,536 | 0,666 | 0,536 | 0,666 |

### Modelo final por episodio real (proporción de filas bien clasificadas, configuración fija)

| ep. | clase | dudoso | mediana `suelo_mv` | fuera de fold | sim → real |
|---|---|---|---|---|---|
| 1 | marchita | | 2832 | 1,00 | 1,00 |
| 3 | estresada | | 2770 | 0,00 | 0,00 |
| 6 | estresada | | 2050 | 0,58 | 0,55 |
| 8 | marchita | sí | 1512 | 0,00 | 0,00 |
| 9 | estresada | sí | 1454 | 0,00 | 0,00 |
| 10 | saludable | | 1504 | 0,98 | 0,98 |
| 11 | saludable | sí | 1786 | 0,00 | 0,00 |
| 12 | marchita | | 1758 | **1,00** | **1,00** |
| 13 | estresada | | 1930 | 0,00 | 0,00 |
| 14 | estresada | sí | 1444 | 0,00 | 0,00 |
| 15 | saludable | | 1453 | 1,00 | 1,00 |

Hay 5 de 7 episodios no dudosos con más de la mitad de las filas bien (el Naive Bayes, 4 de 7). Falla el 3 (radiador, sustrato de marchita) y el 13.

## Modelo elegido y justificación

- **Modelo:** Random Forest, 30 árboles, `max_depth=5`, `min_samples_leaf=20`, `class_weight="balanced"`, con **`suelo_mv` y `vpd_kpa`**.
- **Versión:** `PLANTAIA_MODELO_VERSION = "rf-f04-7734f6"`.
- **Cabecera de `modelo_plantaia.h`.** Reporta primero las métricas de la **configuración final fija**: F1 de la serie 0,720 ± 0,141; exactitud bal. de reales fuera de fold 0,557, y 0,723 sin dudosos. En líneas aparte, rotuladas "búsqueda anidada del tipo Random Forest", van las de la tabla por tipo (0,664 ± 0,150; 0,408 / 0,546).
- **Qué hace.** Con el VPD en la mediana (~1,2 kPa, el aire de octubre) es la misma función escalonada de la sonda que el sólo-suelo:

  | `suelo_mv` (mV) | clase |
  |---|---|
  | < 1639 | saludable |
  | 1639–1740 | estresada |
  | 1740–1845 | marchita (octubre, ep. 12) |
  | 1845–2096 | estresada (septiembre, ep. 13) |
  | > 2096 | marchita |

  No es monótona: superpone las escalas de septiembre y octubre de la sonda. El VPD corre esos cortes (ver "Qué hace el LED").
- **Sonda fuera del rango real**, con el aire de octubre: 900–1140 mV (más mojada que cualquier lectura) → `saludable` 100 %; 3000–3124 mV → `marchita` 100 %.

### Paso 1: criterio original (§5.3, pre-registrado) en el espacio restringido

1. **Restricciones duras:** quedan afuera k-NN y SVM.
2. **Serie completa.** Mejor F1 el árbol, 0,706 ± 0,183 → piso 0,524. Pasan regresión logística, árbol, RF, Naive Bayes y MLP.
3. **Real.** Mejor puntaje Naive Bayes, 0,682 (desvío bootstrap 0,154) → piso 0,528. Pasa también la regresión logística.
4. **Desempate:** Naive Bayes.
5. **Compuerta de influencia** (≥ 1 % de filas reales cambian si la ambiental va a su mediana; **agregada después de ver resultados**): deja afuera `suelo+luz1h` (0,98 %), `suelo+luz` (0,98 %) y `suelo+hr` (0,91 %).

**Resultado: Naive Bayes `suelo+temp`** (`nb-f02-fa0df4`). Tiene tres problemas:

- **pierde la marchita real de octubre**: ep. 12 0 %, recall de marchita real 0,60 sin dudosos;
- da `marchita` con la sonda muy mojada (99 % entre 900 y 1140 mV), un artefacto de las gaussianas;
- su efecto de temperatura ("frío o calor → rojo") sólo cambia el ep. 6, y para peor.

### Paso 2: condición de seguridad (agregada después de ver el paso 1)

- **Por qué.** Decisión de producto: el error caro es no avisar marchita (`docs/ENTREGA2.md` §5.1).
- **La condición** (`modelos.py`), sobre las filas reales fuera de fold y sin dudosos:
  - recall de `marchita` ≥ 0,9, y
  - el ep. 12 con ≥ 50 % de filas bien.
- **La grilla** (`configuraciones_seguridad`): 165 configuraciones fijas. Son suelo + cada ambiental y suelo + cada par de ambientales, con:
  - regresión logística (C 0,01 / 0,1 / 1);
  - árbol (prof. 2 / 3 / 4, hoja 100);
  - RF de 30 árboles (prof. 3 / 5, hoja 20 / 100);
  - Naive Bayes.
- **Filtros:** costo → influencia ≥ 1 % → seguridad. Entre las que pasan, el criterio de §5.3 como antes:
  - F1 de la serie dentro de 1 desvío de la mejor;
  - puntaje real dentro de 1 desvío bootstrap del mejor;
  - desempate por interpretabilidad, después menos features, después puntaje real.

**Tabla de candidatos con la condición de seguridad:**

| tipo | configuraciones | pasan seguridad | pasan costo + influencia | pasan las tres | mejor recall marchita real s/d | mejor acierto ep. 12 |
|---|---|---|---|---|---|---|
| Regresión logística | 45 | 0 | 42 | 0 | 0,604 | 0,00 |
| Naive Bayes | 15 | 0 | 12 | 0 | 0,604 | 0,00 |
| Árbol (prof. 2–4) | 45 | 35 | 0 | 0 | 1,000 | 1,00 |
| Random Forest chico | 60 | 54 | 40 | **36** | 1,000 | 1,00 |

- **Regresión logística y Naive Bayes no pueden cumplir.** Su frontera es monótona (o casi) en la sonda, y la marchita real de octubre (1758 mV) está debajo de la estresada de septiembre (2050 mV) y del ep. 13 (1930 mV). Ninguno acierta una sola fila del ep. 12.
- La mejor regresión logística (`suelo+temp+vpd`, C=1) tiene puntaje real 0,574, sin el artefacto de la sonda mojada, pero recall de marchita 0,60.
- **Los árboles** que cumplen la seguridad no usan la ambiental: como mucho cambian 0,98 % de las filas reales.
- **Entre los 36 RF:**
  - Mejor F1 de la serie: `suelo+vpd` prof. 3, hoja 20 (0,755 ± 0,121) → piso 0,634; pasan los 36.
  - Mejor puntaje real: `suelo+hr+vpd` prof. 3, hoja 100 (0,682), con desvío bootstrap 0,048 → piso 0,634; pasan 14.
  - Desempate. Todos tienen interpretabilidad 3; con 2 features quedan:

  | config | F1 serie | puntaje real | % reales que cambian | flash estimada |
  |---|---|---|---|---|
  | **suelo+vpd, prof. 5, hoja 20** | 0,720 ± 0,141 | **0,661** | 2,5 % | 23.730 B |
  | suelo+temp, prof. 5, hoja 20 | 0,692 ± 0,144 | 0,660 | 11,1 % | 22.440 B |
  | suelo+temp, prof. 5, hoja 100 | 0,715 ± 0,133 | 0,656 | 9,2 % | 17.040 B |
  | suelo+vpd, prof. 5, hoja 100 | 0,747 ± 0,125 | 0,654 | 6,3 % | 18.180 B |
  | suelo+temp, prof. 3, hoja 100 | 0,729 ± 0,126 | 0,644 | 2,5 % | 6.720 B |
  | suelo+temp, prof. 3, hoja 20 | 0,752 ± 0,125 | 0,642 | 2,5 % | 6.930 B |
  | suelo+hr, prof. 5, hoja 100 | 0,738 ± 0,124 | 0,635 | 8,1 % | 18.390 B |

  **Gana `suelo+vpd`, prof. 5, hoja 20**, por 0,001 de puntaje sobre `suelo+temp`: un empate práctico.
- La tabla completa de las 165 está en `tablas_03_modelos.md`.

### Contra los baselines

| | F1 serie (config. fija) | puntaje real | exactitud bal. reales oof (todos / s/d / s/d ni 13) | recall marchita real s/d | flash |
|---|---|---|---|---|---|
| **RF `suelo+vpd` (elegido)** | 0,720 ± 0,141 | **0,661** | **0,557 / 0,723 / 0,809** | 1,000 | 23.730 B est. / 23.790 B exportados |
| Dos umbrales | **0,749 ± 0,123** | 0,551 | 0,536 / 0,666 / 0,666 | 1,000 | 8 B |
| Umbral único | 0,523 ± 0,058 | 0,553 | 0,534 / 0,664 / 0,664 | 1,000 | 51 B |
| Clase mayoritaria | 0,232 ± 0,036 | 0,213 | 0,333 / 0,333 / 0,333 | 0,000 | 4 B |

- **Contra los dos umbrales.** Empata en la serie (dentro del desvío) y gana sobre lo real en todas las columnas.
- Sigue siendo con 7 episodios no dudosos, y con condiciones elegidas después de mirar: es una ventaja frágil.

## Restricción de diseño: el semáforo no puede depender sólo de la sonda

### La decisión

- **El problema.** El modelo anterior (`rf-f0-c42286`) usaba **sólo `suelo_mv`**: el LED respondía únicamente a la sonda.
- **Por qué está mal como producto.**
  - La sonda es resistiva y deriva: la misma marchita marcaba ~2830 mV en septiembre y ~1758 mV en octubre.
  - La maceta tiene sensores de ambiente que el semáforo ignoraba.
- **La regla.** Todo candidato con selección de features usa `suelo_mv` + al menos una de `temp_c`, `hum_aire_pct`, `vpd_kpa`, `luz_mv`, `luz_media_1h` (`modelos.cumple_restriccion`). `suelo_delta_1h` no cuenta.
- **Es una decisión de producto tomada después de ver los resultados** (el criterio pre-registrado elegía el RF sólo-suelo; ver la historia de pasos 1→2). No es un resultado del análisis. Los baselines siguen siendo sólo-suelo, como referencia.

### Declaración honesta

- **(a) Agregados después de ver resultados.** La compuerta de influencia (≥ 1 %) y la condición de seguridad (recall de marchita real ≥ 0,9, ep. 12 ≥ 50 %) **no estaban en el criterio pre-registrado de §5.3**. Se agregaron después de ver que ese criterio elegía un Naive Bayes que no avisaba la marchita de octubre, por decisión de producto: el error caro es no avisar marchita (`ENTREGA2.md` §5.1).
  - Elegir con reglas puestas después de mirar hace que los números del elegido sobre lo real sean **optimistas**.
  - Por eso se reportan también el Naive Bayes del criterio original y el sólo-suelo.
- **(b) Qué parte de la influencia ambiental es medida y qué parte es del simulador.**
  - ~88 % del entrenamiento es simulado. En el simulador la clase depende del ambiente **por reglas escritas a mano**: marchitez transitoria cuando la demanda (luz × VPD) supera lo que da el sustrato, secado más rápido con VPD alto, radiador y freezer. La dirección "aire más seco → más grave" que aprende el RF viene de ahí.
  - **Lo medido** que la respalda es un solo episodio, el ep. 6 de septiembre. El modelo entrenado **sólo con simulado** usa el VPD para pasar 38 filas del ep. 6 de mal a bien: con VPD bajo dice estresada en vez de marchita.
  - **Lo medido** que la contradice: en el modelo de la placa el VPD cambia 16 filas del ep. 13 de bien a mal.
  - El resto del efecto (aire seco → rojo antes, aire húmedo → amarillo en la banda de octubre) no tiene ningún episodio real que lo pruebe.

### Sólo-suelo vs. criterio original vs. nuevo vs. dos umbrales, sobre los episodios REALES

Configuraciones fijas, mismos folds. El sólo-suelo reentrenado en el notebook da exactamente `rf-f0-c42286`.

| exactitud balanceada (F1 macro) | todos | sin dudosos | sin el 13 | sin dudosos ni el 13 |
|---|---|---|---|---|
| sólo suelo `rf-f0-c42286`, reales fuera de fold | 0,487 (0,399) | 0,644 (0,591) | 0,494 (0,449) | 0,724 (0,698) |
| criterio original NB `nb-f02-fa0df4`, reales fuera de fold | 0,529 (0,483) | **0,741 (0,741)** | 0,451 (0,376) | 0,555 (0,556) |
| **nuevo `rf-f04-7734f6`, reales fuera de fold** | **0,557** (0,442) | 0,723 (0,663) | **0,565 (0,497)** | **0,809 (0,827)** |
| dos umbrales, reales fuera de fold | 0,536 (0,389) | 0,666 (0,551) | 0,536 (0,427) | 0,666 (0,608) |
| sólo suelo, sim → real | **0,557** (0,439) | 0,717 (0,655) | **0,563 (0,492)** | 0,797 (0,814) |
| criterio original NB, sim → real | 0,523 (0,476) | **0,730 (0,730)** | 0,445 (0,366) | 0,531 (0,530) |
| **nuevo, sim → real** | 0,556 (0,439) | 0,720 (0,658) | **0,563 (0,492)** | **0,802 (0,819)** |
| dos umbrales, sim → real | 0,536 (0,389) | 0,666 (0,551) | 0,536 (0,427) | 0,666 (0,608) |

| | sólo suelo | criterio original NB | **nuevo** | dos umbrales |
|---|---|---|---|---|
| recall marchita real (todos / s/d), oof y sim → real | 0,677 / 1,000 | 0,407 / 0,604 | **0,674 / 1,000** | 0,674 / 1,000 |
| ep. 12 fuera de fold | 1,00 | **0,00** | 1,00 | 1,00 |
| puntaje real (config. fija) | 0,623 | 0,736 | 0,661 | 0,551 |
| F1 serie (CV, config. fija) | 0,715 ± 0,112 | 0,589 ± 0,156 | 0,720 ± 0,141 | 0,749 ± 0,123 |
| flash estimada (`costo_esp32`, float) | 24.600 B | 60 B | 23.730 B | 8 B |
| flash del header exportado (tablas) | 24.660 B | 122 B (`double`) | 23.790 B | no se exporta |
| features | suelo | suelo, temp | suelo, vpd | suelo |

- **Ejecución anterior**, tal como estaba en este archivo, con la búsqueda anidada del RF sin restricción: F1 de la serie 0,744 ± 0,119, puntaje real 0,589; exactitud bal. de reales fuera de fold 0,494 / 0,644; sim → real 0,531 / 0,657.
- **Nuevo vs. sólo suelo.**
  - Puntaje real +0,038, y gana en el 100 % de las remuestras del bootstrap (desvío de la diferencia 0,019). Fallan y aciertan casi los mismos episodios; el nuevo acierta más filas del ep. 6.
  - En la serie empatan (+0,005 de F1 por fold de media).
  - Sim → real prácticamente igual.
- **Lo que cuesta la restricción con la seguridad:** casi nada sobre lo medido, y ~900 B menos de flash. **Lo que gana:** poco, y respaldado por un episodio.
- **El Naive Bayes del criterio original** gana en "sin dudosos" sólo por acertar el ep. 13, a cambio de perder la marchita del 12.

### Verificación de que la ambiental influye (filas medidas)

- **Importancia por permutación** (1.321 filas reales, 30 permutaciones):

  | modelo | feature | caída exactitud bal. | % predicciones que cambian |
  |---|---|---|---|
  | final | `suelo_mv` | 0,300 ± 0,010 | 51,3 % |
  | final | `vpd_kpa` | 0,021 ± 0,004 | 5,3 % |
  | sim → real | `suelo_mv` | 0,241 ± 0,010 | 48,3 % |
  | sim → real | `vpd_kpa` | 0,026 ± 0,005 | 8,2 % |

- **`vpd_kpa` reemplazado por su mediana.**
  - El modelo de la placa cambia la clase de **2,50 % de las filas reales** (33 filas, todas de día): cumple el umbral de 1 %.
    - Ep. 6: 17 filas; con VPD 82 % bien, sin VPD 18 %.
    - Ep. 13: 16 filas; con VPD 0 %, sin VPD 100 %.
  - El modelo entrenado sólo con simulado cambia 2,88 % (38 filas, todas del ep. 6, todas de mal a bien).
- **Barrido**: `suelo_mv` fijo en valores medidos de octubre, VPD entre 0,40 y 4,15 kPa (percentiles 1–99 real), el resto en la mediana real de octubre. Cambia la clase en los 4 suelos.
  - **En el rango real de octubre (0,76–1,45 kPa):**
    - 1480 y 1619 mV → siempre saludable;
    - 1758 mV → siempre marchita;
    - entre ~1850 y ~2050 mV → estresada en ~70 % del rango y marchita en ~30 % (RF dentado).
  - **Aire seco (VPD ≈ 2 kPa):** todo lo que está arriba de ~1735 mV es marchita (desaparece la banda estresada 1845–2096).
  - **Aire húmedo (VPD ≈ 0,6 kPa):** la banda marchita de octubre (1740–1845 mV) pasa a estresada; marchita recién desde ~2127 mV.
  - **VPD muy bajo (< 0,47 kPa, frío y húmedo como el ep. 1 de septiembre):** vuelve a marchita desde ~1600 mV. Es el frío de ese episodio, no un efecto botánico.
- **¿Proxy de la hora?** V de Cramér con la franja de 3 h, filas reales:

  | | V |
  |---|---|
  | clase real | 0,466 |
  | predicción sólo suelo | 0,388 |
  | predicción criterio original (NB) | 0,150 |
  | **predicción nueva** | **0,382** |
  | predicción nueva con el VPD en la mediana | 0,389 |
  | `vpd_kpa` en terciles | 0,412 |

  - El VPD está asociado a la hora, pero no la mete en el modelo: la asociación de la predicción con la franja es la misma con y sin VPD.
  - A sustrato fijo, con el aire real de octubre, la predicción no cambia entre día y noche.
  - El ep. 12 (marchita nocturna) se acierta por la sonda: sacarle el VPD no cambia ninguna de sus filas.
  - La luz no entra al modelo.

### Qué hace el LED ahora

- **Con el aire normal de una habitación** (VPD ~0,8–1,5 kPa, todo octubre) manda la sonda:
  - verde hasta ~1640 mV;
  - amarillo ~1640–1740;
  - rojo ~1740–1845;
  - amarillo ~1845–2100, con tramos rojos (zona dentada: ~70 % estresada, ~30 % marchita en el barrido con VPD de 0,76–1,45 kPa);
  - rojo desde ~2100 mV.
- **Aire seco y caliente** (por ejemplo un secador apuntando al DHT11, VPD ≳ 2 kPa): con la sonda arriba de ~1735 mV el LED pasa a **rojo** aunque estuviera en amarillo (zona 1850–2100 mV).
- **Aire húmedo** (aliento sobre el DHT11, VPD ≈ 0,6): con la sonda en ~1740–1845 mV el LED baja de **rojo a amarillo**.
- **Con la sonda en zona húmeda** (< ~1640 mV) el aire no cambia nada en el rango normal: verde. Mojar la sonda de más (< 1140 mV) también da verde.
- **Para el demo:** primero llevar la sonda a la zona media-seca, después cambiar el aire. El efecto del aire es chico y en la mayoría de los suelos no se ve.

## Binario secundario (requiere cuidado = estresada ∪ marchita)

| modelo | exactitud bal. serie | F1 cuidado serie | ROC-AUC serie | exactitud bal. reales oof s/d | exactitud bal. sim→real s/d |
|---|---|---|---|---|---|
| Clase mayoritaria | 0,500 ± 0,000 | 0,061 ± 0,122 | 0,500 ± 0,000 | 0,097 | 0,500 |
| Umbral único | 0,879 ± 0,073 | 0,859 ± 0,093 | 0,879 ± 0,073 | 0,996 | 0,996 |
| Árbol | 0,845 ± 0,076 | 0,785 ± 0,163 | 0,878 ± 0,100 | 0,784 | 0,981 |
| Regresión logística | 0,873 ± 0,056 | 0,845 ± 0,093 | 0,899 ± 0,065 | 0,966 | 0,962 |
| Naive Bayes | 0,823 ± 0,126 | 0,811 ± 0,117 | 0,850 ± 0,135 | 1,000 | 1,000 |

- Mismos folds que el análisis de 3 clases. Los candidatos usan el espacio restringido.
- "Seco / no seco" se resuelve casi perfecto sobre los 7 episodios reales no dudosos con un solo umbral sobre la sonda. Lo difícil es separar estresada de marchita.

## Figuras (`docs/entrega2/fig/`)

| archivo | qué muestra |
|---|---|
| `serie_maceta01_modelado.png` | La serie de modelado: `suelo_mv` por clase (real opaco, relleno tenue), T y qué fuente cubre cada tramo |
| `comparacion_modelos.png` | Exactitud bal., F1 macro y recall de marchita (media ± desvío y cada fold) de los 3 baselines y los 7 candidatos, serie completa |
| `matrices_confusion_candidatos.png` | Matrices de confusión fuera de fold de los 10 modelos (serie completa) |
| `rendimiento_vs_costo.png` | F1 de la serie y puntaje real contra la flash estimada (log), con el límite de 32 KB (criterio original por tipo) |
| `modelo_final_sensibilidad.png` | **Nueva.** Clase predicha y P(marchita) del modelo final contra `suelo_mv`, para `vpd_kpa` en los percentiles 5, 50 y 99 de lo real (0,43, 1,21 y 4,15 kPa), con los suelos típicos de octubre marcados |
| `modelo_final_suelo_mv.png` | El modelo de la placa como función de `suelo_mv` con el VPD en la mediana de la serie: probabilidad de cada clase y clase predicha (la usa el informe) |
| `matriz_confusion_final.png` | El modelo final: serie completa fuera de fold, reales fuera de fold y reales entrenando sólo con simulado |
| `control_reales.png` | Exactitud bal. por modelo (búsqueda anidada): serie completa, reales oof (con y sin dudosos), sim→real (con y sin dudosos), sólo reales |
| `fronteras_suelo_mv.png` | Histogramas de `suelo_mv` por clase (relleno y real) con los cambios de clase del modelo final (VPD en la mediana) |
| `clase_por_hora.png` | Proporción de clases por franja horaria, real vs. relleno |
| `maceta01_completada.png` | La serie completada; la genera `plantaia_ml.relleno`, no el notebook |

Las figuras `auditoria_*` son de la auditoría de datos.

## Hallazgos y limitaciones clave

1. **El N efectivo son los episodios.**
   - El split aleatorio da 0,887 y el split por episodio 0,681 (en los reales, 0,947 contra 0,291).
   - Hay 11 episodios reales, 7 sin dudosos: el orden entre modelos sobre lo real lo deciden 1 o 2 episodios.
   - Entrenando sólo con reales nada generaliza.
2. **El criterio final se completó después de ver resultados.** La compuerta de influencia y la condición de seguridad son decisiones de producto posteriores; los números del elegido sobre lo real son optimistas. Sin ellas, el criterio pre-registrado elegía un Naive Bayes que no avisaba la marchita de octubre.
3. **La restricción de diseño se cumple, con un efecto ambiental chico y poco respaldado.**
   - El VPD cambia 2,5 % de las predicciones reales.
   - Lo respalda un episodio medido (el 6) y lo contradice otro (el 13). El resto sale de las reglas del simulador.
4. **Contra los baselines:** empata en la serie con los dos umbrales y gana sobre lo real (puntaje 0,661 contra 0,551), con la fragilidad de 1 y 2.
5. **La sonda resistiva deriva.** La regla superpone las escalas de septiembre y octubre y dejará de valer si la sonda sigue corriéndose. Hace falta la calibración semanal (`docs/CALIBRACION.md`).
6. **Conflicto 12/13 del 19/10.** El modelo final le cree al 12 (avisa la marchita) y falla el 13. Sólo las fotos de la ESP32-CAM lo pueden resolver.
7. **Hora del día.** V de Cramér franja × clase: 0,47 en lo real, 0,10 en el relleno v2. El modelo no usa la luz, y el VPD no agrega asociación con la hora (0,38 con y sin VPD).
8. **El costo no es la restricción, los datos sí.** El RF ocupa el 72 % del presupuesto de 32 KB; un baseline de dos umbrales ocuparía 8 B.
