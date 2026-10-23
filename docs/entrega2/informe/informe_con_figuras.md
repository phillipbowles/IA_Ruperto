<!--
Texto de entregaia3.pdf con las figuras marcadas donde van.
Cada marca dice: [archivo] — tamaño sugerido — caption propuesto.
Todas las figuras están en docs/entrega2/fig/ (las genera notebooks/03_modelos.ipynb).
Son 4 figuras. Prioridad si no entra en 3 páginas: Fig. 1 > Fig. 2 > Fig. 3 > Fig. 4.
Primero achicar la Fig. 4 a un solo panel ("sin dudosos") y poner la 3 y la 4 lado a lado.
-->

# PlantaIa — Clasificador del estado de la planta en la ESP32

**Universidad de Montevideo · Facultad de Ingeniería · Curso de Inteligencia Artificial · Tarea 2**

**Integrantes:** Manuel Pérez, Guillermo Storace y Phillip Bowles

## 1. Objetivo y sistema

Una ESP32 mide cada 5 minutos un lirio de paz con una sonda resistiva de humedad del sustrato, un DHT11 (temperatura y humedad del aire) y un LDR (luz). Con datos recolectados en la Tarea 1 se entrenó un clasificador multiclase: código 1, `saludable` (turgente, LED verde); código 2, `estresada` (marchitez transitoria, amarillo); y código 3, `marchita` (marchitez franca, rojo). Cada 5 minutos la placa lee los sensores, calcula las features, predice y activa el LED; la inferencia no depende de WiFi.

## 2. Datos y preparación

Se usaron mediciones reales de la placa, remuestreadas a 5 minutos con la mediana desde un snapshot de la base de Railway al 21/10. En cada observación manual se registra la clase con un botón; las muestras siguientes heredan la etiqueta hasta la próxima observación y forman un episodio. Se descartaron los primeros 60 minutos tras cada arranque (transitorio de la sonda), las lecturas saturadas y las filas sin episodio. Los días sin registro —por ejemplo, del 04/10 al 17/10— quedaron como huecos, sin interpolación. Hay 1.357 filas en 11 episodios (3 saludables, 5 estresados y 3 marchitos); cuatro episodios son dudosos (por ejemplo, una etiqueta `marchita` con suelo similar a una saludable o heredada durante 16 días). Se reportan métricas con y sin ellos; al excluirlos quedan 7 episodios.

La sonda deriva por corrosión: la clase marchita pasó de aproximadamente 2830 mV en septiembre a 1760 mV en octubre. Además, todas las observaciones de marchitez fueron nocturnas (V de Cramér entre franja horaria y clase: 0,47). El 19/10 hubo dos etiquetas distintas, `marchita` y `estresada`, con lecturas cercanas (1756 y 1796 mV). Estos factores limitan la generalización.

> **[serie_maceta01_modelado.png]** — FIGURA 1 · ancho completo, ~6 cm de alto.
> *Caption:* Serie de modelado de `maceta-01` (5 min). Arriba, `suelo_mv` coloreado por clase con el número de cada episodio; abajo, temperatura del aire. Se ven las tres ventanas con datos, la deriva de la sonda (marchita a ~2830 mV en septiembre y ~1760 mV en octubre), el conflicto de los episodios 12 y 13 del 19/10 y el único episodio frío (ep. 1, ~8,5 °C).

Se calcularon siete features con la lectura actual y un buffer de 13 muestras (1 h); las medianas de suelo y luz usan 9 lecturas. Python y C++ implementan el mismo cálculo y se verificó su coincidencia.

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

El target usa los códigos 1–3 y las filas sin etiqueta no se entrenan. Se excluyeron las columnas que filtran la etiqueta (origen, episodio, calidad y hora) y se comprobó que la matriz de entrada contenga sólo estas siete features.

## 3. Evaluación y comparación

Las muestras consecutivas son muy parecidas; por ello, la partición se hizo por episodio, no aleatoriamente. Un Random Forest alcanza exactitud balanceada 0,943 con split aleatorio y 0,135 al separar episodios (azar: 0,33): el modelo reconoce el episodio, no el estado. Se usó `StratifiedGroupKFold` con 5 folds agrupados por episodio (N efectivo: 11), y búsqueda anidada por episodio (3 folds internos) maximizando F1 macro. Como cada fold de prueba contiene sólo 2–3 episodios y no las tres clases, se agregan todas las predicciones fuera de fold antes de calcular métricas. La incertidumbre se estima con bootstrap por episodio (500 remuestras); se reportan F1 macro, exactitud balanceada y recall de `marchita`, el error más costoso.

La tabla resume resultados sin los cuatro episodios dudosos. El costo de memoria/tiempo es estimado para la ESP32.

**Cuadro 2:** Comparación fuera de fold: 7 episodios.

| Modelo | F1 macro | Bal. | R. mar. | B / µs |
|---|---|---|---|---|
| Dos umbrales suelo | **0,393 ± 0,191** | **0,416** | 0,60 | 8 / 0,1 |
| Umbral único suelo | 0,388 ± 0,188 | 0,412 | 0,60 | 51 / 0,1 |
| Árbol | 0,316 ± 0,045 | 0,326 | 0,00 | 81 / 0,2 |
| MLP | 0,306 ± 0,135 | 0,395 | 0,41 | 260 / 8,2 |
| Naive Bayes | 0,297 ± 0,057 | 0,304 | 0,00 | 84 / 4,6 |
| Random Forest | 0,213 ± 0,026 | 0,227 | 0,00 | 11,6 KB / 16 |
| Reg. logística | 0,142 ± 0,072 | 0,128 | 0,00 | 52 / 4,0 |
| k-NN | 0,110 ± 0,053 | 0,141 | 0,00 | 17,7 KB / 622 |
| SVM RBF | 0,069 ± 0,035 | 0,119 | 0,00 | 17,5 KB / 1544 |
| Clase mayoritaria | 0,110 ± 0,054 | 0,232 | 0,00 | 4 / 0 |

*Bal.: exactitud balanceada; R. mar.: recall de `marchita`; B: bytes estimados en flash.*

> **[rendimiento_vs_costo.png]** — FIGURA 2 · ancho completo (o 0,8 del ancho), ~5,5 cm de alto. Va pegada al Cuadro 2.
> *Caption:* Rendimiento contra costo en la ESP32. F1 macro fuera de fold sin dudosos (± desvío bootstrap) contra la flash estimada en escala logarítmica; gris = baselines, rojo = modelo elegido, línea punteada = límite de 32 KB. Todos los candidatos entran en la memoria; lo que los separa es el rendimiento, y las barras de error se superponen.

Se compararon tres baselines (clase mayoritaria y uno o dos umbrales de suelo) y siete candidatos: regresión logística, árbol, Random Forest, Naive Bayes, k-NN, SVM RBF y MLP. Ningún candidato supera al baseline de dos umbrales; las diferencias están dentro del ruido (desvíos bootstrap de 0,05–0,19). Con los 11 episodios, incluidos los dudosos, todos quedan por debajo del azar. Las tres marchitas observadas tampoco comparten escala de sensor (2832 mV con frío, 1758 mV y 1518 mV en un episodio dudoso).

## 4. Selección y lógica del modelo

El criterio de selección, fijado antes de observar resultados, fue: (1) menos de 32 KB de flash, menos de 1 ms por predicción y sin memoria dinámica; (2) F1 macro sin dudosos dentro de un desvío del mejor; (3) desempate por interpretabilidad. Como restricción de diseño, los candidatos debían combinar suelo y al menos una variable del aire; por eso los baselines basados sólo en la sonda no eran elegibles. Se excluyó la luz: las regresiones logísticas con `luz_media_1h` llegaban a recall de marchita 0,91, pero aprendían "oscuro → marchita" y, en muestras nuevas del 22/10 con la planta sana, predecían `marchita` en 76–83 % de las filas nocturnas. Ninguna de las 66 configuraciones sin luz cumplió la condición de seguridad (recall ≥ 0,9 y acierto en la marchita de octubre); no se forzó ese resultado. Estas dos últimas decisiones se tomaron después de ver resultados.

Se eligió el árbol de profundidad 2 `arbol-p2-f012-58e644`, con `suelo_mv` y `temp_c`. Sus reglas completas son:

- **Si `temp_c` ≤ 10,25 °C:** `marchita` (rojo).
- **Si `temp_c` > 10,25 °C y `suelo_mv` ≤ 1821,5 mV:** `saludable` (verde).
- **Si `temp_c` > 10,25 °C y `suelo_mv` > 1821,5 mV:** `estresada` (amarillo).

Fuera de fold y sin dudosos obtuvo F1 macro 0,282 ± 0,136, exactitud balanceada 0,279 y recall de marchita 0,36. Aunque su F1 es inferior al de dos umbrales (0,393), la diferencia está dentro de la incertidumbre: el árbol gana en 46 % de remuestras bootstrap. La regla de frío cambia 9,7 % de las predicciones, pero se apoya en un solo episodio (13/09, cerca de 8,5 °C).

> **[fronteras_suelo_mv.png]** — FIGURA 3 · media columna (0,49 del ancho), lado a lado con la Figura 4.
> *Caption:* Distribución de `suelo_mv` por clase (filas medidas) con el corte del árbol en 1821,5 mV (línea punteada) y la clase que predice (franja superior). Las marchitas aparecen en tres zonas distintas (~1450–1600, ~1760 y ~2830 mV), mezcladas con las otras clases: ningún umbral sobre la sonda las separa.

> **[matriz_confusion_final.png]** — FIGURA 4 · media columna (0,49 del ancho), al lado de la Figura 3. Si falta lugar, recortar y dejar sólo el panel derecho ("sin dudosos").
> *Caption:* Matriz de confusión del árbol elegido, predicciones fuera de fold (izquierda: 11 episodios; derecha: 7 sin dudosos). La columna `marchita` de la fila `estresada` (204 filas) es la regla del frío aplicada al episodio 6 (16/09, 11–15 °C).

## 5. Implementación y pruebas

Un script de Python reentrena el modelo elegido y exporta `modelo_plantaia.h` como tablas `static const` en flash: código C++ sin dependencias de Arduino ni memoria dinámica. El modelo ocupa 81 B (cinco nodos y tres hojas) y requiere como máximo dos comparaciones por predicción. El ciclo de 5 minutos lee sensores, actualiza el buffer circular de 13 muestras, calcula features, predice, activa el LED y envía clase, probabilidad y versión al backend. Si faltan features (por ejemplo, si el DHT11 no responde), no predice y apaga los tres LEDs para evitar indicar erróneamente que hay que regar.

Las features de Python y C++ coinciden en pruebas. Los 21 tests de host (`pio test -e native`) verifican, además, coincidencia del 100 % entre C y scikit-learn en 324 vectores, incluidos los umbrales. En replay de 150 muestras reales alrededor de un riego, el modelo pasa de `estresada` (suelo aproximadamente 1880–1940 mV) a `saludable` tras el riego; inferencia medida en host: 0–1 µs. Ejemplo del log: `[INF] n=105 warmup=0 x=[1516,-420,20.6,53,1.14,1792,1522] -> saludable p=[0.45,0.28,0.27] t_us=1`. En 184 muestras nuevas del 22/10 (planta sana) predijo `saludable` en el 100 %, tanto de día como de noche.

## 6. Discusión y conclusión

El modelo es interpretable, evita usar la luz como sustituto de la hora del observador y satisface el requisito de incorporar temperatura. El firmware 2.0.0 usa 73,4 % de flash (962 KB de 1,31 MB) y 14,6 % de RAM; la inferencia agrega 4,3 KB de flash y 192 B de RAM. El árbol ocupa 81 B de un presupuesto de 32 KB; incluso el Random Forest (11,6 KB, cerca de 16 µs) cabía. El límite actual son los datos, no el hardware.

El rendimiento es bajo e incierto por los 11 episodios; el modelo no identifica la marchitez de octubre, la regla "frío → marchita" se sustenta en un solo episodio y el umbral de 1821 mV depende de la escala actual de la sonda, que seguirá cambiando por corrosión. Las decisiones sobre luz y seguridad se fijaron después de ver resultados, por lo que las métricas pueden ser optimistas. Aunque el sistema es interpretable, usa poca memoria y evita confundir oscuridad con marchitez, necesita más observaciones manuales de día y de distintos estados, idealmente apoyadas por fotos de la ESP32-CAM. También se propone calibrar semanalmente o usar sonda capacitiva, guardar predicciones para evaluación en línea y medir latencia en la propia placa.

La evaluación por episodio muestra que 1.357 filas no sustituyen a más episodios independientes: el split aleatorio habría sugerido 94 % de exactitud balanceada para el Random Forest, frente a 0,135 al separar episodios. El sistema está integrado de sensores a LED y queda listo para reentrenarse con observaciones nuevas, con límites de generalización explícitos.
