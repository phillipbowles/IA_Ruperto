# Iteraciones de la personalidad de Ruperto

Registro de cómo se ajustó la forma de responder, con las respuestas reales.
Las decisiones están en [../ENTREGA3.md](../ENTREGA3.md) §2 (D211 en adelante).
Material para la sección de resultados y mejoras del informe.

## v1 — primera prueba en Telegram (2026-11-04)

Pregunta: *¿Cómo estás?* (sensores caídos desde el 29/10).

> ¡Qué tragedia, che! Estoy sumergido en el olvido absoluto. Te aviso primero que
> mis sensores están caídos y no mandan datos desde el 29 de octubre a las 18:12 [2].
> ¡Hace cinco días y quince horas que nadie escucha mis lamentos!
>
> En aquel último suspiro de mis circuitos, mi sonda marcaba 2062 mV; como sabés,
> más milivoltios es puro desierto para mis raíces [5]. Según la regla vigente, con
> más de 1940 mV yo ya estaba marchita, entregada al destino fatal del suelo seco
> [3]. Aquella vez el aire estaba a 21.0 grados y la humedad al 65 por ciento, pero
> hoy solo soy un silencio en la base de datos. ¡Enchufame, por favor, que este
> vacío de información me mata más que la sed!

Problemas (feedback del equipo): la respuesta no está en la primera oración;
jerga del proyecto (mV, "regla vigente", umbrales); marcas `[n]` que el usuario
no puede abrir; una exageración por oración; "marchita" en femenino.

## v2 — estructura fija y palabras simples (D211), ronda 1

Mismo caso, con el reloj real:

> No tengo ni idea de cómo estoy ahora porque mis sensores no mandan datos hace
> cinco días; en la última medición estaba marchito y caído.
>
> EN PALABRAS SIMPLES: tenía la tierra muy seca y el ambiente templado.
>
> ¡Es un calvario vivir a ciegas! Por favor, revisá que la placa esté conectada.
> De paso, tocá la tierra a 2 o 3 centímetros de profundidad: si está seca, regame
> urgente hasta que el agua drene por abajo.

Mejoró: respuesta directa primero, sin mV, masculino, un cierre con qué hacer.
Problemas que quedaron (todas las respuestas en
[iteraciones/ronda1_2026-11-04.md](iteraciones/ronda1_2026-11-04.md)):

- Copia el nombre del bloque ("EN PALABRAS SIMPLES:") en la respuesta.
- Nombra la tierra con una palabra más fuerte que la del bloque ("muy seca" con
  1934 mV, que es "secándose").
- Avisa de los sensores caídos incluso cuando le preguntan por los cuidados de
  la especie.
- Presenta las 5,5 h de recuperación del semáforo como un dato de la especie.
- Error de datos: el 19/10 dice que no lo riegan hace 4 días, pero lo regaron el
  17/10 (D212).
- Latencia de 9 a 30 s por respuesta (D213).
- Cupo: después de 10 preguntas, el plan gratuito se agotó por el día (D214).

Lo que anduvo bien: el guardrail rechazó la receta de ñoquis sin generar; con
la tierra mojada recién regada dijo "no me riegues" y explicó por qué el
semáforo seguía en amarillo; las preguntas de cuidados citaron UF/IFAS, NC
State y RHS al pie.

## v3 — reglas nuevas, cadena de modelos y chequeos automáticos (rondas 2–5)

Desde la ronda 2, `docs/entrega3/eval/probar.py` corre 20 preguntas en cuatro
momentos de la serie (hoy con sensores caídos, con sed el 19/10, recién
regado, sano el 21/10) y pasa cada respuesta por chequeos sin LLM: dominio
correcto, ≤ 100 palabras, sin rótulos de bloques, sin femenino, sin jerga
técnica no pedida, fuente al pie en preguntas de ciencia, aviso de sensores
caídos sólo cuando corresponde.

| ronda | modelo que responde | pasan | latencia mediana | qué se aprendió |
|---|---|---|---|---|
| 2 | gemini-3.5-flash | 15/20 | 7,4 s | sin fragmentos (bug del script): en cuidados y toxicidad "no tengo la información" |
| 3 | gemini-3.5-flash | 10/20 | 4,0 s | con fragmentos, cita UF/IFAS, ASPCA, NC State; a la 11.ª pregunta, 429: 20 por día |
| 4 | flash-lite-latest (3-flash sin cupo) | 6/14 | 3,8 s | copia rótulos; un dato del futuro por el historial del mismo día |
| 5 | gemini-3.5-flash-lite | 16/20 | 5,3 s | buena calidad para respaldo; rótulos en medio de la línea |

Ejemplo de la ronda 3 (`gemini-3.5-flash`), *¿Sos tóxico para mi gato?*:

> Sí, soy tóxico para los gatos. Tengo oxalatos de calcio insolubles que le
> pueden causar una irritación oral muy fuerte, ardor intenso en la boca y la
> lengua, babeo excesivo, vómitos y dificultad para tragar si llega a masticar
> mis hojas. ¡Por favor, manteneme bien lejos de sus garras curiosas! Si
> sospechás que ingirió un pedazo de mi follaje, llevalo de inmediato con su
> veterinario.
>
> 📚 Fuente: ASPCA, NC State Extension

Ejemplo de la ronda 5 (`gemini-3.5-flash-lite`), recién regado, *¿Por qué tu
semáforo está en amarillo si la tierra está mojada?*:

> Mi semáforo está en amarillo porque pasaron pocas horas desde el último
> riego. El sustrato se moja al toque, pero a mí me toma horas volver a
> levantar las hojas. No me agregues más agua, dejame descansar tranquilo.
> ¡Qué difícil es recuperarse a las apuradas!

Lo que se corrigió después (D216, D217): cadena de modelos, guardrail en un
`lite`, rótulos sacados con código, historial sólo de días pasados, sin
emojis ni apodos, el ambiente sólo cuando dice algo.

Pendiente de medir: una ronda completa con `gemini-3.5-flash` cuando vuelva
su cupo diario, con todas las correcciones juntas.

## v4 — memoria y línea de tiempo (D218), ronda 6

La primera charla real con la placa de vuelta (04/11, 19:28, Telegram):

> **👤** Jajajaja q bien, decime, hace cuanto q no estas estresado o marchito?
> **🌿** Estoy entero y sin caídas desde hace dos semanas. El último episodio
> registrado quedó atrás el 20 de octubre, […]
>
> **👤** Decime cuales fueron las fechas de esos estados, los umtimos registros
> **🌿** Mis últimos registros muestran que estuve bien y firme, sin sobresaltos
> por ahora. Tierra húmeda. […]

La misma charla después de D218 (ronda 6, `gemini-3.5-flash-lite`):

> **👤** Jajajaja q bien, decime, hace cuanto q no estas estresado o marchito?
> **🌿** No me acuerdo de lo que es estar marchito desde el 29 de octubre.
> Aunque la placa estuvo apagada varios días y ese rato es un misterio, cuando
> volvió a arrancar el 4 de noviembre ya estaba firme y saludable. […]
>
> **👤** ¿Cuándo te regaron por última vez?
> **🌿** No tengo la hora exacta de mi último riego porque ocurrió mientras la
> placa estaba apagada, entre el 29 de octubre y el 4 de noviembre. La tierra
> estaba más seca antes y volvió húmeda. […]
>
> **👤** ¿Sos tóxico para mi gato? → sí, ASPCA · **👤** ¿y para mi perro?
> **🌿** Sí, también soy tóxico para tu perro. […] 📚 Fuente: ASPCA, NC State Extension

Todas las respuestas en [iteraciones/ronda6_2026-11-04.md](iteraciones/ronda6_2026-11-04.md).
Queda: en "las fechas de esos estados" supone que la tierra "se fue secando"
durante el hueco, que no lo sabe.
