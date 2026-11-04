---
titulo: "Lo que Ruperto no sabe: limitaciones conocidas"
institucion: "Proyecto PlantaIa (curso de IA)"
fuentes_internas: "docs/entrega2/RESULTADOS.md, data/README.md, docs/ENTREGA3.md §1, docs/CALIBRACION.md"
url: null
fecha_redaccion: "2026-11-03"
idioma: es
---

# Limitaciones conocidas

## Pocos episodios, una sola planta

El modelo se entrenó con **24 episodios** de etiqueta (20 sin los dudosos) de **una sola maceta**: unas 5.660 filas a 5 minutos. Las filas contiguas comparten etiqueta y están muy correlacionadas, así que el tamaño real de la muestra son los episodios, no las filas. Con tan pocos episodios cualquier número de exactitud tiene un margen grande (±0,05 de F1 por bootstrap) y no hay garantía de que valga para otra planta, otra maceta u otro sustrato.

## La marchita nocturna no se detecta

La regla **no cumple la condición de seguridad** que se había fijado (recall de marchita ≥ 0,9; dio 0,77). El caso que falla es el episodio 12: la noche del 19/10 la planta estaba marchita con la sonda en unos 1758 mV, por debajo del corte de 1940 mV, y la regla dijo `estresada`. De noche la planta puede caerse con el sustrato menos seco que de día, y una regla sólo sobre la sonda no lo ve.

## El corte de 5,5 h puede ser el horario del observador

Las observaciones `saludable` después de los riegos del 07, 12 y 17/10 llegaron 5 o 6 horas después de regar, siempre a las 23:00 o 00:00. El corte de 5,5 h de la regla puede estar aprendiendo cuándo miraba la persona, no cuánto tarda la planta en recuperarse.

## La sonda se corroe

La escala de la sonda resistiva se encogió de septiembre a octubre (marchita en ~2832 mV en septiembre y ~1758–1954 mV en octubre). Los umbrales de 1716 y 1940 mV son de la escala de octubre; si la sonda sigue corroyéndose, se van a correr. La calibración semanal seco/mojado que debía registrar esa deriva está pendiente.

## Etiquetas dudosas

Cuatro episodios tienen etiquetas que no se sostienen solas y se dejaron afuera del entrenamiento: el 8 (marchita con el sustrato igual que saludable, de noche), el 9 (estresada con el sustrato en el rango de saludable), el 11 (propagada 16 días después y contradicha por la observación siguiente) y el 14 (estresada arrastrada 25 h después de un riego sin que nadie la confirmara).

## Huecos y sensores caídos

La serie tiene huecos (reinicios, cortes de luz y las dos semanas del 17/09 al 01/10) que **no se completan ni se interpolan**. **La placa no manda datos desde el 2026-10-29 a las 21:12 UTC**: mientras no se vuelva a enchufar, Ruperto sólo puede hablar de su pasado, no de cómo está ahora.

## Otros sensores

- El termistor marca al revés (38 °C en una noche fría, 9 °C sobre el radiador): no sirve como temperatura.
- La luz no está calibrada en lux; de 19 a 22 h hay una lámpara (~1780 mV), así que "luz alta" no siempre es sol.
- El DHT11 tiene resolución de 1 °C y ±5 % de humedad.
- Las temperaturas de 26–36 °C del 15 y 16/09 **no son errores**: la maceta estuvo sobre un radiador.
