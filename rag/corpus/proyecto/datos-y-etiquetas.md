---
titulo: "Cómo se registraron los datos y las etiquetas"
institucion: "Proyecto PlantaIa (curso de IA)"
fuentes_internas: "CLAUDE.md, data/README.md, docs/ENTREGA2.md §3, docs/entrega2/RESULTADOS.md"
url: null
fecha_redaccion: "2026-11-03"
idioma: es
---

# Cómo se registraron los datos

## Muestreo

La placa mide cada 5 minutos (en septiembre y principios de octubre, con un firmware viejo, mandaba cada 30 segundos; para analizar se agrupa todo en intervalos de 5 minutos con la mediana). Cada muestra viaja con la hora de la placa en UTC, el valor crudo del ADC además del convertido, un número de muestra correlativo y un identificador de arranque (`boot_id`) que cambia en cada reinicio.

## Episodios de etiqueta

La etiqueta no se guarda fila por fila sino como **episodios**: intervalos de tiempo durante los cuales la planta estuvo en un estado (`saludable`, `estresada` o `marchita`). Están en `data/episodios.csv`, con una nota que explica cada uno. Cada episodio tiene un origen:

- `manual`: alguien miró la planta y apretó el botón dentro del episodio. Es la única evidencia directa.
- `propagada`: la placa arrancó con la etiqueta anterior guardada y la siguió mandando; nadie miró.
- `corregida`: se reconstruyó después, de memoria o con fotos.

## Etapas del registro

- **12 al 17/09**: primeras mediciones. El 15 y el 16/09 la maceta estuvo sobre un radiador (hasta 35,6 °C y ~23 % de humedad del aire, la condición más exigente de todo el registro).
- **17/09 al 01/10**: hueco de dos semanas sin datos.
- **01 al 03/10**: episodios 8 a 10.
- **03 al 18/10**: tres ciclos casi iguales de unos 5 días: saludable → estresado (el sustrato se seca) → marchito (unas 12 h, de día) → riego a las 18:00 UTC → estresado unas 5–6 h de recuperación → saludable. Ambiente estable: 18,5–21,3 °C y 44–55 % de humedad del aire.
- **18 al 22/10**: episodios 11 a 15, con el marchitamiento nocturno del 19/10 y el riego de ese día a las 22:41 UTC.
- **22/10**: se flasheó el firmware 2.0.0 (con el modelo en la placa).
- **Hasta el 29/10 21:12 UTC**: última muestra recibida.

## Riegos detectados en el entrenamiento

Con la regla de la caída de 250 mV, los riegos detectados en los datos de entrenamiento fueron el **07/10 18:00, 12/10 18:00, 17/10 18:00 y 19/10 22:40** (hora UTC; en Montevideo son tres horas menos).

## Hora local

Los datos se guardan en UTC. Montevideo está en UTC−3 todo el año (Uruguay no usa horario de verano), así que un riego a las 18:00 UTC fue a las 15:00 en Montevideo.
