# Resultados de modelos — Tarea 2 (para el informe)

**Versión final (2026-10-23): regla sonda + riego, entrenada sin los episodios dudosos.**

- **De dónde salen los números.** De la ejecución commiteada de `notebooks/03_modelos.ipynb` sobre `data/mediciones_raw_2026-10-23.csv`. El notebook reescribe todas las tablas en `docs/entrega2/tablas_03_modelos.md` (generado, no se edita).
- **Modelo de la placa:** `regla-p3-f07-79b556`, con la regla y la entrada que se ven abajo.
- **En una línea:** con 24 episodios los modelos generalizan por episodio. La regla sonda + riego es la mejor (F1 macro 0,858 ± 0,049) y le gana a la regla de dos umbrales sobre la sonda en el 98 % de las remuestras del bootstrap por episodio. No cumple la condición de seguridad: no reconoce la marchita nocturna del 19/10.
- **Historia.** `arbol-p2-f012-58e644` (21/10, 11 episodios, sonda + temperatura) → `arbol-p3-f03-ee3419` (23/10, sonda + HR, entrenado con los dudosos; F1 0,711) → esta regla. Las versiones anteriores de este archivo están en el historial de git, y los informes viejos en `historico/`.

## La regla

| condición (en este orden) | clase / LED |
|---|---|
| `h_desde_riego` ≤ 5,5 h | estresada (amarillo): la planta se está recuperando del riego |
| `suelo_mv` ≤ 1716 mV | saludable (verde) |
| `suelo_mv` ≤ 1940 mV | estresada (amarillo) |
| si no | marchita (rojo) |

- **`h_desde_riego`** es la feature 7 del contrato (`docs/ENTREGA2.md` §4): horas desde la última caída de la sonda de 250 mV o más entre dos muestras, fuera del warm-up. La placa guarda la hora del riego en Preferences.
- Se exporta como un árbol de 7 nodos (`static const`, 111 B), con a lo sumo 3 comparaciones. Las probabilidades de cada hoja son la proporción de clases del train.

## Decisiones del 2026-10-23 (tomadas mirando resultados)

1. **Nueva feature `h_desde_riego`.** El modelo anterior fallaba siempre en la recuperación post-riego (eps. 19, 23 y 27, `estresada` con el sustrato ya mojado).
2. **Entrenar sin los episodios dudosos** (8, 9, 11, 14). Con el ep. 14 en el train, el modelo aprendía "estresada hasta 25 h después del riego".
3. **Sacar la exigencia de una variable del aire.** En octubre el aire se movió entre 18–21 °C y 42–57 % de HR, y la exigencia sólo costaba F1.
4. **La luz sigue afuera**: aprende la hora del observador.

## Datos

5.663 filas a 5 min en 24 episodios de una sola maceta. Del 03/10 al 18/10 los datos llegaron con el identificador `maceta-02` por error y se unifican al leer.

| | filas | episodios | saludable | estresada | marchita |
|---|---|---|---|---|---|
| todos | 5.663 | 24 | 2.452 / 7 | 2.446 / 11 | 765 / 6 |
| sin dudosos | 5.171 | 20 | 2.425 / 6 | 2.092 / 9 | 654 / 5 |

Riegos detectados por la feature: 07/10 18:00, 12/10 18:00, 17/10 18:00 y 19/10 22:40.

## Protocolo

- **Partición por episodio:** `StratifiedGroupKFold` k=5, con búsqueda anidada por episodio (k=3).
- **Entrenamiento sin dudosos** y evaluación con y sin ellos.
- **Métricas:** sobre las predicciones fuera de fold juntas, con desvío por bootstrap de episodios (500 remuestras).
- **Fuga:** un Random Forest sin luz da 0,991 de exactitud balanceada con split aleatorio y 0,753 por episodio.

## Comparación (fuera de fold, sin dudosos)

| modelo | F1 macro | exact. bal. | recall marchita | F1 con dudosos | ROC-AUC | flash / µs |
|---|---|---|---|---|---|---|
| **Regla sonda + riego** | **0,858 ± 0,049** | **0,860** | 0,765 | **0,795** | 0,904 | 111 B / 0,3 |
| Dos umbrales (baseline) | 0,833 ± 0,057 | 0,834 | 0,765 | 0,762 | n/d | 8 B / 0,1 |
| Árbol de decisión | 0,801 ± 0,055 | 0,815 | 0,739 | 0,742 | 0,889 | 111 B / 0,2 |
| Regresión logística | 0,791 ± 0,057 | 0,827 | **0,850** | 0,726 | **0,914** | 52 B / 4 |
| Random Forest | 0,758 ± 0,075 | 0,753 | 0,564 | 0,701 | 0,870 | 6,1 KB / 11 |
| k-NN | 0,744 ± 0,058 | 0,734 | 0,492 | 0,700 | 0,851 | 66 KB / 2.370 |
| SVM RBF | 0,731 ± 0,077 | 0,756 | 0,661 | 0,684 | n/d | 12,5 KB / 981 |
| MLP | 0,672 ± 0,079 | 0,663 | 0,297 | 0,615 | 0,845 | 1,1 KB / 26 |
| Naive Bayes | 0,564 ± 0,090 | 0,561 | 0,144 | 0,513 | 0,750 | 60 B / 4 |
| Umbral único (baseline) | 0,425 ± 0,043 | 0,612 | 0,862 | 0,394 | 0,764 | 51 B / 0,1 |
| Clase mayoritaria (baseline) | 0,188 ± 0,089 | 0,203 | 0,000 | 0,219 | 0,385 | 4 B / 0 |

**Selección (§5):**

- **Costo:** queda afuera el k-NN.
- **Puntaje:** el mejor es la regla (0,858 ± 0,049), con piso en 0,809. Sólo la regla lo pasa.
- **Contra los rivales:** la regla le gana a los dos umbrales en el 98 % de las remuestras y al árbol en el 99 %.

**Configuración fija, fuera de fold:**

| | sin dudosos | todos |
|---|---|---|
| F1 macro | 0,858 | 0,795 |
| exactitud balanceada | 0,860 | 0,786 |
| recall de marchita | 0,77 | 0,65 |
| ROC-AUC OvR | 0,90 | 0,83 |

**Condición de seguridad:** recall de marchita 0,77 (< 0,9) y el ep. 12 al 0 %. **No la cumple.**

## ¿Cuánto aporta cada variable? (§6, árbol p3, hoja 20)

| features | F1 sin dudosos | post-riego (19/23/27) |
|---|---|---|
| suelo + riego + HR / sin luz | 0,805 | 69 % |
| suelo + HR | 0,774 | 0 % |
| suelo + riego + T | 0,751 | 69 % |
| suelo + delta | 0,742 | 36 % |
| suelo + riego / + VPD | 0,741 | 69 % |
| suelo | 0,710 | 0 % |
| suelo + T / + VPD | 0,64 | 0 % |

- **La humedad del aire ayuda dentro de un árbol** (de 0,71 a 0,77), pero el aporte sale del radiador de septiembre.
- **Las horas desde el riego son lo único que resuelve la recuperación.** La regla que la usa explícitamente le gana a todos los árboles.

## Errores y riesgos (§7)

- **Por episodio:** más de la mitad bien en 17 de los 20 no dudosos.
  - Fallan el 3 y el 6 (`estresada` de septiembre con la escala vieja de la sonda → `marchita`), el 12 (marchita nocturna a 1758 mV → `estresada`) y los cuatro dudosos.
  - Las recuperaciones post-riego pasan de 0 % (modelo anterior) a 76–100 %.
- **Matriz sin dudosos:** ninguna `saludable` se predice `marchita` ni al revés. Los errores son entre clases vecinas: 136 saludable → estresada, 107 estresada → saludable, 164 estresada → marchita y 154 marchita → estresada.
- **Riesgo principal: el corte de 5,5 h puede ser el horario del observador.** Las observaciones `saludable` llegaron 5,0, 6,0 y 5,0 h después de los tres riegos del 07, 12 y 17/10, siempre a las 23:00 o 00:00. El del 19/10 llegó 25 h después y el tramo intermedio es el dudoso 14.
- **Deriva de la sonda** (mediana de `suelo_mv` de la marchita): 2832 mV en septiembre, 1954 mV del 03/10 al 18/10 y 1758 mV el 19/10.
- **Hora del día:** V de Cramér entre franja horaria y clase 0,24; entre franja y predicción, 0,13.
- **Datos sin etiqueta del 21–22/10:** 272 filas, 100 % `saludable`, con `h_desde_riego` entre 47 y 69 h.

## Inferencia en tiempo real

- **Replay en host** (`docs/entrega2/logs/replay_host.txt`, 200 muestras del 19/10 desde las 14:00 UTC, mismo código que la placa):
  - 45 `estresada` → 30 `marchita` (sonda > 1940 mV) → `estresada`.
  - El riego se ve en la muestra 105 (`suelo_delta_1h` = −420, `h_desde_riego` = 0,0) y la clase queda `estresada`.
  - En la muestra 172 (5,6 h después) pasa a `saludable`.
  - `t_us` en el host: 0–33.
- **Placa:** el 22/10 corría el firmware 2.0.0 con `arbol-p2-f012-58e644` (`t_us=33`). Falta flashear el 2.1.0 con `firmware/tools/flashear_y_registrar.sh`; el log queda en `docs/entrega2/logs/placa_<fecha>.txt`.
- **Firmware 2.1.0:** 73,5 % de la flash (962.809 B) y 14,6 % de la RAM. 23 tests nativos en verde, con paridad Python↔C en 336 vectores del modelo y 190 muestras de features (con un riego real).

## Figuras (`docs/entrega2/fig/`)

| archivo | qué muestra |
|---|---|
| `serie_modelado.png` | La serie por clase con los episodios y los riegos detectados; T y HR |
| `comparacion_modelos.png` | F1, exactitud balanceada y recall de marchita de los 11 modelos |
| `rendimiento_vs_costo.png` | F1 macro contra flash estimada (log), con el límite de 32 KB |
| `modelo_final.png` | La regla en el plano (sonda, horas desde el riego) y su matriz de confusión |
| `matriz_confusion_final.png` | Matrices de confusión del modelo final, con y sin dudosos |
| `aporte_variables.png` | F1 del mismo árbol con cada subconjunto de features |
| `fronteras_suelo_mv.png` | Histogramas de la sonda por clase con los cortes de la regla |
| `clase_por_hora.png` | Proporción de clases por franja horaria |
| `prueba_railway_nuevos.png` | Datos sin etiqueta del 21–22/10 con la clase predicha |

Las figuras `auditoria_*` son de `AUDITORIA_DATOS.md`. El informe final, con sus copias de las figuras, está en `docs/entrega2/informe_final/`.
