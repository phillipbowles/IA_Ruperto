<!--
INSTRUCCIONES PARA LA CONVERSIÓN A LaTeX (no forman parte del informe)

- Objetivo: PDF de 3 páginas como máximo, A4, `article` a 10–11 pt, márgenes
  de ~2 cm, dos columnas opcionales si hace falta para que entre.
- Paquetes sugeridos: babel (spanish), booktabs (tablas), graphicx, siunitx
  (unidades: \SI{1821}{mV}, \SI{10.25}{\celsius}), hyperref, caption, float.
- Coma decimal: los números están escritos con coma decimal (0,282). Respetarla
  (siunitx con output-decimal-marker={,}) o dejarlos como texto.
- Las figuras están en el repo, en `docs/entrega2/fig/`. Las marcadas con
  [FIGURA] van en el PDF; si no entra todo en 3 páginas, sacar primero la
  Figura 3 y después achicar la Tabla 2.
- Los nombres en `monoespaciado` son identificadores de código o de
  variables: usar \texttt{}.
- No agregar contenido ni cambiar números. Se puede acortar redacción.
- Autores: completar en el título (equipo 11).
-->

# PlantaIa — Tarea 2: clasificador del estado de la planta ejecutado en la ESP32

**Curso:** Inteligencia Artificial · **Equipo:** 11 · **Fecha:** 22/10/2026

## 1. Objetivo

Una ESP32 mide cada 5 minutos sensores sobre un lirio de paz: humedad del sustrato (sonda resistiva), temperatura y humedad del aire (DHT11) y luz (LDR). Con esos datos, recolectados en la Tarea 1, se entrenó un clasificador de tres clases:

| código | clase | equivale a | LED |
|---|---|---|---|
| 1 | `saludable` | turgente | verde |
| 2 | `estresada` | marchitez transitoria | amarillo |
| 3 | `marchita` | marchitez franca | rojo |

El modelo **corre dentro de la placa**: cada 5 minutos lee, arma las features, predice y prende el LED del semáforo. La inferencia no depende del WiFi.

## 2. Datos

- **Origen.** Sólo mediciones reales de la placa (snapshot de la base de Railway al 21/10), remuestreadas a 5 min con la mediana. Las etiquetas salen de las **observaciones manuales**: cada vez que alguien miró la planta apretó el botón y registró la clase; las muestras siguientes heredan esa etiqueta hasta la próxima observación. Cada tramo con una misma etiqueta es un **episodio**.
- **Filtros.** Se descartan los primeros 60 min tras cada arranque (transitorio de la sonda), las lecturas con la sonda saturada y las filas sin episodio. Los días sin registro (por ejemplo, 04/10 al 17/10) quedan como huecos: no se interpolan ni se completan.
- **Tamaño.** 1.357 filas en **11 episodios** (3 saludable, 5 estresada, 3 marchita). Cuatro episodios tienen etiqueta **dudosa** (por ejemplo, una "marchita" con el sustrato igual al de una saludable, o una etiqueta heredada 16 días después); todas las métricas se reportan con y sin ellos (7 episodios sin dudosos).
- **Problemas detectados en la auditoría de datos:**
  1. **La sonda resistiva deriva.** La misma clase lee distinto según el mes por la corrosión de los electrodos: la marchita marcaba ~2830 mV en septiembre y ~1760 mV en octubre.
  2. **La clase está atada a la hora del observador.** Todas las marchitas se observaron de noche (V de Cramér franja horaria × clase = 0,47).
  3. **Conflicto del 19/10.** Dos observaciones a pocas horas, con la sonda casi en el mismo valor (1756 y 1796 mV), dicen `marchita` y `estresada`.

[FIGURA 1: `docs/entrega2/fig/serie_maceta01_modelado.png` — Serie de `suelo_mv` coloreada por clase y temperatura. Se ven las tres ventanas con datos y el corrimiento de escala de la sonda entre septiembre y octubre.]

## 3. Features y target

Siete features calculadas con la muestra actual y un buffer de 13 muestras (1 h). El mismo cálculo está implementado en Python (entrenamiento) y en C++ (placa), y un test automático verifica que den idéntico:

| # | feature | descripción |
|---|---|---|
| 0 | `suelo_mv` | sonda de suelo, mediana de 9 lecturas (mV; más alto = más seco) |
| 1 | `suelo_delta_1h` | cambio de `suelo_mv` en la última hora |
| 2 | `temp_c` | temperatura del aire (DHT11) |
| 3 | `hum_aire_pct` | humedad relativa del aire |
| 4 | `vpd_kpa` | déficit de presión de vapor (a partir de 2 y 3) |
| 5 | `luz_mv` | LDR, mediana de 9 lecturas |
| 6 | `luz_media_1h` | media de la luz en la última hora |

El target son los códigos 1–3. Las muestras sin etiqueta no se usan para entrenar. Antes de entrenar se descartan explícitamente todas las columnas que delatan la etiqueta (origen de la etiqueta, episodio, marcas de calidad, hora) y se verifica que en la matriz de entrada queden sólo estas 7.

## 4. Protocolo de evaluación

- **Partición por episodio.** Las muestras contiguas comparten etiqueta y son casi iguales. Con un split aleatorio, un Random Forest da **0,943** de exactitud balanceada; partiendo por episodio, **0,135** (el azar es 0,33). Toda la diferencia es *data leakage*: el modelo reconoce el episodio, no el estado de la planta. Por eso se usa `StratifiedGroupKFold` (k = 5) con el episodio como grupo, y el **N efectivo son 11 episodios**, no 1.357 filas.
- **Búsqueda de hiperparámetros anidada**, también por episodio (k = 3 interno), maximizando F1 macro.
- **Métricas.** Como cada fold de test tiene sólo 2–3 episodios (ninguno con las tres clases), las métricas se calculan sobre todas las predicciones fuera de fold juntas, y la incertidumbre con un **bootstrap por episodio** (500 remuestras). Se reportan exactitud balanceada, F1 macro y recall de `marchita` (el error más caro es no avisar que la planta está marchita).

## 5. Modelos comparados

Tres baselines sobre la sonda (clase mayoritaria, un umbral, dos umbrales) y siete candidatos con selección de features: regresión logística, árbol de decisión, Random Forest, Naive Bayes, k-NN, SVM RBF y MLP.

**Tabla 2.** Predicciones fuera de fold, 7 episodios sin dudosos (± desvío bootstrap). Costo estimado en la ESP32.

| modelo | F1 macro | exactitud bal. | recall marchita | flash | µs est. |
|---|---|---|---|---|---|
| Dos umbrales `suelo_mv` (baseline) | **0,393 ± 0,191** | **0,416** | **0,60** | 8 B | 0,1 |
| Umbral único `suelo_mv` (baseline) | 0,388 ± 0,188 | 0,412 | 0,60 | 51 B | 0,1 |
| Árbol de decisión | 0,316 ± 0,045 | 0,326 | 0,00 | 81 B | 0,2 |
| MLP | 0,306 ± 0,135 | 0,395 | 0,41 | 260 B | 8,2 |
| Naive Bayes | 0,297 ± 0,057 | 0,304 | 0,00 | 84 B | 4,6 |
| Random Forest | 0,213 ± 0,026 | 0,227 | 0,00 | 11,6 KB | 16 |
| Regresión logística | 0,142 ± 0,072 | 0,128 | 0,00 | 52 B | 4,0 |
| k-NN | 0,110 ± 0,053 | 0,141 | 0,00 | 17,7 KB | 622 |
| SVM RBF | 0,069 ± 0,035 | 0,119 | 0,00 | 17,5 KB | 1.544 |
| Clase mayoritaria (baseline) | 0,110 ± 0,054 | 0,232 | 0,00 | 4 B | 0 |

**Lectura.** Ningún candidato le gana al baseline de dos umbrales, y todas las diferencias están dentro del ruido (desvíos de 0,05 a 0,19). Con los 11 episodios, incluidos los dudosos, todos los modelos quedan por debajo del azar. Casi ningún modelo recupera la marchita fuera de fold: las tres marchitas observadas no se parecen entre sí (2832 mV con frío, 1758 mV, y 1518 mV en un episodio dudoso).

[FIGURA 2: `docs/entrega2/fig/rendimiento_vs_costo.png` — F1 macro sin dudosos contra flash estimada (escala log) para los 10 modelos, con el límite de 32 KB.]

## 6. Selección del modelo para la placa

**Criterio**, fijado antes de mirar los resultados:
1. Costo: flash < 32 KB, menos de 1 ms por predicción y sin memoria dinámica. Queda afuera la SVM.
2. Rendimiento: F1 macro sin dudosos dentro de un desvío del mejor.
3. Desempate por interpretabilidad.

**Decisiones de producto** (las dos últimas tomadas después de ver los resultados, y declaradas así):
- **Restricción de diseño.** El semáforo no puede depender sólo de la sonda, porque deriva. Todo candidato usa `suelo_mv` y al menos una variable del aire (temperatura, humedad o VPD). Por eso los baselines, que usan sólo la sonda, no son elegibles.
- **Luz excluida.** Con la luz permitida, los únicos modelos que reconocían la marchita (regresiones logísticas con `luz_media_1h`, recall de marchita 0,91) aprendieron "oscuro → marchita": en datos nuevos del 22/10, con la planta sana, predecían `marchita` en el **76–83 % de las filas nocturnas**. La luz delata la hora del observador, no el estado de la planta.
- **Condición de seguridad.** Se pidió recall de marchita ≥ 0,9 y acertar la marchita de octubre. **Ninguna de las 66 configuraciones sin luz la cumple**, y no se forzó: quedó el modelo del criterio original.

**Modelo elegido: árbol de decisión de profundidad 2** (`arbol-p2-f012-58e644`), con `suelo_mv` y `temp_c`:

| condición | clase | LED |
|---|---|---|
| `temp_c` ≤ 10,25 °C | marchita | rojo |
| `temp_c` > 10,25 °C y `suelo_mv` ≤ 1821,5 mV | saludable | verde |
| `temp_c` > 10,25 °C y `suelo_mv` > 1821,5 mV | estresada | amarillo |

Fuera de fold, sin dudosos: **F1 macro 0,282 ± 0,136**, exactitud balanceada 0,279, recall de marchita 0,36. Pierde en F1 contra los dos umbrales (0,393), dentro del ruido: el elegido gana en el 46 % de las remuestras del bootstrap. A cambio cumple la restricción de producto. La regla del frío influye de verdad (cambia la clase del 9,7 % de las filas), pero sale de un solo episodio (13/09, ~8,5 °C).

[FIGURA 3: `docs/entrega2/fig/arbol_final.png` — El árbol de la placa con sus dos cortes y las proporciones por hoja.]

## 7. Implementación en la ESP32

- **Exportación.** Un script de Python reentrena el modelo elegido y genera `modelo_plantaia.h` con las tablas del árbol como `static const` en flash. Es código C++ sin dependencias de Arduino y sin memoria dinámica.
- **Costo.** El modelo ocupa **81 B** de tablas (5 nodos, 3 hojas) y hace como mucho 2 comparaciones por predicción. El firmware 2.0.0 completo usa el **73,4 % de la flash** (962 KB de 1,31 MB) y el **14,6 % de la RAM**; la librería de inferencia suma 4,3 KB de flash y 192 B de RAM respecto del firmware anterior.
- **Ciclo en la placa.** Cada 5 min: lectura de sensores → features (buffer circular de 13 muestras) → predicción → LED → envío al backend con la clase predicha, su probabilidad y la versión del modelo. Si el vector de features queda incompleto (por ejemplo, el DHT11 nunca respondió), no se predice y los tres LEDs quedan apagados: un rojo por falta de datos haría regar una planta que puede estar bien.
- **Verificación.** 21 tests en el host (`pio test -e native`). Comprueban que las features en C coincidan con Python y que el modelo en C prediga la misma clase que scikit-learn en 324 vectores (100 % de coincidencia), incluidos casos justo en los umbrales.
- **Log de inferencia.** Un replay en el host con el mismo código de la placa sobre 150 muestras reales que cruzan un riego predice `estresada` (sonda ≈ 1880–1940 mV) y pasa a `saludable` después del riego, en 0–1 µs por inferencia. Ejemplo:
  `[INF] n=105 warmup=0 x=[1516,-420,20.6,53,1.14,1792,1522] -> saludable p=[0.45,0.28,0.27] t_us=1`
- **Prueba con datos nuevos.** Sobre 184 muestras del 22/10 que el modelo nunca vio (planta sana), predice `saludable` en el **100 %**, de día y de noche.

## 8. Discusión

**Ventajas.**
- El modelo se lee entero: tres reglas.
- Cumple la restricción de que el LED dependa del aire y no sólo de la sonda.
- No confunde la noche con marchita.
- Usa una fracción mínima de la memoria.

**Limitaciones.**
1. **Rendimiento bajo y muy incierto**, consecuencia de tener 11 episodios: uno o dos episodios deciden el orden entre modelos.
2. **No reconoce la marchita de octubre**, que con la escala corrida de la sonda se lee más húmeda que estresadas de septiembre.
3. **La regla "frío → marchita" tiene un solo episodio de respaldo.** En condiciones de octubre (siempre > 10 °C) el modelo funciona como un único umbral sobre la sonda.
4. **Parte del criterio se fijó después de ver los resultados** (exclusión de la luz, condición de seguridad), así que las métricas del elegido son algo optimistas.
5. **El umbral de 1821 mV vale para la escala actual de la sonda** y dejará de valer si los electrodos siguen corroyéndose.

**Memoria y CPU.** El límite no fue el hardware sino los datos: el árbol usa 81 B de un presupuesto de 32 KB, e incluso un Random Forest de 30 árboles (11,6 KB, ~16 µs) entraba.

**Mejoras.**
- Más observaciones manuales, sobre todo de día y en estados distintos, apoyadas en las fotos de la ESP32-CAM: es lo único que rompe la confusión clase ↔ hora.
- Calibración semanal de la sonda, o una sonda capacitiva, para que los umbrales no dependan del mes.
- Guardar las predicciones en el backend para evaluar el modelo en línea contra observaciones nuevas.
- Medir el tiempo de inferencia en la placa misma.

**Conclusión.** El resultado principal es metodológico: evaluar por episodio muestra que con 11 episodios ningún modelo generaliza con confianza, cuando un split aleatorio habría reportado 94 %. El sistema quedó completo de punta a punta (datos → features → modelo exportado → inferencia en la placa → LED), con un modelo simple y honesto sobre sus límites, listo para reentrenarse a medida que se acumulen observaciones.
