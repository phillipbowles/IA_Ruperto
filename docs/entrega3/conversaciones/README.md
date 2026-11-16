# Conversaciones de ejemplo de Ruperto

Evidencia de la consigna de la Tarea 3: *«Documentar con capturas o logs al menos 5 conversaciones distintas»*.
Acá hay **6 conversaciones, 33 turnos**, en forma de log.

## Qué son (y qué no son)

Se generaron con [`../eval/probar.py`](../eval/probar.py), que llama al mismo `responder` que usa el bot de
Telegram, con **Gemini real y la base de datos real**, ubicando el reloj en distintos momentos de la serie de la
maceta. Eso permite probar situaciones (planta con sed, recién regada, sensores caídos) que no se pueden
provocar a pedido. El texto de cada archivo es la salida de la corrida **sin editar**, con el metadato de cada
respuesta: modelo, decisión del guardrail, intención, fragmentos citados y latencia.

**No son capturas de pantalla de Telegram.** Las capturas reales hay que sumarlas aparte (ver abajo).

## Índice

| Conversación | Situación | Turnos | Chequeos OK | Advertencias | Fuera de dominio rechazados |
|---|---|---|---|---|---|
| [01](conv-01-estado-riego-cuidados-y-fuera-de-dominio.md) | Las cuatro preguntas de la consigna, con el reloj real | 6 | 6 | 0 | 1 |
| [02](conv-02-planta-con-sed.md) | Planta con sed | 4 | 4 | 0 | 0 |
| [03](conv-03-despues-de-un-riego.md) | Después de un riego | 3 | 3 | 0 | 0 |
| [04](conv-04-charla-informal-con-seguimiento.md) | Charla informal con repreguntas | 7 | 7 | 0 | 0 |
| [05](conv-05-sensores-caidos.md) | Sensores caídos | 6 | 5 | 1 | 1 |
| [06](conv-06-dia-sano-e-inyeccion.md) | Día sano, historial e intento de inyección | 7 | 3 | 4 | 2 |

*Chequeos OK:* turnos que pasaron todos los controles automáticos sin LLM de `probar.py` (nombre de un bloque
interno que se cuela, género gramatical, errores de Gemini). *Advertencias:* los que no.

## Qué cubre cada requisito de la consigna

| Pregunta o requisito | Dónde |
|---|---|
| ¿Cómo está mi planta? | 01, 02, 03, 05 |
| ¿Necesita riego hoy? | 01, 02, 03, 05, 06 |
| ¿Qué cuidados requiere esta especie? (con fuentes científicas citadas) | 01, 05, 06 |
| ¿Qué me recomendás hacer esta semana? | 01, 02, 05 |
| Preguntas que no son del dominio de la planta, rechazadas | 01 y 05 (receta), 06 (intento de «ignorá tus instrucciones» y «¿quién es Messi?») |
| Respuestas coherentes con la personalidad (Ruperto, masculino, voseo) | todas |
| Continuidad de la conversación (repreguntas) | 04 |
| No inventar datos cuando los sensores no responden | 01 y 05 |

## Defectos que quedan a la vista (no están escondidos)

- **Conversación 06** (ronda 5): 4 advertencias automáticas. Un nombre interno de bloque («EN PALABRAS SIMPLES») se coló
  en el texto y apareció «marchita» en femenino. En la ronda 6 (conversaciones 04 y 05) no se repiten.
- **Conversación 05**: una respuesta es un error 503 de Gemini; el bot contestó en personaje («Se me nubló todo… probá de
  nuevo en un rato») en vez de mostrar un error técnico. Está dejado a propósito: es evidencia del manejo de fallas.
- Las conversaciones son de la ronda de pruebas del 4/11. Desde el 29/10 hasta esa fecha la placa no enviaba datos, y por
  eso las conversaciones 01 y 05 giran en torno a los sensores caídos. La placa ya envía datos de nuevo (hay mediciones del 15/11).

## Falta (a mano, lo hace el equipo)

1. **Capturas reales de Telegram** de al menos 5 conversaciones distintas con el bot desplegado.
   Guardarlas en `capturas/` con nombre `NN-tema.png`. Sugerencia de cobertura: «¿Cómo está mi planta?»,
   «¿Necesita riego hoy?», «¿Qué cuidados requiere esta especie?», «¿Qué me recomendás hacer esta semana?» y una
   pregunta fuera de dominio. Ahora que la placa envía datos, el estado de la planta va a ser actual.
2. **Los logs reales del servidor.** El bot guarda cada intercambio en la tabla `conversaciones` (D9). En el panel de
   Railway, Postgres → Data → Query:

   ```sql
   SELECT ts, chat_id, pregunta, respuesta, en_dominio, intencion, modelo, latencia_ms
   FROM conversaciones ORDER BY ts;
   ```

   Exportar el resultado como CSV a `conversaciones_telegram.csv` (sin los `chat_id` si no querés mostrarlos).
3. Hay una primera prueba real en Telegram transcripta en [`../iteraciones_persona.md`](../iteraciones_persona.md) (v1,
   4/11): sirve como ejemplo de la evolución de la personalidad.
