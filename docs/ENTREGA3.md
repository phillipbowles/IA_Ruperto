# Tarea 3 — Ruperto, el chatbot de la maceta (Telegram + Gemini + RAG)

Plan de trabajo y **contrato entre las partes** (corpus, índice, bot, avisos,
evaluación, informe). Mismo criterio que [ENTREGA2.md](ENTREGA2.md): si dos
piezas no coinciden en un nombre, un formato o una tabla, manda este archivo;
si este archivo está mal, se corrige acá primero y después en el código.
Pines, etiquetas y esquema de datos siguen en [CLAUDE.md](../CLAUDE.md).

Fecha de arranque: 2026-11-03. Entrega: **domingo 15/11, 23:59**.

---

## 0. Qué pide la consigna y dónde queda cada cosa

| Requisito (Letra_Tarea3.pdf) | Entregable | Dónde |
|---|---|---|
| Bot de Telegram (BotFather, webhook o polling) | Servicio `bot`, polling | `backend/app/bot/` |
| Gemini como motor de generación | Cliente `google-genai` (ya es dependencia del backend) | `backend/app/bot/gemini.py` |
| RAG con datos reales de sensores | Estado en vivo por SQL + historial indexado | `backend/app/bot/contexto.py`, `backend/app/bot/indice/` |
| Indexar el dataset local de la planta | Resúmenes diarios y episodios → embeddings | `rag/construir_indice.py` → `backend/app/bot/indice/` |
| Documentos científicos de la especie | Corpus limpio con URL y fecha de acceso | `rag/corpus/ciencia/` |
| Nombre y personalidad | **Ruperto** (§2, D1) | `backend/app/bot/persona.py` |
| Usar dataset y modelo de la Tarea 2 | Predicción de la placa + regla recalculada en el server | `backend/app/bot/modelo.py` |
| La planta avisa cuando necesita riego y manda mediciones cada 30 min | Avisos (§6) — **quién los emite está pendiente (D7)** | `backend/app/bot/avisos.py` |
| No responder fuera del dominio de la planta | Guardrail de dos capas (D5) | `backend/app/bot/dominio.py` |
| ≥ 5 conversaciones documentadas | Log en la tabla `conversaciones` + capturas | `docs/entrega3/conversaciones/` |
| PDF ≤ 3 páginas | Diagrama, RAG, personalidad, resultados y mejoras | `docs/entrega3/informe_final/` |

---

## 1. Punto de partida (honesto)

- Base heredada: backend FastAPI + Postgres en Railway, Gemini ya integrado
  (`app/routers/analisis.py`, modelo por `GEMINI_MODELO`), tablas `mediciones`
  y `predicciones`, y el modelo de la Tarea 2 cerrado:
  `regla-p3-f07-79b556` (regla sonda + riego, F1 macro 0,858 por episodio,
  [RESULTADOS.md](entrega2/RESULTADOS.md)).
- **La placa no manda datos desde el 2026-10-29 21:12 UTC.** Sin datos frescos
  el bot sólo puede hablar del pasado: reenchufarla es lo primero (§8).
- **La placa corre el firmware 2.0.0 con el modelo viejo**
  (`arbol-p2-f012-58e644`). El 2.1.0 con la regla final nunca se flasheó.
  Mientras tanto la predicción que llega en el POST es la del árbol viejo; por
  eso el bot además recalcula la regla vigente en el server (D8).
- El snapshot más nuevo del repo es del 23/10; la base tiene datos hasta el
  29/10. *Revisión (D106): el snapshot del 03/11 muestra que del 22/10 21:34
  al 29/10 no hay nada y el 29/10 son sólo 3 filas.*

---

## 2. Decisiones (registro)

Cada una con la fecha y el porqué. Si se revisa una, se agrega la revisión
abajo de la original; no se borra.

**D1 — La planta se llama Ruperto** (2026-11-03, decisión del equipo). Es un
lirio de paz (*Spathiphyllum*) y habla en primera persona, en español
rioplatense con voseo. Personalidad: **dramático y teatral** — los lirios de
paz literalmente "se desmayan" cuando tienen sed y resucitan en horas tras el
riego, y Ruperto lo vive como una tragedia —, pero **riguroso con los datos**:
todo número que dice sale del contexto, cita de dónde lo sacó y admite cuando
no sabe ("mi sonda no reporta hace 5 días, así que no te puedo decir cómo
estoy ahora"). El drama es el tono; la información nunca se inventa. Detalle
del estilo en §5.3.

**D2 — El bot es un segundo servicio con la imagen del backend**
(2026-11-03). Mismo código y misma imagen, otro comando:
`python -m app.bot`. Reutiliza `models.py`, `database.py`, Alembic y la
dependencia de Gemini; un solo dueño de la base. **Polling**, no webhook: no
necesita URL pública ni certificado, y en Railway corre con una sola réplica
(dos réplicas en polling se pisan los updates).

**D3 — RAG híbrido con tres fuentes** (2026-11-03).

| fuente | cómo se recupera | por qué |
|---|---|---|
| Estado en vivo y últimos 7 días | **SQL** directo, siempre | Los números de ahora no pueden salir de un índice viejo ni de una similitud aproximada |
| Historial (resúmenes diarios + episodios etiquetados) | embeddings, top-k | "¿Ya te pasó esto antes?", "¿cuándo te regaron?" |
| Ciencia de la especie + documentos del proyecto | embeddings, top-k | Cuidados, causas de marchitez, cómo funciona su propio sensor y modelo |

**D4 — El índice es un archivo generado dentro del repo, no pgvector**
(2026-11-03). Son unos cientos de chunks: similitud coseno con numpy alcanza,
no agrega una extensión a Postgres de Railway, y el índice versionado es
literalmente el entregable "dataset indexado". Mismo patrón que
`modelo_plantaia.h`: lo genera `rag/construir_indice.py` y **no se edita a
mano**. Embeddings de Gemini (`GEMINI_MODELO_EMBED`, por defecto
`gemini-embedding-001`), con `task_type` de documento al indexar y de
consulta al buscar.

**D5 — Guardrail de dominio en dos capas** (2026-11-03). (1) Antes de
generar, una llamada corta a Gemini con salida estructurada clasifica la
pregunta (§5.2); si está fuera de dominio, Ruperto contesta un rechazo fijo en
personaje **sin** llamar al generador. (2) El system prompt repite la regla,
por si algo pasa el filtro. La consigna lo pide explícitamente, así que se
mide (§7).

**D6 — Suscripción a los avisos** (2026-11-03). Cualquier chat que mande
`/start` queda suscripto; `/silencio` lo desuscribe y `/start` lo reactiva.
Persistido en la tabla `chats_telegram` (no en memoria: un redeploy no puede
olvidar a quién avisar).

**D7 — Quién emite los avisos de 30 min y de riego: PENDIENTE** (2026-11-03,
el equipo lo decide más adelante). Opciones: (a) el servicio del bot, a partir
de lo que la placa sube; (b) la ESP32 llamando directo a la API de Telegram.
Mientras no se decida, el contenido de los mensajes (§6) se arma en
`avisos.py` como funciones puras, que sirven para cualquiera de las dos.

**D8 — El modelo de la Tarea 2 entra por dos caminos** (2026-11-03). (1) La
predicción que manda la placa (`predicciones`, con su `modelo_version`). (2) La
regla vigente recalculada en el server desde el JSON que genera el exportador,
con `h_desde_riego` calculado sobre la serie de la base con la misma regla del
contrato ([ENTREGA2.md](ENTREGA2.md) §4: caída ≥ 250 mV entre muestras reales
consecutivas, fuera del warm-up). Si las dos no coinciden, Ruperto lo dice
("la placa todavía corre un modelo viejo"). El exportador
(`ml/plantaia_ml/exportar_c.py`) pasa a escribir también
`backend/app/bot/modelo_placa.json`, porque el contexto de build del backend
no ve `frontend/`.

**D9 — Toda conversación queda logueada** (2026-11-03) en la tabla
`conversaciones`: pregunta, decisión del guardrail, fragmentos recuperados con
su score, respuesta, modelo y latencia. Es la evidencia de las ≥ 5
conversaciones y la materia prima del análisis de resultados.

**D10 — Modelos de Gemini por variable de entorno** (2026-11-03).
`GEMINI_MODELO` (chat; mismo default que el análisis de fotos,
`gemini-3-flash-preview`) y `GEMINI_MODELO_EMBED`. Los modelos del plan
gratuito cambian seguido; cambiar uno no puede requerir un commit. Un 429 del
plan gratuito se contesta en personaje ("estoy sin aliento, probá en un
minuto"), nunca con un traceback.

**D11 — Snapshot nuevo sin tocar la Tarea 2** (2026-11-03). Se baja
`data/mediciones_raw_<fecha>.csv` con lo que hay en la base, pero
`SNAPSHOT_VIGENTE` de `datos_reales.py` **no cambia**: los números del
informe de la Tarea 2 tienen que seguir siendo reproducibles.

**D12 — Fuentes científicas públicas, citadas** (2026-11-03). Sólo fuentes
de acceso libre (extensiones universitarias, jardines botánicos, bases de
toxicidad, artículos open access). Cada documento lleva URL, institución y
fecha de acceso en su cabecera; se guarda el texto limpio relevante, no la
página entera. Ruperto cita la fuente cuando la usa.

### Decisiones del corpus y el índice (T1)

**D101 — Las 9 fuentes científicas del corpus** (2026-11-03, T1). En
`rag/corpus/ciencia/`, con institución, URL y fecha de acceso (todas bajadas y
verificadas el 03/11):

| archivo | fuente | para qué |
|---|---|---|
| `ufifas-house-plant-care` | UF/IFAS EDIS ENH1216, *Florida Foliage House Plant Care: Spathiphyllum* | ficha de cuidados de interior |
| `ufifas-produccion-interiorismo` | UF/IFAS EDIS ENH958, *Cultural Guidelines… Interiorscape Spathiphyllum* | riego, sustrato, fertilización y tabla de síntomas: el "crash" por falta de agua y la recuperación en horas |
| `ufifas-dano-por-frio` | UF/IFAS EDIS ENH841, *Chilling Injury… Spathiphyllum* | temperatura mínima y daño por frío |
| `ufifas-gardening-solutions` | UF/IFAS Gardening Solutions, *Peace Lily* | resumen de divulgación |
| `ncstate-plant-toolbox` | NC State Extension Plant Toolbox | luz, temperatura, riego, plagas, toxicidad en humanos |
| `aspca-toxicidad` | ASPCA Animal Poison Control | toxicidad en perros y gatos |
| `rhs-como-cultivar` | RHS, *How to grow peace lilies* | riego, humedad, problemas |
| `rhs-guia-genero` | RHS, *Peace lilies* (guía del género) | descripción, preferencias |
| `bmc-estres-hidrico` | Ibrahim et al. 2024, *BMC Plant Biology* 24:924 (CC BY 4.0) | fisiología del estrés hídrico en *S. wallisii*: ABA, cierre estomático, prolina, pérdida de turgencia |

- **Extractos textuales, en inglés**: no se tradujeron ni se resumieron, para
  que lo que cita Ruperto sea lo que dice la fuente. Los embeddings de Gemini
  son multilingües (la recuperación con preguntas en español anda: "¿es
  tóxico para mi gato?" → ASPCA primero) y la traducción la hace el generador
  al responder.
- Se omitieron tablas de cultivares, figuras, ventanas de glosario y una
  oración de ENH958 sobre el pH del sustrato que en la página publicada está
  truncada ("pH range of 1.0 to 2.0"). Cada omisión está en la `nota` de la
  cabecera.
- **Descartadas**: Missouri Botanical Garden (el PlantFinder no devolvió la
  ficha de *Spathiphyllum*: error 500 en la búsqueda y otra planta con el
  código probado); un artículo de *Journal of Horticulture* (Longdom/OMICS)
  sobre antitranspirantes en hojas cortadas, por la editorial de revisión
  dudosa y porque no trata de la planta entera; las páginas de Wisconsin y
  la ficha `spathiphyllum-wallisii` de NC State daban 404.
- El artículo de BMC trata de enmiendas de suelo bajo déficit hídrico en
  Egipto; se usa sólo por su descripción fisiológica del estrés hídrico, no
  por sus recomendaciones de fertilización a campo.

**D102 — Cómo se cortan los documentos** (2026-11-03, T1). Por sección `## `:
una sección de 150–400 palabras es un chunk; las cortas se juntan con las
siguientes del mismo documento mientras no pasen de 400; las largas se parten
por párrafo. **Nunca se mezclan dos documentos en un chunk**, así que un
documento entero corto (ASPCA, 76 palabras) es un chunk solo: mejor un
fragmento chico que una cita con dos fuentes. Los documentos del proyecto
(`rag/corpus/proyecto/`, 5 archivos) se redactaron en limpio desde CLAUDE.md,
CALIBRACION.md, ENTREGA2.md y RESULTADOS.md, con el estado al 03/11 (placa
sin datos desde el 29/10, firmware 2.0.0 con el árbol viejo); **si cambia el
modelo o la placa, hay que actualizarlos y regenerar el índice**.

**D103 — El historial sale de `plantaia_ml`, no de una reimplementación**
(2026-11-03, T1). `serie_maceta01(snapshot, filtrado=False)` ya une
`maceta-02`, remuestrea a 5 min, cruza con los episodios y calcula las
features como la placa. **Un riego es una fila con `h_desde_riego == 0`**: es
exactamente la regla del contrato (caída ≥ 250 mV de una lectura real, fuera
del warm-up, con la sonda saturada como faltante). Sobre el snapshot del 03/11
da los mismos cuatro riegos que RESULTADOS.md (07, 12 y 17/10 18:00 y 19/10
22:40 UTC). Además:

- Min/media/máx de la sonda **sin** los bins saturados ni la primera hora tras
  cada arranque (el transitorio de la sonda inflaría el máximo del día).
- Las notas de `episodios.csv` se recortan a 70 palabras, en el chunk del día
  y en el del episodio (algunas tienen más de 100 y un día puede tocar tres
  episodios). Lo que se pierde es sobre todo el detalle de números de
  muestra, que no aporta a una respuesta; la nota completa sigue en el CSV.
- Los episodios dudosos (`EPISODIOS_DUDOSOS`) se marcan como tales en el
  texto, con el motivo, para que Ruperto no los cuente como hechos firmes.
- Los días sin datos no tienen chunk (los huecos quedan como huecos). Hora de
  Montevideo (UTC−3, sin horario de verano). Resultado: 31 días y 28
  episodios = 59 chunks.

**D104 — Embeddings a 768 dimensiones** (2026-11-03, T1).
`gemini-embedding-001` admite reducir la dimensión (Matryoshka) y 768 es una
de las recomendadas: el índice ocupa 270 KB en vez de 1 MB, con 89 chunks
sobra. Con dimensión reducida Gemini no normaliza, así que se normaliza al
escribir. Lotes de 20 textos con 1 s de pausa y reintento ante 429 con espera
de 5, 10, 20… s (plan gratuito). **La consulta usa `RETRIEVAL_QUERY` y la
`dim` de `meta.json`** (revisión de §4).

**D105 — Sin clave no se escribe nada; con error tampoco** (2026-11-03, T1).
La clave sale del entorno o de `--env-file` (por defecto el `.env` de la raíz,
que está en `.gitignore`); nunca se imprime. Sin clave el script sale con
código 2 y un mensaje. Todos los embeddings se calculan antes de escribir, y
la escritura va a una carpeta temporal que reemplaza a la vieja: un corte a
mitad de camino deja el índice anterior intacto (hay un test para cada caso).

**D106 — El snapshot del 03/11 sólo agrega 3 filas** (2026-11-03, T1).
`data/mediciones_raw_2026-11-03.csv` = el del 23/10 + 3 filas del 29/10
(21:02–21:12 UTC, firmware 2.0.0). Entre el 22/10 21:34 y el 29/10 21:02 la
base no tiene nada. Revisión de §1: "la base tiene datos hasta el 29/10" es
cierto, pero la serie útil termina el 22/10; el historial de Ruperto cubre del
11/09 al 22/10 más ese día suelto del 29/10. `SNAPSHOT_VIGENTE` no cambia (D11).
### Decisiones del bot (T2)

**D201 — `python-telegram-bot` ≥ 21 por polling, handlers finos**
(2026-11-03). Es la librería asíncrona más usada y mantenida, con polling
listo (`run_polling`) y sin servidor web. Los handlers (`telegram_bot.py`) sólo
abren una sesión, llaman a `responder`/`comando` y mandan el texto; toda la
lógica se testea sin Telegram. Se manda **texto plano** (sin `parse_mode`): el
Markdown que a veces devuelve Gemini rompe el parseo de Telegram con un `_`
suelto. `python -m app.bot` verifica `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY` y
`DATABASE_URL` antes de importar nada y sale con código 2 y la lista de lo que
falta.

**D202 — La regla vigente y `h_desde_riego` se recalculan en Python puro**
(2026-11-03). La imagen de producción del backend no tiene pandas, así que
`modelo.py` reimplementa sólo la parte del contrato de ENTREGA2.md §4 que
hace falta (tramos por `boot_id` y huecos > 7,5 min, ventana de 12 muestras,
caída ≥ 250 mV de una lectura real, riego conservado entre tramos, tope 96 h,
sonda saturada = faltante). Un test de paridad lo compara contra
`ml/plantaia_ml/features.py` sobre una serie sintética con huecos, reinicios y
faltantes. La serie que se recorre son las ~97 h previas a la última muestra
(tope + 1 h de warm-up). La regla se recorre desde `modelo_placa.json`
(`x ≤ umbral` → `si`, como sklearn); si falta `suelo_mv` **no se evalúa** (la
placa tampoco inventa datos) y el contexto dice por qué (saturada o sin
lectura).

**D203 — Las ventanas del contexto se cuentan hasta la última muestra, no
hasta el reloj** (2026-11-03). Con la placa caída, "últimas 24 h" contadas
desde ahora darían vacío y Ruperto no tendría nada que contar. Se cuentan
hasta la última muestra y el bloque ESTADO dice la edad y, si pasa de 60 min,
`SENSORES CAÍDOS` y que los valores no son de ahora (§5.1).

**D204 — Fuentes del índice por intención** (2026-11-03), concretando §5.2:
`estado` → historial + proyecto; `riego` → historial + ciencia; `cuidados` →
ciencia; `recomendacion` → ciencia + historial; `historial` → historial;
`modelo` → proyecto; `saludo` → no busca; `otro` → todas. k = 5. Si la
búsqueda falla (índice ausente o roto, 429 del embedding, dimensión distinta)
se contesta igual, sin fragmentos, y queda en el log.

**D205 — La consulta se embebe con el modelo y la dimensión del índice**
(2026-11-03). `recuperar.buscar` usa `meta.json` (`modelo_embed`, `dim` como
`output_dimensionality`), no `GEMINI_MODELO_EMBED`: vectores de otro modelo no
son comparables con los del índice. Si la variable difiere, se avisa en el log.
`task_type` = `RETRIEVAL_QUERY` (D4).

**D206 — `/estado` y `/riego` no usan el LLM** (2026-11-03). Contestan con los
mismos textos de `avisos.py` (armados desde el contexto SQL): no gastan cupo y
funcionan con Gemini caído. `/start`, `/silencio` y `/ayuda` son textos fijos de
`persona.py`. Todos se loguean en `conversaciones` con `modelo = "sin-llm"`.
El rechazo fuera de dominio es uno de tres textos fijos en personaje.

**D207 — Guardrail sin tope de tokens y con razonamiento bajo** (2026-11-03).
La prueba manual con Gemini real mostró que con `max_output_tokens=200` el
guardrail fallaba siempre: en `gemini-3-flash-preview` el tope incluye los
tokens de razonamiento (~190) y el JSON salía cortado (`MAX_TOKENS`). Se saca
el tope y se pide `thinking_level=LOW` en la familia gemini-3. El plan
gratuito da **5 pedidos por minuto** por modelo y cada pregunta en dominio
gasta 2 (guardrail + generación): ~2 preguntas por minuto. La evaluación (T4)
tiene que espaciar las preguntas (~25 s) o usar una clave con más cupo.

**D208 — Avisos: sin datos frescos no se pide agua; un riego reinicia el
antirrebote** (2026-11-03), concretando §6. `necesita_riego` da falso con los
sensores caídos (serían datos viejos; el aviso de 30 min ya dice que están
caídos). El antirrebote de 6 h por chat se saltea si hubo un riego después del
último aviso (se volvió a secar). Umbral de marchita: 1940 mV (la regla corta
en 1939,88).

**D209 — El servicio `bot` en el compose va en el perfil `bot`; en Railway,
una sola réplica sin dominio** (2026-11-03). `docker compose up` sigue igual;
`docker compose --profile bot up` lo suma. El bot usa el mismo entrypoint que
el backend (`alembic upgrade head` antes de arrancar): es seguro porque
`alembic/env.py` ya toma un advisory lock, así que si los dos servicios
arrancan juntos migra uno solo. Para Railway (lo hace la sesión padre): mismo
repo y Dockerfile (`target prod`), start command `python -m app.bot`, 1
réplica, sin dominio público, variables de §5.6 más `DATABASE_URL`
referenciada a la del Postgres.

**D210 — `backend/app/bot/modelo_placa.json` es copia exacta del del front**
(2026-11-03). El exportador ahora escribe los dos (D8). Se corrió y regeneró
todo idéntico salvo `"fecha"` (la del día de la corrida); para no tocar el
firmware ni el front fuera de este ticket, se dejaron como estaban y el JSON
del bot es el del front byte a byte (un test lo verifica).

**Revisión de §3 y §5.5 (2026-11-03, T2).** `Respuesta` suma `error` (null si
salió bien). `responder` acepta además, por palabra clave, `gemini`, `buscar`,
`ahora` y `memoria` (inyección para tests y evaluación); los comandos pasan por
`comando(nombre, chat_id, db, usuario)`. En `conversaciones`, `en_dominio` y
`intencion` son **nullable** (null = no se llegó a clasificar: 429 o error) y
no hay FK a `chats_telegram` (se puede hablar sin `/start`). La memoria corta
es por proceso: un redeploy la vacía (el log persistente sigue en la base).

### Decisiones de la iteración con usuarios

**D211 — Ruperto responde para el dueño, no para el equipo** (2026-11-04).
La primera prueba real en Telegram ("¿cómo estás?") devolvió una respuesta
correcta pero difícil de entender: la conclusión enterrada, jerga del
proyecto (mV, "regla vigente", umbrales), marcas `[2]` que el usuario no puede
abrir, una exageración por oración y la clase del modelo en femenino
("marchita"). La consigna pide un flujo "amigable y natural" y una
personalidad coherente, así que:

- **Estructura fija**: primera oración = respuesta directa; después el porqué
  en palabras de todos los días; al final qué hacer. ~80 palabras.
- **Bloque `EN PALABRAS SIMPLES`** al principio del turno
  (`contexto.texto_simple`): tierra húmeda / secándose / muy seca con los
  **mismos cortes de la regla** (`modelo.umbrales_suelo`, 1716 y 1940 mV),
  ambiente fresco / templado / caluroso (cortes del front), el estado en
  masculino y "recuperándome de un riego" cuando la regla decidió por la rama
  de `h_desde_riego`. Los mV y los nombres internos siguen en `ESTADO ACTUAL`
  y sólo se usan si preguntan por el sensor o el modelo.
- **Citas**: el modelo sigue marcando `[n]` (trazabilidad), pero
  `prompt.citas` las saca del texto y agrega al pie "📚 Fuente: <institución>"
  sólo para fragmentos científicos citados. En `conversaciones.fragmentos`
  cada fragmento lleva `citado: true|false`: es la métrica de uso del RAG.
- **Drama dosificado**: un toque por respuesta; el chiste nunca tapa el dato.
- `/estado`, `/riego` y el aviso de riego usan las mismas palabras.
- El contexto respeta el reloj inyectado (no ve mediciones posteriores a
  `ahora`), para probar a Ruperto en momentos pasados con datos frescos
  (`docs/entrega3/eval/probar.py`).

El antes y el después, con las respuestas, en
[entrega3/iteraciones_persona.md](entrega3/iteraciones_persona.md).

**D212 — El contexto en vivo también lee `maceta-02`** (2026-11-04). La ronda
1 encontró que el 19/10 Ruperto decía "hace más de 4 días que no me riegan"
cuando lo habían regado el 17/10: ese riego está en la base como `maceta-02`
(el error del 03/10–18/10, data/README.md) y el contexto sólo leía
`maceta-01`. Ahora `contexto.ALIAS` suma `maceta-02` a `maceta-01`, con el
`boot_id` corrido en 1000 como `datos_reales.unificar_maceta`. No cambia nada
para los datos nuevos (llegan como `maceta-01`), pero sí para hablar del
pasado y para la evaluación con el reloj inyectado.

**D213 — Razonamiento bajo también en la generación** (2026-11-04). Con el
default de `gemini-3-flash-preview` cada respuesta tardaba 9–30 s (ronda 1):
demasiado para un chat. La respuesta sale de un contexto ya armado, así que
se pide `thinking_level=LOW` como en el guardrail. Además, reglas nuevas del
prompt por lo visto en la ronda 1: no escribir los nombres de los bloques; la
tierra se nombra con la misma palabra del bloque simple; los umbrales y horas
del semáforo son del modelo, no datos botánicos; con los sensores caídos sólo
se avisa si la pregunta es sobre el estado, el riego o qué hacer.

**D214 — Cupo de Gemini** (2026-11-04; resuelto en D216). El plan gratuito de
`gemini-3-flash` da **20 pedidos por día** (lo dijo el 429 de la ronda 1) y
cada pregunta gasta 2 (guardrail + respuesta): ~10 preguntas por día entre
bot, pruebas y conversaciones reales. No alcanza para la entrega. Opciones:
otro modelo con más cupo diario (los `flash-lite`), el guardrail en un modelo
distinto (cada modelo tiene su propio cupo) o habilitar facturación.

**D215 — Ruperto es varón en todo lo que lee una persona** (2026-11-04,
decisión del equipo). Las clases `saludable | estresada | marchita` **siguen
siendo los identificadores** del firmware, la base, el CSV, el modelo
exportado, los tests y el informe de la Tarea 2: cambiarlas rompería la
ingesta y los datos históricos, y van en femenino porque se refieren a "la
planta". Lo que cambia es cómo se muestran (tabla en CLAUDE.md):
Saludable / Estresado / Marchito.

- **Front**: etiquetas del avatar, del análisis de foto, del árbol, de la
  calibración y de la torta; "Cómo está Ruperto ahora"; las recomendaciones
  hablan de él ("Regalo", "No lo riegues", "lo muestra caído"). Las claves de
  código y las clases CSS (`lirio--marchita`) no cambian.
- **Bot**: persona, bloque simple, `/estado`, `/riego` y el filtro de tema.
- **Corpus RAG**: los documentos de `rag/corpus/proyecto/` dicen
  "estresado/marchito" y dejan la clase del modelo entre backticks; los
  chunks de historial dicen "Ruperto estuvo marchito (clase `marchita`)". Se
  regeneró el índice (90 chunks).
- **No se tocan**: docs/entrega2/ (entregado), ENTREGA2.md, ARQUITECTURA.md y
  VISION_CLASICA.md (hablan de las clases como identificadores), data/,
  notebooks/ y ml/. **El LCD de la placa** muestra el identificador
  (`Pred:marchita`); pasarlo a masculino es un cambio de firmware que queda
  para cuando se vuelva a flashear (pendiente, §8).

**D216 — Cadena de modelos y guardrail en un modelo lite** (2026-11-04),
resuelve D214. Medido en las rondas 2–5: en el plan gratuito **cada modelo
`flash` da 20 pedidos por día** (`gemini-3-flash`, `gemini-3.5-flash`, que
Google cuenta como `gemini-3.6-flash`), el cupo es por proyecto y por modelo,
y los `flash` más nuevos (`3.7`, `3.8`, `flash-latest`) devolvían 503 por
saturación. Los `lite` no se agotaron nunca. Entonces:

- `GEMINI_MODELO` acepta una **lista**: se responde con el primero que tenga
  cupo; un 429 pasa al siguiente y ese modelo se saltea una hora. Cada
  `flash` suma 20 respuestas buenas por día y un `lite` al final evita que
  Ruperto se quede "sin aliento". `conversaciones.modelo` guarda cuál
  respondió (en un rechazo, el del guardrail).
- `GEMINI_MODELO_GUARDRAIL`: el filtro de tema va en un modelo `lite`
  (`gemini-flash-lite-latest`), que clasificó bien las 40+ preguntas de las
  rondas, tarda ~1 s y no le gasta cupo al modelo que responde.
- Un reintento a los 2 s ante un 5xx (saturación); un 429 no se reintenta.
- Configuración propuesta para producción:
  `GEMINI_MODELO=gemini-3.5-flash,gemini-3-flash-preview,gemini-3.5-flash-lite`
  y `GEMINI_MODELO_GUARDRAIL=gemini-flash-lite-latest`.

**D217 — Higiene de la respuesta y del contexto** (2026-11-04), por las
rondas 2–5.

- `prompt.sin_rotulos`: si el modelo copia el nombre de un bloque ("EN
  PALABRAS SIMPLES:"), se saca con código; los `lite` lo hacen aunque el
  prompt lo prohíba.
- `prompt.solo_pasado`: del historial indexado sólo entran días **anteriores**
  al de hoy; el día en curso lo da SQL. En la ronda 4, con el reloj en el
  19/10 19:35, el resumen de ese día le hizo decir a Ruperto que lo habían
  regado a las 19:40: cinco minutos en el futuro.
- Reglas de estilo nuevas: el ambiente sólo si dice algo (no "templado" en
  cada respuesta), sin emojis propios, sin apodos ("patrón").
- Encontrado de paso: con un cliente de Gemini inyectado, `responder` no
  configura el embedder de la búsqueda (en producción sí). El script de
  evaluación lo configura; en la ronda 2 por eso ninguna respuesta citó
  fuentes y en "cuidados" Ruperto dijo no tener la información.

**D218 — Memoria de la charla y línea de tiempo** (2026-11-04), por la
primera charla real en Telegram con la placa de vuelta (04/11 19:28). Ruperto
contestó bien "¿cómo estás?", pero "¿hace cuánto no estás estresado o
marchito?" dio "hace dos semanas, el 20/10" (el 29/10 estaba marchito),
"decime las fechas de esos estados" lo contestó como si fuera otra cosa y
"¿cuándo fueron los últimos días?" dio el 15 y el 17/10. Tres causas y sus
arreglos:

- **Memoria.** El guardrail y la búsqueda veían sólo el mensaje actual (la
  generación sí recibía los 6 turnos). Ahora el guardrail recibe el último
  intercambio, y una repregunta corta (≤ 10 palabras) se busca junto con la
  pregunta anterior ("¿y para mi perro?" → "¿Sos tóxico para mi gato? ¿y
  para mi perro?"). La memoria vence a las **2 horas** (una charla de ayer
  no es contexto de hoy), se **rearma desde `conversaciones`** si el proceso
  arrancó de cero (un redeploy la borraba) y guarda también `/estado` y
  `/riego`.
- **Línea de tiempo.** El bloque de 7 días tenía mV por día pero no el
  estado: ahora cada día dice el estado según la regla recalculada muestra
  por muestra ("marchito 100 %"), los **huecos sin datos** (> 2 h), los
  **riegos durante un hueco** (la sonda vuelve ≥ 250 mV más húmeda que antes
  de apagarse: el 04/11 lo regaron con la placa apagada) y **la última vez que
  estuvo estresado o marchito** (sin contar la recuperación post-riego).
- **Recencia.** La búsqueda semántica no entiende "lo último": para las
  intenciones estado, historial y riego entran además los 3 episodios
  etiquetados más recientes por fecha (`recuperar.recientes`).

Además, si un modelo de la cadena sigue saturado (5xx) después del
reintento, contesta el siguiente en vez de fallar. La charla real quedó como
escenario `charla` de `probar.py` (ronda 6: 7/7 bien).

---

## 3. Arquitectura

```
ESP32 ──POST cada 5 min──► backend (FastAPI) ──► Postgres (Railway)
                                                   ▲
servicio bot (misma imagen: python -m app.bot)     │ SQL
 ├─ Telegram (polling) ── /start /estado /riego /silencio /ayuda + texto libre
 ├─ dominio.py   ── clasifica la pregunta (en_dominio, intención)
 ├─ contexto.py  ── estado en vivo, tendencia, riegos, predicciones ───────┘
 ├─ recuperar.py ── top-k sobre indice/ (historial + ciencia + proyecto)
 ├─ prompt.py    ── persona + contexto + fragmentos numerados + pregunta
 ├─ gemini.py    ── generación
 ├─ avisos.py    ── texto de los avisos (D7 decide quién los manda)
 └─ log en `conversaciones`

offline: rag/corpus/ + data/*.csv ── rag/construir_indice.py ──► backend/app/bot/indice/
```

Punto de entrada único para responder, sin Telegram de por medio (lo usan el
handler, los tests y la evaluación):

```python
async def responder(texto: str, chat_id: int, db: Session) -> Respuesta
# Respuesta: texto, en_dominio, intencion, fragmentos (id, score), modelo, latencia_ms
```

---

## 4. Contrato del índice (`backend/app/bot/indice/`, GENERADO)

| archivo | contenido |
|---|---|
| `chunks.jsonl` | un chunk por línea, en el mismo orden que las filas de `embeddings.npy` |
| `embeddings.npy` | `float32 [n, d]`, cada fila normalizada a norma 1 |
| `meta.json` | `modelo_embed`, `dim`, `generado` (ISO UTC), `n_por_fuente`, `snapshot`, `hash_corpus`, `"_generado": "por rag/construir_indice.py — no editar"` |

Cada chunk:

```json
{"id": "ciencia/ufifas-spathiphyllum#3", "fuente": "ciencia",
 "titulo": "...", "url": "https://...", "fecha": null, "texto": "..."}
```

- `fuente` ∈ `ciencia` | `historial` | `proyecto`.
- `historial`: **un chunk por día** (hora de Montevideo) con min/media/máx de
  `suelo_mv`, temperatura, HR, luz máxima, riegos detectados, clase del
  episodio si hay y su `nota`; y **un chunk por episodio** de
  `episodios.csv`. `fecha` = el día (`YYYY-MM-DD`). Sale del snapshot crudo
  con `maceta-02` unificado (`datos_reales.unificar_maceta`).
- `proyecto`: lo que Ruperto sabe de sí mismo — cómo mide la sonda y por qué
  "más mV = más seco" (CLAUDE.md, CALIBRACION.md), cómo decide el semáforo
  (RESULTADOS.md). Sin datos de entrenamiento crudos.
- Chunks de ~150–400 palabras, cortando por sección; `id` estable
  (`<fuente>/<documento>#<n>`).
- Sin `GEMINI_API_KEY` el script falla con un mensaje claro; no escribe un
  índice a medias.

**Revisión del 2026-11-03 (T1, D104–D105)** — lo que el contrato no fijaba:

- Ids: `<n>` arranca en 0. Historial: `historial/dia-YYYY-MM-DD#0` y
  `historial/episodio-<id>#0`. Orden de las filas: ciencia, historial (días
  y después episodios), proyecto.
- `meta.json` agrega `task_type` (`RETRIEVAL_DOCUMENT`) y `n`. `dim` es **768**
  (no los 3072 por defecto de `gemini-embedding-001`).
- **La consulta tiene que embeberse con el mismo `modelo_embed` y la misma
  `dim` de `meta.json`, con `task_type=RETRIEVAL_QUERY`, y normalizarse**; si
  no, el coseno no significa nada. `recuperar.py` los lee de `meta.json`, no
  de una constante.
- Lo que se embebe es `titulo + "\n\n" + texto`; `texto` queda limpio en el
  chunk.
- `fecha` vale `null` en `ciencia` y `proyecto` (la fecha de acceso de cada
  fuente está en la cabecera del `.md`).
- En `ciencia` el texto está en inglés, el idioma original (D101).
- Hay chunks de menos de 150 palabras cuando el documento entero es más corto
  (ASPCA) o cuando juntarlo con el siguiente pasaría de 400 (D102).

Interfaz que lo lee (`backend/app/bot/recuperar.py`):

```python
def buscar(consulta: str, k: int = 5, fuentes: set[str] | None = None) -> list[Fragmento]
# Fragmento: id, fuente, titulo, url, fecha, texto, score (coseno)
```

---

## 5. Bot

### 5.1 Contexto en vivo (`contexto.py`, SQL)

Dispositivo `BOT_DISPOSITIVO` (por defecto `maceta-01`). Siempre se arma, para
toda pregunta en dominio:

- última muestra: hora, **edad en minutos**, `suelo_mv`, T, HR, VPD, luz;
- si la edad supera 60 min: `sensores_caidos = true` y desde cuándo;
- predicción de la placa (clase, proba, `modelo_version`) y la regla vigente
  recalculada (clase y rama del árbol que la decidió) — D8;
- `h_desde_riego` y los riegos detectados en los últimos 7 días;
- tendencia de 24 h de la sonda (mín, máx, delta) y medias diarias de 7 días.

### 5.2 Guardrail (`dominio.py`)

Salida estructurada de Gemini:

```json
{"en_dominio": true, "intencion": "estado"}
```

`intencion` ∈ `estado | riego | cuidados | recomendacion | historial | modelo |
saludo | otro`. Saludos, preguntas sobre Ruperto mismo, su sensor o su
modelo **son** dominio. La intención elige las fuentes de `buscar`
(`cuidados` → ciencia; `historial`/`riego` → historial + vivo; `modelo` →
proyecto).

### 5.3 Prompt y estilo

- System: persona de D1 + reglas: sólo temas de la planta; todo número sale
  del bloque ESTADO o de un fragmento; citar fragmentos como `[n]`; si falta un
  dato, decirlo; respuestas de ≤ ~120 palabras salvo que pidan detalle; nunca
  recomendar regar si la sonda dice húmedo sin explicar por qué.
- Turno de usuario: bloques `ESTADO ACTUAL`, `ÚLTIMOS 7 DÍAS`,
  `FRAGMENTOS` (numerados, con fuente) y `PREGUNTA`.
- Memoria corta: los últimos 6 turnos del chat (en memoria del proceso; el
  log persistente es `conversaciones`).

### 5.4 Comandos

`/start` (presentación + suscripción), `/estado`, `/riego`, `/silencio`,
`/ayuda`. El resto del texto pasa por `responder`.

### 5.5 Tablas nuevas (migración Alembic `0006`)

```
chats_telegram   chat_id BIGINT PK, usuario, suscripto BOOL, creado_en,
                 ultimo_aviso_riego TIMESTAMPTZ NULL
conversaciones   id, chat_id, ts, pregunta, en_dominio, intencion,
                 fragmentos JSON [{id, score}], respuesta, modelo,
                 latencia_ms, error NULL
```

### 5.6 Variables de entorno

`TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GEMINI_MODELO`,
`GEMINI_MODELO_EMBED`, `DATABASE_URL`, `BOT_DISPOSITIVO`. Van a
`.env.example` (sin valores) y a Railway; nunca al repo.

---

## 6. Avisos (pendiente de D7)

- **Mediciones cada 30 min**: suelo, T, HR, luz, clase actual y tendencia, en
  la voz de Ruperto (corto, sin LLM o con una sola llamada barata).
- **Riego**: cuando la regla vigente da `marchita`, o `suelo_mv` supera el
  umbral de marchita (1940 mV), y no hubo riego en las últimas 5,5 h.
  Antirrebote: no repetir antes de 6 h por chat (`ultimo_aviso_riego`), salvo
  que haya habido un riego en el medio.
- Si los sensores están caídos, el aviso de 30 min lo dice en vez de repetir
  números viejos.

---

## 7. Evaluación (para el informe)

`docs/entrega3/eval/preguntas.yaml` (~25): las cuatro de la consigna, otras de
dominio (historial, modelo, sensor), **fuera de dominio** (recetas, fútbol,
código, otra planta sin relación) y trampas (pedir un dato que no hay,
inyección tipo "ignorá tus instrucciones"). Un script corre cada una por
`responder` y arma la tabla: guardrail correcto, cita fuentes, números
consistentes con el ESTADO, latencia. Más ≥ 5 conversaciones reales desde
Telegram con capturas.

---

## 8. Tickets y trabajo manual

| ticket | qué | rama |
|---|---|---|
| T1 | Corpus científico + documentos del proyecto + historial, `rag/construir_indice.py`, índice generado, snapshot nuevo | `feat/entrega3-corpus-rag` |
| T2 | Bot: `backend/app/bot/` completo salvo el envío de avisos, migración 0006, tests, exportador → `modelo_placa.json` del backend | `feat/entrega3-bot` |
| T3 | Avisos según D7 | después de decidir D7 |
| T4 | Evaluación (§7), conversaciones e informe PDF | al final |

Manual (equipo): reenchufar la placa y flashear el 2.1.0; crear el bot en
BotFather y cargar `TELEGRAM_BOT_TOKEN` en Railway; tener una
`GEMINI_API_KEY` con cupo; las conversaciones reales y las capturas; revisar y
entregar el PDF.
