---
titulo: "Cómo mide la sonda de suelo y por qué más mV es más seco"
institucion: "Proyecto PlantaIa (curso de IA)"
fuentes_internas: "CLAUDE.md, docs/CALIBRACION.md, data/README.md, docs/entrega2/RESULTADOS.md"
url: null
fecha_redaccion: "2026-11-03"
idioma: es
---

# Cómo mide la sonda de suelo

## Una sonda resistiva

La humedad del sustrato se mide con una sonda **resistiva**: dos electrodos metálicos enterrados que forman, junto con una resistencia fija, un divisor de tensión. El agua del sustrato conduce la corriente. Con el sustrato mojado la resistencia entre los electrodos es baja y la tensión que lee la placa también; con el sustrato seco la resistencia es alta y la tensión sube.

Por eso **más milivoltios quiere decir más seco**: el valor "seco" de calibración es mayor que el "mojado". Un riego se ve como una caída brusca de `suelo_mv` (en octubre, de unos 1935 a unos 1500 mV en una sola muestra).

## Por qué se alimenta sólo durante la lectura

Mientras hay tensión aplicada, los iones del agua migran hacia los electrodos (electrólisis): la lectura deriva hacia abajo y los electrodos se corroen. Para limitarlo, la sonda se alimenta desde un pin de la placa (GPIO 33) **sólo mientras se mide**, con una espera fija de 100 ms. Esa espera no se alarga: el divisor se asienta en microsegundos y lo que importa es que sea siempre la misma.

## La corrosión y la deriva

Los electrodos se corroen con las semanas y la escala de la sonda se encoge: la misma humedad real se lee distinto en la semana 3 que en la semana 1. La mediana de `suelo_mv` en los episodios de marchitez franca fue de unos **2832 mV en septiembre**, **1954 mV del 03/10 al 18/10** y **1758 mV el 19/10**. Como la condición de la planta también cambia con el tiempo, esa deriva puede confundirse con una señal real; es el riesgo metodológico más serio del montaje.

La mitigación prevista es medir una vez por semana el par de referencia seco (sonda al aire) y mojado (sonda en un vaso de agua) y anotarlo en `docs/CALIBRACION.md`. Al 2026-11-03 esa tabla de calibración semanal sigue **pendiente**: no hay mediciones registradas.

## Valores de referencia en octubre

Con la escala de octubre, del 03/10 al 18/10 el sustrato acompañó a la etiqueta en todos los episodios: saludable alrededor de 1500–1610 mV, estresado alrededor de 1840–1870 mV y marchito alrededor de 1940–1960 mV. Después de un riego baja a unos 1400–1520 mV.

`suelo_pct` (el porcentaje que muestra la pantalla) no está calibrado y no se usa para nada; el modelo usa `suelo_mv`.

## El transitorio al arrancar

Cuando la placa arranca o se vuelve a meter la sonda en la tierra, la lectura arranca alta y baja de a poco durante decenas de minutos (una exponencial con constante de 24 a 83 minutos según el arranque). Por eso los primeros minutos después de un arranque no se usan para entrenar y no cuentan para detectar riegos. Si la sonda está fuera del sustrato, el ADC se satura (3124 mV) y esa lectura se trata como faltante.
