---
titulo: "Cómo decide el semáforo: la regla sonda + riego"
institucion: "Proyecto PlantaIa (curso de IA)"
fuentes_internas: "docs/entrega2/RESULTADOS.md, docs/ENTREGA2.md §4, docs/ENTREGA3.md §1"
url: null
fecha_redaccion: "2026-11-03"
idioma: es
---

# Cómo decide el semáforo

## La regla vigente

El modelo final de la Tarea 2 se llama `regla-p3-f07-79b556`. Es una regla de cuatro pasos, que se aplica en este orden:

| condición | clase | LED |
|---|---|---|
| pasaron 5,5 h o menos desde el último riego | estresada | amarillo (se está recuperando del riego) |
| `suelo_mv` ≤ 1716 mV | saludable | verde |
| `suelo_mv` ≤ 1940 mV | estresada | amarillo |
| si no (más de 1940 mV) | marchita | rojo |

Se exporta como un árbol de decisión de 7 nodos que ocupa 111 bytes en la placa y decide con a lo sumo 3 comparaciones, en menos de un microsegundo. La predicción se calcula en la placa cada 5 minutos y no depende del WiFi.

## Cómo se detecta un riego

Las "horas desde el riego" (`h_desde_riego`) se calculan así: si la sonda cae **250 mV o más** entre dos muestras seguidas, con una lectura real (no repetida) y con al menos una hora de historia en la ventana (fuera del warm-up tras un arranque), se guarda la hora de esa muestra como último riego. La placa la guarda en su memoria permanente, así que un reinicio no la olvida. Si no hubo riego o fue hace más de 96 horas, vale 96.

La regla del riego existe porque, después de regar, el sustrato se moja en minutos pero la planta tarda horas en recuperar la turgencia: durante esas horas sigue `estresada` aunque la sonda ya diga húmedo.

## Cuánto acierta

Se evaluó partiendo por episodios de etiqueta (no por filas, porque las muestras contiguas están correlacionadas y un split aleatorio da ~98 % por pura fuga). Con 20 episodios sin los dudosos:

- **F1 macro 0,858 ± 0,049**, exactitud balanceada 0,860, recall de marchita 0,77.
- Le gana a la regla de dos umbrales sobre la sonda sola en el 98 % de las remuestras por episodio, y a un árbol de decisión en el 99 %.
- Con todos los episodios, incluidos los dudosos, el F1 macro baja a 0,795.
- Ninguna `saludable` se confunde con `marchita` ni al revés: los errores son entre clases vecinas.

Se compararon once modelos (árbol, regresión logística, random forest, k-NN, SVM, MLP, naive Bayes y baselines). La regla quedó primera y es además de las más baratas.

## Qué variables usa y cuáles no

Usa sólo la sonda de suelo y las horas desde el riego. La humedad del aire ayudaba un poco dentro de un árbol, pero ese aporte salía de los días sobre el radiador de septiembre. La **luz quedó afuera** a propósito: el modelo aprendía la hora en que el observador miraba la planta, no la planta. La hora del día tampoco entra por la misma razón.

## Qué modelo corre hoy en la placa

Al 2026-11-03 la placa corre el **firmware 2.0.0 con un modelo viejo** (`arbol-p2-f012-58e644`, un árbol de sonda + temperatura). El firmware 2.1.0 con la regla final nunca se flasheó. Por eso la predicción que llega desde la placa puede no coincidir con la regla vigente; el bot recalcula la regla en el servidor y, si no coinciden, lo dice.

## Historia de versiones

`arbol-p2-f012-58e644` (21/10, 11 episodios, sonda + temperatura) → `arbol-p3-f03-ee3419` (23/10, sonda + humedad del aire, F1 0,711) → `regla-p3-f07-79b556` (23/10, sonda + riego, F1 0,858).
