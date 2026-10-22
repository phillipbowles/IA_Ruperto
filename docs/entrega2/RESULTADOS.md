# Resultados de modelos — Tarea 2 (para el informe)

**FINAL.** Los números salen de la ejecución commiteada de `notebooks/03_modelos.ipynb` con el relleno simulado **v2** (`data/sintetico/payloads_relleno.jsonl`, 2026-10-21 23:41 UTC, idéntico byte a byte a `data/sintetico_v2/`). Todos están copiados de las salidas del notebook. El notebook también reescribe todas las tablas en `docs/entrega2/tablas_03_modelos.md`.

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
| Dos umbrales `suelo_mv` (baseline) | 0,751 ± 0,118 | **0,749 ± 0,123** | 0,811 ± 0,184 | n/d |
| Regresión logística | 0,623 ± 0,147 | 0,615 ± 0,162 | 0,421 ± 0,265 | 0,836 ± 0,067 |
| Árbol de decisión | 0,733 ± 0,133 | 0,712 ± 0,180 | 0,776 ± 0,171 | 0,818 ± 0,083 |
| **Random Forest (elegido)** | 0,744 ± 0,115 | 0,744 ± 0,119 | 0,799 ± 0,182 | 0,832 ± 0,081 |
| Naive Bayes | 0,570 ± 0,099 | 0,549 ± 0,100 | 0,422 ± 0,284 | 0,789 ± 0,101 |
| k-NN | 0,712 ± 0,191 | 0,713 ± 0,190 | 0,711 ± 0,289 | 0,806 ± 0,156 |
| SVM RBF | 0,702 ± 0,143 | 0,706 ± 0,143 | 0,610 ± 0,294 | n/d |
| MLP | 0,637 ± 0,188 | 0,639 ± 0,190 | 0,534 ± 0,275 | 0,813 ± 0,093 |

- La configuración final fija del RF, sin búsqueda, da exactitud bal. 0,716 ± 0,114, F1 0,715 ± 0,112, recall de marchita 0,793 ± 0,185 y AUC 0,822 ± 0,089.
- "Dos umbrales" es la regla `suelo ≤ t1` saludable, `≤ t2` estresada, si no marchita, con t1 y t2 ajustados en el train por F1 macro.

## Costo estimado en la ESP32 (cada modelo reentrenado con toda la serie)

| modelo | config | flash (B) | RAM (B) | ops | exp | µs est. | exportable |
|---|---|---|---|---|---|---|---|
| Dos umbrales | suelo | 8 | 0 | 2 | 0 | 0,08 | sí (dos if) |
| Umbral único | suelo | 51 | 16 | 2 | 0 | 0,08 | sí |
| Regresión logística | suelo+delta, C=0,01 | 52 | 20 | 25 | 3 | 4,0 | sí |
| Árbol | suelo, prof. 4 | 441 | 16 | 8 | 0 | 0,33 | sí |
| **Random Forest** | **suelo, 30 árboles, prof. 5** | **24.600** | **28** | **390** | 0 | **16,3** | sí (tablas) |
| Naive Bayes | suelo | 36 | 12 | 15 | 3 | 3,6 | sí |
| k-NN | suelo+delta, k=25 | 99.475 | 216 | 88.412 | 0 | 3.684 | guarda todo el train |
| SVM RBF | suelo+delta, C=0,1 | 103.260 | 28 | 64.524 | 6.452 | 9.141 | guarda los vectores soporte |
| MLP | suelo+delta, (8,) | 220 | 64 | 106 | 3 | 7,4 | sí |

- **Medido.** El replay en host da `t_us` de 1–3 µs por inferencia del RF (40 µs en la primera llamada). Falta medir en la placa (M1).
- **`pio run`.** Flash 75,3 % (986.961 B) y RAM 14,6 % (47.740 B) del firmware completo; con el árbol anterior, la flash era 73,4 %.

## Control con datos reales (filas reales agrupadas)

Exactitud balanceada (F1 macro entre paréntesis):

| modelo | reales fuera de fold | ídem sin dudosos | sim → real | ídem sin dudosos | sólo reales | ídem sin dudosos |
|---|---|---|---|---|---|---|
| Clase mayoritaria | 0,333 (0,162) | 0,333 (0,213) | 0,333 (0,162) | 0,333 (0,213) | 0,092 (0,072) | 0,232 (0,106) |
| Umbral único | 0,534 (0,388) | 0,664 (0,550) | 0,442 (0,351) | 0,664 (0,557) | 0,144 (0,130) | 0,212 (0,225) |
| Dos umbrales | 0,536 (0,389) | 0,666 (0,551) | 0,536 (0,389) | 0,666 (0,551) | 0,314 (0,320) | 0,495 (0,479) |
| Regresión logística | 0,443 (0,367) | 0,562 (0,551) | 0,418 (0,362) | 0,540 (0,536) | 0,412 (0,390) | 0,616 (0,606) |
| Árbol | 0,412 (0,332) | 0,554 (0,494) | 0,532 (0,386) | 0,654 (0,542) | 0,172 (0,167) | 0,325 (0,265) |
| **Random Forest** | **0,494 (0,402)** | **0,644 (0,591)** | **0,531 (0,424)** | **0,657 (0,588)** | **0,257 (0,221)** | **0,402 (0,338)** |
| Naive Bayes | 0,535 (0,486) | 0,738 (0,738) | 0,477 (0,396) | 0,613 (0,599) | 0,269 (0,223) | 0,402 (0,365) |
| k-NN | 0,552 (0,501) | 0,783 (0,759) | 0,564 (0,452) | 0,721 (0,661) | 0,204 (0,191) | 0,370 (0,305) |
| SVM RBF | 0,641 (0,601) | 0,922 (0,918) | 0,555 (0,445) | 0,724 (0,672) | 0,361 (0,298) | 0,519 (0,469) |
| MLP | 0,442 (0,351) | 0,549 (0,526) | 0,465 (0,377) | 0,584 (0,529) | 0,082 (0,065) | 0,199 (0,093) |

Cómo se arma cada columna:

- **Reales fuera de fold**: predicciones de la CV de la serie completa, restringidas a las filas reales.
- **sim → real** (transferencia): entrenado con los 36 episodios puramente simulados (9.228 filas), evaluado en todas las filas reales.
- **Sólo reales**: el mismo protocolo con los 11 episodios reales nada más. Reproduce el hallazgo del notebook 02.

El recall de marchita real del RF es 0,696 fuera de fold, 1,000 sin dudosos, 0,643 en sim → real y 0,931 en sim → real sin dudosos.

### Sensibilidad al ep. 13 (conflicto del 19/10)

- **El conflicto.**
  - Ep. 12: marchita, pulsación de noche con 1756 mV.
  - Ep. 13: estresada, pulsación a la mañana con 1796 mV; la mediana de 1930 mV sale de ~11 h propagadas sobre un sustrato más seco.
  - Ninguna regla monótona sobre `suelo_mv` respeta las dos. El relleno v2 se calibró creyéndole al 12.
- **Por qué el 13 no se marca dudoso.** Sería circular: se descartaría justo el episodio que contradice la calibración. En cambio se reporta la sensibilidad. El criterio de selección no cambió: usa "sin dudosos".

| Exactitud balanceada | todos | sin dudosos | sin el 13 | sin dudosos ni el 13 |
|---|---|---|---|---|
| RF, reales fuera de fold | 0,494 | 0,644 | 0,500 | 0,724 |
| RF, sim → real | 0,531 | 0,657 | 0,528 | 0,655 |
| Dos umbrales, reales fuera de fold | 0,536 | 0,666 | 0,536 | 0,666 |
| Dos umbrales, sim → real | 0,536 | 0,666 | 0,536 | 0,666 |
| SVM RBF, reales fuera de fold | 0,641 | 0,922 | 0,581 | 0,865 |
| k-NN, reales fuera de fold | 0,552 | 0,783 | 0,520 | 0,792 |

En F1 macro sim → real sin dudosos ni el 13: RF 0,630, dos umbrales 0,608, árbol 0,596.

### RF final por episodio real (proporción de filas bien clasificadas)

| ep. | clase | dudoso | mediana `suelo_mv` | fuera de fold | sim → real |
|---|---|---|---|---|---|
| 1 | marchita | | 2832 | 1,00 | 1,00 |
| 3 | estresada | | 2770 | 0,00 | 0,00 |
| 6 | estresada | | 2050 | 0,54 | 0,54 |
| 8 | marchita | sí | 1512 | 0,01 | 0,01 |
| 9 | estresada | sí | 1454 | 0,00 | 0,00 |
| 10 | saludable | | 1504 | 0,91 | 0,97 |
| 11 | saludable | sí | 1786 | 0,00 | 0,00 |
| 12 | marchita | | 1758 | 1,00 | 1,00 |
| 13 | estresada | | 1930 | 0,00 | 0,00 |
| 14 | estresada | sí | 1444 | 0,00 | 0,00 |
| 15 | saludable | | 1453 | 0,70 | 1,00 |

Hay 5 de 7 episodios no dudosos con más de la mitad de las filas bien, tanto fuera de fold como en sim → real.

## Modelo elegido y justificación

- **Modelo:** Random Forest, 30 árboles, `max_depth=5`, `min_samples_leaf=20`, `class_weight="balanced"`, **sólo `suelo_mv`**.
- **Versión:** `PLANTAIA_MODELO_VERSION = "rf-f0-c42286"`. Reemplaza al árbol `arbol-p2-…` de la pasada con el relleno v1.
- **Qué hace.** Es una función escalonada de la sonda:

  | tramo de `suelo_mv` (mV) | clase | de dónde sale |
  |---|---|---|
  | ≤ 1597,75 | saludable | |
  | 1639–1733,75 | estresada | |
  | 1740–1845,25 | marchita | octubre (ep. 12) |
  | 1845,5–2096,5 | estresada | septiembre / ep. 13 |
  | ≥ 2096,75 | marchita | septiembre |

  Hay además dos islitas de marchita de 1–3 mV en ~1598 y ~1734 mV, artefactos del promedio de 30 árboles. **No es monótona**: superpone las escalas de la sonda de septiembre y octubre.

### Criterio (§5.3, fijado antes de ver los resultados y aplicado sin cambios)

1. **Restricciones duras** (flash < 32 KB, < 1 ms, sin memoria dinámica): quedan afuera k-NN y SVM RBF.
2. **Serie completa.** El mejor F1 entre los candidatos es el RF, 0,744 ± 0,119, así que el piso es 0,625. Pasan el árbol, el RF y el MLP.
3. **Real.** *Puntaje real* = media del F1 macro en "reales fuera de fold sin dudosos" y "sim → real sin dudosos".
   - El mejor es el RF, con 0,589. El desvío bootstrap por episodio (7 episodios, 500 remuestras) es 0,051, así que el piso es 0,539.
   - El árbol (0,518) y el MLP (0,527) quedan afuera.
4. Sólo cumple todo el RF.
5. **Dentro del RF**, la configuración más simple a 1 desvío de la mejor de la búsqueda sobre toda la serie es la mejor misma: `[suelo]` prof. 5, hoja 20 (F1 interno 0,705 ± 0,014).

### Contra los baselines: **el elegido no supera con claridad al baseline de dos umbrales**

| | F1 serie | exactitud bal. serie | F1 reales oof s/d | F1 sim→real s/d | puntaje real | exactitud bal. reales oof (todos / s/d) | flash |
|---|---|---|---|---|---|---|---|
| Random Forest (elegido) | 0,744 ± 0,119 | 0,744 | 0,591 | 0,588 | **0,589** | 0,494 / 0,644 | 24.600 B |
| Dos umbrales | **0,749 ± 0,123** | **0,751** | 0,551 | 0,551 | 0,551 | **0,536 / 0,666** | 8 B |
| Umbral único | 0,523 ± 0,058 | 0,601 | 0,550 | 0,557 | 0,553 | 0,534 / 0,664 | 51 B |
| Clase mayoritaria | 0,232 ± 0,036 | 0,333 | 0,213 | 0,213 | 0,213 | 0,333 / 0,333 | 4 B |

- **Contra los dos umbrales.** En la serie completa empatan: F1 por fold −0,025, +0,088, −0,077, −0,023 y +0,013 (media −0,005; gana en 2 de 5).
  - Sobre lo real, el RF gana en puntaje (F1 macro) por +0,038, en el 78 % de las remuestras del bootstrap. Pero la diferencia es menor que un desvío (0,051).
  - En **exactitud balanceada sobre lo real los dos umbrales le ganan** (0,536 contra 0,494; sin dudosos, 0,666 contra 0,644).
  - Conclusión: el RF no lo supera de forma clara, y cuesta 3.000 veces más flash.
- **Contra el umbral único.** Gana claramente en la serie (+0,221 de F1, 4 de 5 folds); sobre lo real sólo por +0,036 de puntaje (76 % de las remuestras).
- **Contra la clase mayoritaria.** Gana en todo.

## Binario secundario (requiere cuidado = estresada ∪ marchita)

| modelo | exactitud bal. serie | F1 cuidado serie | ROC-AUC serie | exactitud bal. reales oof s/d | exactitud bal. sim→real s/d |
|---|---|---|---|---|---|
| Clase mayoritaria | 0,500 ± 0,000 | 0,061 ± 0,122 | 0,500 ± 0,000 | 0,097 | 0,500 |
| Umbral único | 0,879 ± 0,073 | 0,859 ± 0,093 | 0,879 ± 0,073 | 0,996 | 0,996 |
| Árbol | 0,848 ± 0,069 | 0,790 ± 0,163 | 0,884 ± 0,083 | 0,784 | 0,981 |
| Regresión logística | 0,875 ± 0,055 | 0,848 ± 0,091 | 0,900 ± 0,066 | 0,962 | 0,956 |
| Naive Bayes | 0,824 ± 0,118 | 0,810 ± 0,112 | 0,855 ± 0,124 | 1,000 | 1,000 |

- Usa los mismos folds que el análisis de 3 clases.
- "Seco / no seco" se resuelve casi perfecto sobre los 7 episodios reales no dudosos, con un solo umbral. Lo difícil es separar estresada de marchita.

## Figuras (`docs/entrega2/fig/`)

| archivo | qué muestra |
|---|---|
| `serie_maceta01_modelado.png` | La serie de modelado: `suelo_mv` por clase (real opaco, relleno tenue), T y qué fuente cubre cada tramo |
| `comparacion_modelos.png` | Exactitud bal., F1 macro y recall de marchita (media ± desvío y cada fold) de los 3 baselines y los 7 candidatos, serie completa |
| `matrices_confusion_candidatos.png` | Matrices de confusión fuera de fold de los 10 modelos (serie completa) |
| `rendimiento_vs_costo.png` | F1 de la serie y puntaje real contra la flash estimada (log), con el límite de 32 KB y la franja de 1 desvío del mejor |
| `modelo_final_suelo_mv.png` | El modelo de la placa como función de `suelo_mv`: probabilidad de cada clase y clase predicha |
| `matriz_confusion_final.png` | El RF final: serie completa fuera de fold, reales fuera de fold y reales entrenando sólo con simulado |
| `control_reales.png` | Exactitud bal. por modelo: serie completa, reales oof (con y sin dudosos), sim→real (con y sin dudosos), sólo reales |
| `fronteras_suelo_mv.png` | Histogramas de `suelo_mv` por clase (relleno y real) con los cambios de clase del modelo final |
| `clase_por_hora.png` | Proporción de clases por franja horaria, real vs. relleno |
| `maceta01_completada.png` | La serie completada; la genera `plantaia_ml.relleno`, no el notebook |

Las figuras `auditoria_*` son de la auditoría de datos.

## Hallazgos y limitaciones clave

1. **El N efectivo son los episodios.** El split aleatorio da 0,887 y el split por episodio 0,681 (en los reales, 0,947 contra 0,291).
   - Hay 11 episodios reales, 7 sin dudosos.
   - El desvío por episodio del puntaje real es 0,051, y entre folds el F1 varía ±0,12–0,19: la mayoría de las diferencias entre modelos son ruido.
   - Entrenando sólo con reales nada generaliza: el RF da 0,257, el mejor es la regresión logística con 0,412.
2. **El modelo elegido (RF) no supera con claridad al baseline de dos umbrales.** Empata en la serie, gana en F1 sobre lo real por menos de un desvío, pierde en exactitud balanceada sobre lo real, y ocupa 24,6 KB contra 8 B.
3. **La sonda resistiva deriva.** La misma clase da otra lectura según el mes: marchita real ~2830 mV en septiembre y ~1758 mV en octubre (ep. 12). El RF aprende una regla no monótona que superpone las dos escalas y que va a dejar de valer si la sonda sigue corriéndose. Hace falta la calibración semanal (`docs/CALIBRACION.md`).
4. **Conflicto 12/13 del 19/10.** Dos observaciones a 40 mV de distancia con clases distintas. Con el relleno calibrado al 12, el ep. 13 se predice marchita (0 % fuera de fold). Sin el 13, la exactitud real fuera de fold del RF sin dudosos pasa de 0,644 a 0,724. Sólo las fotos de la ESP32-CAM lo pueden resolver.
5. **Confusión con la hora del día.** V de Cramér franja × clase: 0,47 en lo real (marchita sólo de noche), 0,10 en el relleno v2. El modelo no usa ni luz ni hora: la asociación de su predicción con la franja (0,39) entra sólo por el sustrato.
6. **El costo no es la restricción, los datos sí.** El RF usa el 75 % del presupuesto de 32 KB y unos µs cada 5 min. Todos los candidatos salvo k-NN y SVM entran. SVM y k-NN dan los mejores números sobre lo real fuera de fold, pero ocupan ~100 KB y con 7 episodios eso no es concluyente.
