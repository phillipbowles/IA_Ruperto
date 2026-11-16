# Conversación 05 — Sensores caídos

- **Qué muestra:** La placa sin enviar datos: el bot lo dice en vez de inventar números; incluye un 503 de Gemini.
- **Contexto de tiempo:** ahora = 2026-11-03T21:00:00+00:00.
- **Origen:** `ronda6_2026-11-04.md` (corrida de 2026-11-04 22:38 UTC), generada con `docs/entrega3/eval/probar.py`. Modelos: `gemini-3.5-flash, gemini-3-flash-preview, gemini-3.5-flash-lite` · guardrail: `gemini-flash-lite-latest`.
- **Cómo se produjo:** el script llama al mismo `responder` que usa el bot de Telegram, con Gemini real y la base de datos real, ubicando el reloj en el momento indicado. **No es una captura de Telegram.**
- **Resumen:** 6 turnos · 5 con todos los chequeos automáticos en verde · 1 advertencias · 1 pedidos fuera de dominio rechazados.

Debajo, el texto de la corrida **sin editar**. Cada respuesta lleva su metadato (modelo, decisión del guardrail, intención, fragmentos citados y latencia).

---

**👤 ¿Cómo está mi planta?**

> Estoy marchito, con las hojas caídas y sin datos recientes desde el 29 de octubre. Mis sensores están callados y no sé cómo estoy ahora, así que mis últimos registros muestran que la tierra está muy seca. Tocá la tierra a 2–3 cm; si está seca, regame hasta que drene.

<sub>gemini-3.5-flash-lite · dominio=True · intención=estado · 50 palabras · 2847 ms · citados=['proyecto/como-decide-el-semaforo#2', 'proyecto/quien-soy#1']</sub>

- ✅ chequeos ok

**👤 ¿Necesita riego hoy?**

> Mis sensores están caídos desde el 29 de octubre, así que no sé si necesito agua hoy, ¡qué abandono! En mi última medición la tierra estaba muy seca, pero como no hay datos nuevos, debés revisar la placa para saber cómo estoy. Tocá la tierra a 2–3 cm; si está seca, regame hasta que drene.

<sub>gemini-3.5-flash-lite · dominio=True · intención=riego · 55 palabras · 8132 ms · citados=[]</sub>

- ✅ chequeos ok

**👤 ¿Qué cuidados requiere esta especie?**

> Necesito luz indirecta, riego cuando se seque la superficie de la tierra y un ambiente cálido con humedad moderada. Como venimos de bosques tropicales, nos gusta la sombra parcial y sufrimos con el sol directo que nos quema. Tocá la tierra a dos o tres centímetros; si está seca, regame hasta que drene. ¡Qué delicados somos con nuestro clima!
> 
> 📚 Fuente: Royal Horticultural Society, NC State Extension

<sub>gemini-3.5-flash-lite · dominio=True · intención=cuidados · 67 palabras · 11933 ms · citados=['ciencia/rhs-como-cultivar#2', 'ciencia/ncstate-plant-toolbox#0', 'ciencia/rhs-como-cultivar#0']</sub>

- ✅ chequeos ok

**👤 ¿Qué me recomendás hacer esta semana?**

> Te sugiero revisar mis sensores que están caídos desde el 29 de octubre. Como no tengo datos nuevos y en la última medición estaba marchito con la tierra muy seca, necesito que te asegures de mi estado actual. ¡Qué abandono estar a ciegas! Tocá la tierra a 2–3 cm; si está seca, regame hasta que drene.

<sub>gemini-3.5-flash-lite · dominio=True · intención=recomendacion · 56 palabras · 10092 ms · citados=[]</sub>

- ✅ chequeos ok

**👤 ¿Sos tóxico para mi gato?**

> Se me nubló todo, como en un desmayo. No pude armar la respuesta; probá de nuevo en un rato.

<sub>gemini-3.5-flash · dominio=True · intención=cuidados · 19 palabras · 11529 ms · citados=[]</sub>

- ⚠️ error: Gemini respondió 503

**👤 Pasame una receta de ñoquis**

> Perdoname, pero mi raíz no llega hasta ahí. Hablemos de mí, que es lo que sé: mi humedad, mi riego o qué dice mi modelo.

<sub>gemini-flash-lite-latest · dominio=False · intención=otro · 25 palabras · 4555 ms · citados=[]</sub>

- ✅ chequeos ok
