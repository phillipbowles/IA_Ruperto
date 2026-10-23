<!--
Informe de la Tarea 2, versión con el snapshot de Railway del 23/10.
Sale de notebooks/03_modelos.ipynb (ejecución commiteada) y de docs/entrega2/RESULTADOS.md.
Cada marca [archivo.png] indica dónde va una figura; los PNG están en ./figuras/
(copias de docs/entrega2/fig/, que regenera el notebook).
Prioridad si no entra en 3 páginas: Fig. 1 > Fig. 2 > Fig. 3 > Fig. 4 > Fig. 5.
-->

# PlantaIa — Clasificador del estado de la planta en la ESP32

**Universidad de Montevideo · Facultad de Ingeniería · Curso de Inteligencia Artificial · Tarea 2**

**Integrantes:** Manuel Pérez, Guillermo Storace y Phillip Bowles

## 1. Objetivo y sistema

Una ESP32 mide cada 5 minutos un lirio de paz con una sonda resistiva de humedad del sustrato, un DHT11 (temperatura y humedad del aire) y un LDR (luz), y publica cada muestra en un backend propio (Postgres en Railway). Con esos datos se entrenó un clasificador de tres clases: código 1, `saludable` (turgente, LED verde); código 2, `estresada` (marchitez transitoria, amarillo); y código 3, `marchita` (marchitez franca, rojo). Cada 5 minutos la placa lee los sensores, calcula las features, predice y prende el LED; la inferencia no depende del WiFi.

## 2. Datos y preparación

Se usó el snapshot de la base al 23/10: 21.850 filas de la maceta, en dos ventanas: 13–17/09 y del 01/10 al 22/10. En cada observación se registra la clase con un botón; las muestras siguientes heredan la etiqueta hasta la próxima observación y forman un **episodio**. Las filas se remuestrearon a 5 minutos con la mediana (buena parte llegó cada 30 s), y se descartaron los primeros 60 minutos tras cada arranque (transitorio de la sonda), las lecturas saturadas y las filas sin episodio. Los días sin registro quedaron como huecos, sin interpolación.

Quedan **5.663 filas en 24 episodios**. Por clase: 7 episodios `saludable`, 11 `estresada` y 6 `marchita`. Cuatro episodios son **dudosos** (la etiqueta contradice al sustrato o se heredó sin que nadie mirara la planta); las métricas se reportan con y sin ellos, y sin ellos quedan 20.

Del 03/10 al 18/10 la planta recorre tres ciclos de ~5 días (13 de los 24 episodios): saludable → estresada mientras el sustrato se seca (~1500 → ~1900 mV) → marchita durante el día → riego (el sustrato cae ~435 mV en una muestra) → unas horas de `estresada` con el sustrato ya mojado → saludable. La sonda deriva por corrosión: la marchita leía ~2830 mV en septiembre y ~1950 mV en octubre. Con el snapshot anterior (21/10) todas las marchitas observadas eran nocturnas (V de Cramér entre franja horaria y clase: 0,47); las de esos ciclos son diurnas y la asociación baja a 0,24.

> **[serie_modelado.png]** — FIGURA 1 · ancho completo, ~6 cm de alto.
> *Caption:* Serie de modelado (5 min). Arriba, `suelo_mv` coloreado por clase con el número de cada episodio; abajo, temperatura del aire. Se ven los tres ciclos de secado y riego del 03/10 al 18/10 (eps. 16–28), la deriva de la sonda entre septiembre (~2830 mV) y octubre (~1950 mV) y los dos únicos ambientes extremos: el frío del ep. 1 (~8,5 °C) y el radiador del ep. 3 (~34 °C).

Se calcularon siete features con la lectura actual y un buffer de 13 muestras (1 h); las lecturas analógicas son medianas de 9 muestras. Python y C++ implementan el mismo cálculo y un test verifica que coinciden.

**Cuadro 1:** Features de entrada del clasificador.

| # | Feature | Descripción |
|---|---|---|
| 0 | `suelo_mv` | Sonda de suelo, mediana de 9 lecturas (mV; mayor valor indica suelo más seco). |
| 1 | `suelo_delta_1h` | Cambio de `suelo_mv` en la última hora. |
| 2 | `temp_c` | Temperatura del aire medida por DHT11. |
| 3 | `hum_aire_pct` | Humedad relativa del aire. |
| 4 | `vpd_kpa` | Déficit de presión de vapor calculado con temperatura y humedad. |
| 5 | `luz_mv` | Lectura del LDR, mediana de 9 muestras. |
| 6 | `luz_media_1h` | Media de la luz durante la última hora. |

El target usa los códigos 1–3 y las filas sin etiqueta no se entrenan. Se descartaron explícitamente las columnas que filtran la etiqueta (origen, episodio, marcas de calidad, hora) y se comprobó que la matriz de entrada contenga sólo estas siete features.

## 3. Evaluación y comparación

Las muestras consecutivas son casi iguales, así que la partición se hizo por episodio y no al azar. Un Random Forest con las siete features da 0,968 de exactitud balanceada con split aleatorio y 0,646 separando episodios (azar: 0,33): un tercio del número del split aleatorio es reconocer el episodio, no el estado. Se usó `StratifiedGroupKFold` con 5 folds agrupados por episodio y búsqueda de hiperparámetros anidada (3 folds internos, también por episodio) maximizando F1 macro. Como cada fold de prueba tiene 4 o 5 episodios y no siempre las tres clases, las métricas se calculan sobre todas las predicciones fuera de fold juntas, y la incertidumbre sale de un bootstrap por episodio (500 remuestras). Se reportan F1 macro, exactitud balanceada y recall de `marchita`, el error más caro.

Como restricción de diseño, todos los candidatos usan `suelo_mv` y al menos una variable del aire (T, HR o VPD), y ninguno usa la luz. Los baselines usan sólo la sonda.

**Cuadro 2:** Comparación fuera de fold, 20 episodios sin dudosos (costo estimado en la ESP32).

| Modelo | F1 macro | Bal. | R. mar. | B / µs |
|---|---|---|---|---|
| Dos umbrales suelo (baseline) | **0,822 ± 0,060** | **0,818** | 0,71 | 8 / 0,1 |
| Árbol | 0,779 ± 0,054 | 0,792 | **0,73** | 231 / 0,3 |
| k-NN | 0,734 ± 0,058 | 0,739 | 0,56 | 72 KB / 2.596 |
| Random Forest | 0,692 ± 0,052 | 0,718 | 0,65 | 18 KB / 16 |
| SVM RBF | 0,628 ± 0,072 | 0,665 | 0,64 | 57 KB / 4.490 |
| MLP | 0,590 ± 0,074 | 0,589 | 0,22 | 932 / 22 |
| Reg. logística | 0,578 ± 0,053 | 0,594 | 0,43 | 72 / 4,4 |
| Umbral único suelo (baseline) | 0,461 ± 0,091 | 0,482 | 0,22 | 51 / 0,1 |
| Naive Bayes | 0,408 ± 0,072 | 0,401 | 0,00 | 84 / 4,6 |
| Clase mayoritaria (baseline) | 0,128 ± 0,061 | 0,165 | 0,00 | 4 / 0 |

*Bal.: exactitud balanceada; R. mar.: recall de `marchita`; B: bytes estimados en flash.*

> **[rendimiento_vs_costo.png]** — FIGURA 2 · ancho completo (o 0,8 del ancho), ~5,5 cm de alto. Va pegada al Cuadro 2.
> *Caption:* Rendimiento contra costo en la ESP32. F1 macro fuera de fold sin dudosos (± desvío bootstrap por episodio) contra la flash estimada en escala logarítmica; gris = baselines, rojo = modelo elegido, franja = dentro de un desvío del mejor candidato, línea punteada = límite de 32 KB. k-NN y SVM quedan fuera por memoria y tiempo; el árbol es el único candidato dentro de la franja.

Con 24 episodios los modelos sí generalizan: el mejor candidato pasa de un F1 macro de ~0,3 (con los 11 episodios del snapshot del 21/10) a 0,78. Pero **ningún candidato le gana a la regla de dos umbrales sobre la sonda** (0,822): en el bootstrap por episodio el árbol le gana sólo en el 4 % de las remuestras. Con los dudosos incluidos todas las métricas bajan 0,06–0,07.

## 4. Selección y lógica del modelo

El criterio de selección se fijó antes de mirar quién ganaba: (1) menos de 32 KB de flash, menos de 1 ms por predicción y sin memoria dinámica; (2) F1 macro sin dudosos dentro de un desvío del mejor; (3) desempate por interpretabilidad. Dentro del tipo elegido se toma la configuración más simple a un desvío de la mejor que además **use** la variable ambiental (cambia la clase de al menos el 1 % de las filas si se la lleva a su mediana). Por último, una condición de seguridad: recall de marchita ≥ 0,9 sin dudosos y acierto en la marchita observada el 19/10 (ep. 12). Estas dos últimas reglas y la exclusión de la luz se fijaron con la versión anterior de los datos, después de ver resultados; en esta versión no se tocaron.

Sólo el árbol queda dentro de un desvío del mejor (piso 0,725). Los árboles de profundidad 2 con una ambiental no la usan (0 % de filas cambian), así que el primero que cumple es el de profundidad 3 con `suelo_mv` y `hum_aire_pct`. Ninguna de las 66 configuraciones exploradas cumple la condición de seguridad: el ep. 12 (1758 mV) cae en la zona `estresada` de la escala de octubre y ningún modelo lo acierta. Por la regla, queda la configuración anterior: **`arbol-p3-f03-ee3419`**.

> **[arbol_final.png]** — FIGURA 3 · ancho completo, ~6 cm de alto.
> *Caption:* El árbol de la placa (profundidad 3, `class_weight="balanced"`). Las proporciones de cada nodo son por clase (saludable, estresada, marchita). La humedad del aire sólo corta en las ramas de sustrato seco.

Leído como reglas, juntando las hojas iguales:

- **`suelo_mv` ≤ 1445,75 mV:** `estresada` (sustrato muy mojado; recuperación post-riego).
- **1445,75 < `suelo_mv` ≤ 1716,5 mV:** `saludable`.
- **1716,5 < `suelo_mv` ≤ 1936,5 mV:** `estresada`.
- **`suelo_mv` > 1936,5 mV y HR ≤ 43,5 %:** `estresada` (aire muy seco: el radiador de septiembre).
- **`suelo_mv` > 1936,5 mV y HR > 43,5 %:** `marchita`.

Fuera de fold y sin dudosos, la configuración fija obtuvo F1 macro 0,711 ± 0,053, exactitud balanceada 0,737, recall de marchita 0,69 y ROC-AUC OvR 0,82 (con todos: 0,651, 0,669, 0,59 y 0,74). Le gana a un Random Forest que usa sólo la sonda (0,678) en el 74 % de las remuestras, pero pierde contra los dos umbrales por 0,11. La humedad del aire cambia la clase del 1,1 % de las filas (65 filas, ninguna de noche): las del radiador de septiembre y 7 del 19/10 con el aire en 41–43 %. Con el ambiente típico de octubre, el modelo se comporta como tres cortes sobre la sonda.

> **[fronteras_suelo_mv.png]** — FIGURA 4 · media columna (0,49 del ancho), lado a lado con la Figura 5.
> *Caption:* Distribución de `suelo_mv` por clase con los cortes del árbol (líneas punteadas) y la clase que predice con la HR en su mediana (franja superior). El corte de 1936 mV separa estresada de marchita en los ciclos del 03/10 al 18/10; la marchita de septiembre (~2830 mV) queda lejos de todo y la estresada post-riego se mezcla con la saludable por debajo de 1600 mV.

> **[matriz_confusion_final.png]** — FIGURA 5 · media columna (0,49 del ancho), al lado de la Figura 4. Si falta lugar, dejar sólo el panel derecho ("sin dudosos").
> *Caption:* Matriz de confusión del árbol elegido, predicciones fuera de fold (izquierda: 24 episodios; derecha: 20 sin dudosos). Ninguna `saludable` se predice `marchita` y ninguna `marchita` sin dudosos se predice `saludable`; el error dominante es `estresada` ↔ vecinas (las recuperaciones post-riego, eps. 19, 23 y 27, salen `saludable`).

## 5. Implementación y pruebas

Un script de Python reentrena el modelo elegido y exporta `modelo_plantaia.h` como tablas `static const` en flash: C++ sin dependencias de Arduino ni memoria dinámica. El árbol ocupa 231 B (15 nodos) y hace a lo sumo tres comparaciones por predicción. El ciclo de 5 minutos lee los sensores, actualiza el buffer circular de 13 muestras, calcula las features, predice, prende el LED y manda clase, probabilidades y versión del modelo en el POST. Si falta el DHT11 desde el arranque no predice y apaga los tres LEDs, para no indicar algo con un dato inventado.

Los 21 tests de host (`pio test -e native`) pasan: features de C++ idénticas a las de Python sobre una secuencia real con reinicios, huecos y faltantes, y coincidencia del 100 % de clase entre C y scikit-learn en 384 vectores, incluidos los puntos pegados a cada umbral. En un replay de 150 muestras reales del 19/10, el modelo marca `estresada` mientras el sustrato se seca (las últimas 7 muestras, con la sonda ya en 1940 mV, siguen amarillas porque el aire está en 41–43 %), pasa a `marchita` cuando la HR sube a 44 % (27 muestras), vuelve a `estresada` cuando la sonda baja a 1936 mV y pasa a `saludable` en la muestra siguiente al riego; inferencia medida en host: 0–1 µs. Ejemplo del log: `[INF] n=105 warmup=0 x=[1516,-420,20.6,53,1.14,1792,1522] -> saludable p=[0.82,0.08,0.10] t_us=1`. Sobre 272 muestras del 21–22/10 que no tienen observación (la planta presumiblemente sana), predijo `saludable` en el 100 %, de día y de noche. El dashboard dibuja este mismo árbol (lo genera el exportador junto con el header), recorre el camino de la medición actual y avisa si la placa reporta otra versión del modelo. El 22/10 la placa se flasheó con el firmware 2.0.0 y el modelo de la versión anterior (`arbol-p2-f012-58e644`, profundidad 2): la inferencia medida **en la ESP32** tardó 33 µs, lejos del límite de 1 ms. El árbol nuevo tiene una comparación más, así que el tiempo es del mismo orden.

## 6. Discusión y conclusión

El firmware 2.0.0 usa el 73,4 % de la flash (962 KB de 1,31 MB) y el 14,6 % de la RAM; el árbol ocupa 231 B de un presupuesto de 32 KB. Incluso el Random Forest (18 KB, ~16 µs) cabía. El límite de esta entrega son los datos, no el hardware.

Sumar el tramo del 03/10 al 18/10 fue lo que más cambió el resultado: de 11 a 24 episodios, con tres ciclos completos de secado y riego observados de día. Con eso la sonda sí ordena las clases y los modelos generalizan entre episodios. El modelo de la placa es interpretable, barato, no depende de la hora ni de la luz y cumple la restricción de usar una variable del aire. Sus límites también están claros: pierde contra una regla de dos umbrales sobre la sonda; la humedad del aire sólo actúa con aire muy seco (≤ 43,5 %); no reconoce la recuperación post-riego ni la marchita del 19/10; y ese tramo aporta tres cuartos de las filas con ciclos casi idénticos, así que los cortes de 1716 y 1936 mV son los de la sonda en esas dos semanas y pueden dejar de valer con más corrosión. Además, parte del criterio de selección se fijó después de ver resultados, así que las métricas pueden ser algo optimistas.

Como mejoras: más observaciones, sobre todo con ambiente distinto, una feature de "tiempo desde el último riego" (un riego se ve como una caída de ~400 mV en una muestra) para la recuperación, calibración semanal o sonda capacitiva para normalizar la escala de la sonda, y guardar las predicciones en el backend para evaluar el modelo en línea. La evaluación por episodio vuelve a mostrar que las filas no reemplazan a los episodios: el split aleatorio habría dado 0,97 de exactitud balanceada para el Random Forest, contra 0,65 separando episodios.
