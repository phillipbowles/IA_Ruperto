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
