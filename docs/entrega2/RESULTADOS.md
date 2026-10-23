# Resultados de modelos — Tarea 2 (para el informe)

**Versión con el snapshot de Railway del 23/10 (suma el tramo del 03/10 al 18/10), sólo datos medidos, con la restricción de diseño "el semáforo no puede depender sólo de la sonda" (2026-10-23).**

- **De dónde salen los números.** De la ejecución commiteada de `notebooks/03_modelos.ipynb` sobre `data/mediciones_raw_2026-10-23.csv`. Todos están copiados de las salidas del notebook, que además reescribe las tablas en `docs/entrega2/tablas_03_modelos.md` (generado, no se edita).
- **Modelo de la placa:** árbol de decisión de profundidad 3 con **`suelo_mv` y `hum_aire_pct`** (`arbol-p3-f03-ee3419`). Tres cortes sobre la sonda y un ajuste por aire muy seco.
- **En una línea:** con 24 episodios (20 sin dudosos) los modelos sí generalizan por episodio (F1 macro ~0,7–0,8), pero la regla de dos umbrales sobre `suelo_mv` sigue siendo la mejor, y la condición de seguridad sigue sin cumplirla nadie.
- **Qué cambió respecto de la versión anterior** (snapshot del 21/10, 11 episodios, modelo `arbol-p2-f012-58e644`): entran los 13 episodios del 03/10 al 18/10, que antes era un hueco. El F1 macro del mejor candidato pasa de 0,32 a 0,78, la fuga del split aleatorio baja de 0,94 vs 0,14 a 0,97 vs 0,65, y la asociación clase ~ hora del día baja de 0,47 a 0,24. Los números de la versión anterior quedan en el historial de git de este archivo.

## Datos

- **Sólo lo medido.** La serie de `maceta-01` remuestreada a 5 min (mediana por bin), cruzada con los episodios de `data/episodios.csv`. Es una sola maceta: las filas del 03/10 al 18/10 quedaron en la base con el identificador `maceta-02` por error y se unifican al leer (`datos_reales.unificar_maceta`). Los días sin registro quedan como huecos: no se completan ni se interpolan.
- **Filtros** (`dataset.serie_maceta01()`): fuera los primeros 60 min tras cada arranque (transitorio de la sonda), la sonda saturada, las filas sin vector completo y las que no caen en ningún episodio. Las features se calculan antes de filtrar, como las calcularía la placa.
- **Dónde hay dato.** 13–17/09 y del 01/10 al 21/10 (el tramo del 03/10 al 18/10, sin cortes largos).
- **Episodios perdidos.** El corte de 60 min elimina enteros los ep. 2, 4, 5 y 7 (`AUDITORIA_DATOS.md`, H7).
- **Del 03/10 al 18/10**: tres ciclos de ~5 días (saludable → estresada → marchita de día → riego → estresada de recuperación → saludable), 13 episodios `manual`, ninguno dudoso. Detalle en `data/README.md`.

### Conteos

| | filas (5 min) | episodios | saludable | estresada | marchita |
|---|---|---|---|---|---|
| todos | 5.663 | 24 | 2.452 filas / 7 ep. | 2.446 / 11 | 765 / 6 |
| sin dudosos | 5.171 | 20 | 2.425 / 6 | 2.092 / 9 | 654 / 5 |
| septiembre y 01–03/10, 19–21/10 | 1.357 | 11 | | | |
| 03/10 → 18/10 | 4.306 | 13 | | | |

Proporción de filas: 43 % saludable, 43 % estresada, 14 % marchita. Episodios dudosos: 8, 9, 11 y 14 (motivo en la nota de cada uno).

### Medianas por clase (sin dudosos)

| | saludable | estresada | marchita |
|---|---|---|---|
| `suelo_mv` | 1549 | 1852 | 1956 |
| `temp_c` | 20,2 | 19,9 | 20,2 |
| `hum_aire_pct` | 48 | 47 | 46 |
| `luz_mv` | 991 | 1189 | 747 |

La sonda **ordena** las clases (con el snapshot del 21/10 no las ordenaba con todos los episodios). T, HR y VPD casi no cambian entre clases: en octubre el ambiente fue estable.

## Protocolo

- **Partición externa por episodio**: `StratifiedGroupKFold` k=5 con `episodio_id` como grupo. Con 24 episodios cada fold de test tiene 4 o 5, y no siempre las tres clases.
- **Búsqueda anidada de hiperparámetros**: interna k=3, también por episodio, maximizando F1 macro. El subconjunto de features es un hiperparámetro más, **restringido** a `suelo_mv` + al menos una ambiental del aire (10 subconjuntos, ninguno con luz).
- **Métricas sobre las predicciones fuera de fold juntas**, con desvío por **bootstrap de episodios** (estratificado por clase, 500 remuestras). Exactitud balanceada (azar = 0,33), F1 macro, recall de `marchita` y ROC-AUC OvR cuando hay probabilidades.
- Cada métrica se reporta **con todos los episodios y sin los dudosos**. La selección usa "sin dudosos".
- **X sin metadatos de etiqueta** (`modelos.matriz_X` y el `assert` del notebook): exactamente las 7 columnas del contrato §4.
- **Fuga** (Random Forest con las 7 features, exactitud balanceada fuera de fold):

  | partición aleatoria (filas mezcladas) | por episodio |
  |---|---|
  | 0,968 | 0,646 |

## Baselines y candidatos, partición por episodio (§4 del notebook)

| modelo | F1 macro sin dudosos | exactitud bal. sin dudosos | recall marchita sin dudosos | F1 macro todos | ROC-AUC sin dudosos |
|---|---|---|---|---|---|
| Dos umbrales (`suelo_mv`) — baseline | **0,822 ± 0,060** | **0,818** | 0,713 | **0,751** | n/d |
| Árbol de decisión | 0,779 ± 0,054 | 0,792 | **0,731** | 0,711 | 0,834 |
| k-NN | 0,734 ± 0,058 | 0,739 | 0,555 | 0,688 | 0,864 |
| Random Forest | 0,692 ± 0,052 | 0,718 | 0,651 | 0,634 | **0,876** |
| SVM RBF | 0,628 ± 0,072 | 0,665 | 0,636 | 0,597 | n/d |
| MLP | 0,590 ± 0,074 | 0,589 | 0,217 | 0,540 | 0,742 |
| Regresión logística | 0,578 ± 0,053 | 0,594 | 0,433 | 0,529 | 0,786 |
| Umbral único (`suelo_mv`) — baseline | 0,461 ± 0,091 | 0,482 | 0,220 | 0,421 | 0,785 |
| Naive Bayes | 0,408 ± 0,072 | 0,401 | 0,000 | 0,371 | 0,653 |
| Clase mayoritaria — baseline | 0,128 ± 0,061 | 0,165 | 0,000 | 0,151 | 0,352 |

- **Ningún candidato le gana a los dos umbrales.** El árbol de la búsqueda pierde por 0,043 y gana sólo en el 4 % de las remuestras.
- Todos menos Naive Bayes le ganan al umbral único y a la clase mayoritaria.
- Las búsquedas eligen ambientales distintas en cada fold (HR, T, VPD).

## Costo estimado en la ESP32 (cada modelo reentrenado con todos los episodios)

| modelo | configuración | flash | ops | µs est. |
|---|---|---|---|---|
| Dos umbrales | `suelo` | 8 B | 2 | 0,1 |
| Árbol | `suelo+hr`, prof. 3, hoja 20 | 231 B | 6 | 0,3 |
| Regresión logística | `suelo+delta+temp`, C=1 | 72 B | 33 | 4,4 |
| Naive Bayes | `suelo+temp+hr` | 84 B | 39 | 4,6 |
| MLP | `suelo+delta+temp` | 932 B | 460 | 22 |
| Random Forest | `suelo+hr`, prof. 5, hoja 20 | 18,1 KB | 390 | 16 |
| SVM RBF | `suelo+hr+vpd`, C=1 | 56,9 KB | 37.862 | 4.490 |
| k-NN | `suelo+delta+vpd`, k=5 | 71,9 KB | 62.299 | 2.596 |

k-NN y SVM quedan afuera por flash (> 32 KB) y tiempo (> 1 ms).

## Sensibilidad a los dudosos y al ep. 13 (§5.2)

Sacar el ep. 13 (el conflicto con el 12 del 19/10) mueve las métricas menos de 0,01 en todos los modelos. Sacar los dudosos sube todo ~0,06–0,07.

## Modelo elegido y justificación

### Paso 1: criterio de §5.3 (pre-registrado) en el espacio restringido

Restricciones duras → fuera k-NN y SVM. Mejor puntaje: árbol 0,779, desvío bootstrap 0,054 → piso 0,725. **Sólo el árbol pasa.**

### Paso 2: configuración final (§5.5)

Las configuraciones de profundidad 2 con una ambiental no la usan (0 % de filas cambian con la ambiental en la mediana). La primera en orden de parsimonia que sí la usa es **`suelo+hr`, profundidad 3, hoja 20** (F1 interno 0,710 ± 0,110, la mejor de la búsqueda): 1,1 % de las filas cambian, apenas por encima de la compuerta del 1 %.

### Paso 3: condición de seguridad (§5.6) — nadie la cumple

Recall de marchita ≥ 0,9 sin dudosos **y** ep. 12 ≥ 50 %: 0 de 66 configuraciones. El recall máximo es 0,76 (RF) y **el ep. 12 no lo acierta ninguna**: con 1758 mV cae en la zona `estresada` de octubre (1720–1940 mV), que fijan los ciclos del 03/10 al 18/10. La condición no se relajó: queda la configuración del paso 2.

### El modelo: `arbol-p3-f03-ee3419`

| condición | clase |
|---|---|
| `suelo_mv` ≤ 1445,75 mV | estresada |
| 1445,75 < `suelo_mv` ≤ 1716,5 mV | saludable |
| 1716,5 < `suelo_mv` ≤ 1936,5 mV | estresada |
| `suelo_mv` > 1936,5 mV y `hum_aire_pct` ≤ 43,5 % | estresada |
| `suelo_mv` > 1936,5 mV y `hum_aire_pct` > 43,5 % | marchita |

- 15 nodos, 231 B de flash, a lo sumo 3 comparaciones.
- **Fuera de fold (configuración fija):** F1 macro 0,711 ± 0,053 sin dudosos (0,651 todos); exactitud balanceada 0,737 / 0,669; recall de marchita 0,690 / 0,590; ROC-AUC OvR 0,817 / 0,741.
- **Sonda fuera de rango:** muy mojada (900–1140 mV) → `estresada` 100 %; muy seca (3000–3124 mV) → `marchita` 100 %.
- La rama "≤ 1446 mV → estresada" sale del ep. 14 (dudoso, ~1445 mV) y de las recuperaciones post-riego: una planta recién regada con la sonda muy mojada prendería el amarillo.

### Contra los baselines (§5.4)

| | F1 sin dudosos | recall marchita | flash |
|---|---|---|---|
| árbol (búsqueda anidada) | 0,779 | 0,731 | 231 B |
| árbol (config. fija, la de la placa) | 0,711 | 0,690 | 231 B |
| dos umbrales | **0,822** | 0,713 | 8 B |
| umbral único | 0,461 | 0,220 | 51 B |

## Restricción de diseño: el semáforo no puede depender sólo de la sonda (§5.7)

### Qué cuesta la restricción (mismos folds, sin dudosos)

| modelo | F1 macro | recall marchita | ep. 12 |
|---|---|---|---|
| sólo suelo (RF, `rf-f0-532763`) | 0,678 | 0,517 | 0 % |
| **final (`arbol-p3-f03-ee3419`)** | 0,711 | 0,690 | 0 % |
| dos umbrales (baseline) | **0,822** | **0,713** | 0 % |

El final le gana al RF sólo-suelo (+0,033, en el 74 % de las remuestras) pero pierde contra los dos umbrales por 0,11.

### ¿Influye la humedad del aire? Poco, y sólo con aire muy seco

- **Permutación:** `hum_aire_pct` baja la exactitud balanceada 0,015 y cambia el 1,5 % de las predicciones; `suelo_mv` la baja 0,466.
- **HR en la mediana:** cambia el 1,1 % de las filas (65 filas): ep. 3 (radiador, HR ~23 %; 100 % de sus filas pasan a `estresada`, que es lo correcto), ep. 6 (46 %) y ep. 13 (5 %: 7 filas del 19/10 con la sonda en ~1940 mV y el aire en 41–43 %). Ninguna de noche.
- **Barrido con el suelo de octubre:** la HR no cambia la clase en ningún caso.
- **Proxy de la hora:** V de Cramér predicción ~ franja 0,13 (0,13 también con la HR en la mediana).

Con el ambiente típico de octubre el modelo es un umbral triple sobre la sonda; la HR sólo actúa con aire muy seco: el radiador de septiembre y la tarde del 19/10 (HR 41–43 %), donde demora el paso a rojo.

## Por qué la luz quedó afuera (§6.3)

Se decidió con la versión anterior, después de ver resultados: con el snapshot del 21/10 todas las marchitas eran nocturnas y las regresiones logísticas con luz marcaban `marchita` en el 76–83 % de las noches de una planta sana. Con los 24 episodios:

- la asociación clase ~ franja horaria baja a **0,24** (las marchitas del 03/10 al 18/10 son diurnas);
- las regresiones logísticas con luz ya **no pasan la condición de seguridad** (recall de marchita 0,55–0,65, F1 ≤ 0,62);
- en las noches de los datos sin etiqueta del 21–22/10 **ninguna predice `marchita`**.

La exclusión se mantiene, pero ya no le cuesta nada al modelo.

## Análisis de errores

### El modelo final por episodio (§6.1)

Más de la mitad de las filas bien fuera de fold en **13 de los 20 episodios no dudosos**.

- Fallan siempre las **recuperaciones post-riego** (eps. 19, 23, 27): `estresada` con el sustrato ya en ~1490–1520 mV → `saludable`.
- Falla el **ep. 12** (marchita a 1758 mV → `estresada`).
- Fallan el **6** (27 %), el **15** (33 %) y el **18** (marchita, 40 %): sin ese episodio en el train el corte se mueve.
- Fallan los cuatro dudosos.

Matriz de confusión fuera de fold sin dudosos: ninguna `saludable` → `marchita` y ninguna `marchita` → `saludable`. El error dominante es `estresada` ↔ vecinas (286 → saludable, 484 → marchita).

### La frontera sobre `suelo_mv` y la deriva de la sonda (§6.2)

Cortes en ~1446, ~1716 y ~1936 mV (HR en la mediana).

| clase | 13–17/09 | 01–03/10 | 03–18/10 | 19–21/10 |
|---|---|---|---|---|
| saludable | — | 1504 | 1570 | 1456 |
| estresada | 2064 | 1454 | 1837 | 1461 |
| marchita | 2832 | 1518 | 1954 | 1758 |

(medianas de `suelo_mv` en mV, con los dudosos). La misma condición lee ~900 mV distinto según el mes.

### Análisis secundario: binario *requiere cuidado* (§6.4)

Sin dudosos: umbral único 0,924 de exactitud balanceada (ROC-AUC 0,93), regresión logística 0,887, árbol 0,873 (ROC-AUC 0,93). Para decidir "regar o no", un corte sobre la sonda alcanza; lo difícil es separar `estresada` de `marchita`.

## Prueba con datos sin etiqueta de Railway (§6.5)

272 filas de 5 min (21/10 21:25 → 22/10 20:00 UTC) posteriores al ep. 15 y sin observación (la placa mandaba `saludable` propagada): el modelo final predice **`saludable` en el 100 %**, de día y de noche (sustrato 1496–1563 mV).

## Inferencia en tiempo real

### En la placa

El 22/10 se flasheó el firmware 2.0.0 con el modelo de la versión anterior (`arbol-p2-f012-58e644`): `docs/entrega2/logs/placa_2026-10-22*.txt`. Una inferencia medida **en la ESP32**: `t_us=33`. En la base quedan 9 filas con firmware 2.0.0, casi todas con la sonda saturada (fuera del sustrato) y `sin_prediccion`. **Falta flashear `arbol-p3-f03-ee3419`.**

### Replay en el host

`docs/entrega2/logs/replay_host.txt`, mismo código que la placa (`firmware/lib/plantaia_ml`), con el modelo nuevo.

- **Tramo:** desde el 19/10 14:00 UTC, 150 muestras de 5 min, que cruzan un riego.
- **150/150 inferencias**, 12 en warm-up, 0 con faltantes, `t_us` máximo 1 µs (host).
- **Predichas:** 48 `estresada` (sonda 1877–1944 mV; las últimas 7 ya arriba de 1936,5 mV pero con HR 41–43 %) → 27 `marchita` (la HR sube a 44–45 %) → 29 `estresada` (la sonda vuelve a 1936 mV) → desde el riego (`suelo_delta_1h` ≈ −420 mV, ~22:40 UTC) 46 `saludable`.
- **Coincidencia con la condición que mandó la placa: 77/150.**
- Ejemplo de línea:

  ```
  [INF] n=105 warmup=0 x=[1516,-420,20.6,53,1.14,1792,1522] -> saludable p=[0.82,0.08,0.10] t_us=1
  ```

### En el dashboard

La sección **Cómo decide el modelo de la placa** dibuja `arbol-p3-f03-ee3419` (`frontend/src/componentes/ArbolModelo.tsx`) y recorre el camino de la medición actual hasta la hoja. Los nodos salen de `frontend/src/modelo_placa.json`, que genera el exportador junto con el header: si se reentrena, el dibujo se actualiza solo. Si la placa reporta otra `modelo_version` en su última predicción, el pie lo avisa. Hoy ninguna medición trae predicción (las 9 filas con firmware 2.0.0 llegaron con `sin_prediccion`); cuando lleguen con `arbol-p2-f012-58e644` va a marcar que hay que reflashear.

### Qué hace el LED

- **Verde** con la sonda entre ~1446 y ~1716 mV.
- **Amarillo** entre ~1716 y ~1936 mV, y también por debajo de ~1446 mV (muy mojada).
- **Rojo** por encima de ~1936 mV, salvo que la HR del aire sea ≤ 43,5 % (entonces amarillo).
- La temperatura, el VPD y la luz no cambian nada.
- **Para el demo:** secar la sonda en el aire la lleva a rojo; mojarla un poco a verde; sumergirla del todo, a amarillo. La pulsación larga fuerza una consulta sin esperar los 5 min.

## Figuras (`docs/entrega2/fig/`)

| archivo | qué muestra |
|---|---|
| `serie_modelado.png` | La serie de modelado: `suelo_mv` por clase con el número de episodio y `temp_c` |
| `comparacion_modelos.png` | Exactitud bal., F1 macro y recall de marchita fuera de fold de los 3 baselines y los 7 candidatos |
| `matrices_confusion_candidatos.png` | Matrices de confusión fuera de fold de los 10 modelos, todos los episodios |
| `rendimiento_vs_costo.png` | F1 macro fuera de fold sin dudosos contra la flash estimada (log), con el límite de 32 KB |
| `arbol_final.png` | El árbol de la placa (`arbol-p3-f03-ee3419`) |
| `modelo_final_suelo_mv.png` | El modelo como función de `suelo_mv` (HR en la mediana): probabilidades y clase predicha |
| `matriz_confusion_final.png` | El modelo final fuera de fold: todos los episodios y sin dudosos |
| `modelo_final_sensibilidad.png` | Clase predicha y P(marchita) contra `suelo_mv` variando `hum_aire_pct` |
| `fronteras_suelo_mv.png` | Histogramas de `suelo_mv` por clase con los cortes del modelo final |
| `clase_por_hora.png` | Proporción de clases por franja horaria local |
| `prueba_railway_nuevos.png` | Datos sin etiqueta del 21–22/10: `suelo_mv` y clase predicha |

`serie_maceta01_modelado.png` es de la versión anterior (snapshot del 21/10) y la usa el informe viejo de `docs/entrega2/informe/`. Las figuras `auditoria_*` son de `AUDITORIA_DATOS.md`. El informe de esta versión está en `docs/entrega2/informe_v2/` (con copias de sus figuras en `figuras/`).

## Hallazgos y limitaciones clave

1. **Más episodios cambió todo.** De 11 a 24 episodios el mejor F1 macro por episodio pasa de 0,32 a 0,78. La fuga sigue siendo grande (0,968 aleatorio vs 0,646 por episodio).
2. **El baseline gana.** Los dos umbrales sobre `suelo_mv` (0,822) le ganan al árbol de la búsqueda en el 96 % de las remuestras y al de la placa por 0,11. La restricción "suelo + ambiental" cuesta F1.
3. **La ambiental es casi decorativa.** La HR cambia el 1,1 % de las filas: el radiador de septiembre y 7 filas del 19/10 con el aire en 41–43 %.
4. **No reconoce la recuperación post-riego** (eps. 19, 23, 27) ni la marchita del 19/10 (ep. 12). La condición de seguridad no la cumple ningún modelo.
5. **El tramo del 03/10 al 18/10 pesa mucho**: 76 % de las filas y 13 de los 24 episodios, con tres ciclos casi idénticos. Los cortes de 1716 y 1936 mV son los de la sonda en esas dos semanas.
6. **El criterio se completó después de ver resultados** (compuerta de influencia, condición de seguridad, exclusión de la luz), en la versión anterior. No se tocaron en esta.
7. **La sonda resistiva deriva** (~900 mV entre septiembre y octubre). Hace falta la calibración semanal (`docs/CALIBRACION.md`).
8. **El costo no es la restricción, los datos sí.** 231 B de los 32 KB de presupuesto; firmware completo en el 73,4 % de la flash; 33 µs medidos en la ESP32 con el modelo anterior.

## Mejoras posibles

- **Más episodios observados**, sobre todo con ambiente distinto, para que la ambiental tenga algo que aprender.
- **Feature de tiempo desde el último riego** (un riego es una caída de ~400 mV en una muestra) para la recuperación post-riego.
- **Normalizar la sonda** con la calibración semanal, o una sonda capacitiva.
- **Persistir las predicciones** en el backend (tabla `predicciones`) para evaluar el modelo en línea.
- **Flashear `arbol-p3-f03-ee3419`** y medir `t_us` real con el modelo nuevo.
