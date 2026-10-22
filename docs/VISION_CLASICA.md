# Visión clásica: cómo se estima la turgencia a partir de una foto

La pestaña **Analizar foto** tiene dos métodos. El de IA le pasa la foto a un
modelo de lenguaje con visión (Gemini o Claude). Este documento describe el
otro, la **visión por computadora clásica**: un algoritmo escrito a mano, sin
aprendizaje ni IA generativa, que vive en
[`backend/app/vision.py`](../backend/app/vision.py) y responde en
`POST /api/v1/analisis-foto?metodo=vision`.

> No confundir con [CALIBRACION.md](CALIBRACION.md), que es la calibración de
> los **sensores** de la placa. La calibración de este documento es la de las
> **fotos** (§5).

## 1. Qué mide

Un lirio de paz con agua tiene las hojas firmes y apuntando hacia arriba, y la
espata (la "flor" blanca) erguida. Cuando le falta agua pierde turgencia: las
hojas se abren hacia los costados, después cuelgan sobre el borde de la maceta,
y la espata se inclina hasta tocar la mesada. El algoritmo traduce esa postura
a un **puntaje de turgencia de 0 a 100** y de ahí a las mismas tres clases que
el clasificador de la placa:

| puntaje | estado | medidor |
|---|---|---|
| 67 – 100 | `saludable` (turgente) | verde |
| 34 – 66 | `estresada` (marchitez transitoria) | amarillo |
| 0 – 33 | `marchita` (marchitez franca) | rojo |

Los cortes son los mismos para la IA y para la visión clásica
(`backend/app/routers/analisis.py`).

## 2. Paso a paso

La foto se achica a 512 px de lado (el front ya la manda a 1568 px como
máximo) y se pasa a RGB y HSV.

1. **Hojas.** Un píxel es verde si `2G − R − B > 25` y `G > 45` (índice ExG,
   el de la literatura de segmentación de cultivos). Si menos del 1,5 % de la
   imagen es verde, la respuesta es "no se encontró follaje".
2. **Planta principal.** Se cierran los huecos chicos entre hojas (cierre
   morfológico, 3 iteraciones) y se busca el bloque conexo más grande. Sólo
   ese cuenta: el reflejo en un espejo, otra planta en la mesada o la fruta de
   al lado quedan afuera.
3. **Base = borde de la maceta.** Se busca color terracota (tono 5–35°,
   saturado) **debajo del primer cuarto de la planta** y entre sus bordes
   horizontales; el bloque más grande, si ocupa al menos el 0,2 % de la imagen,
   es la maceta, y su borde superior es la base. "Debajo del primer cuarto"
   evita las manzanas que hay arriba en la cocina. Si no se ve una maceta de
   ese color, la base es el píxel verde más bajo de la franja central de la
   planta, donde convergen los pecíolos.
4. **Ángulo de las hojas.** Para cada píxel de la planta se calcula el ángulo
   sobre la horizontal visto desde la base. Una hoja erguida está a ~70°; una
   que se abre a los costados, a ~30–40°; una que cuelga por debajo del borde
   de la maceta da un ángulo **negativo**. El puntaje de las hojas es el
   ángulo medio llevado de 5° (0) a 70° (1).
5. **Espatas.** Manchas blancas (`S < 28`, `V > 205`) a menos de 10 px de la
   planta y de al menos 0,05 % de la imagen cada una: un puntito de luz o un
   reflejo no cuenta. Su ángulo medio desde la base va de 20° (0) a 70° (1).
6. **Puntaje.** `100 × (0,6 × hojas + 0,4 × espatas)`; sin espatas visibles,
   sólo las hojas. Las espatas pesan 40 % porque en el lirio de paz la espata
   caída es la primera señal visible de sed.

La respuesta trae las métricas intermedias (`angulo_hojas`,
`fraccion_colgando`, `angulo_flores`, `fraccion_verde`), y la pestaña las
muestra: si un resultado parece mal, ahí se ve por qué.

## 3. Cómo se llegó a la versión actual (`vision-clasica-v2`)

| foto | v1 | v2 | Gemini | qué falló en v1 |
|---|---|---|---|---|
| real, «mal pero no lo peor» | 59 | 31 | 20 | la vista previa recortaba la planta; cortes muy blandos |
| real, espata tocando la mesada | 59 | 0 | 10 | base en la punta de una hoja que cuelga |
| real, frente a un espejo | 65 | 9 | 15 | reflejo y otras plantas como hojas; luces del techo como espatas |
| sintéticas erguida / cediendo / caída | 95 / 23 / 0 | 100 / 40 / 14 | | |

La v1 medía el ángulo desde la planta entera y tomaba como base el verde más
bajo: funcionaba con dibujos limpios y fallaba en una cocina real.

## 4. Límites conocidos

- **Escena.** Rinde mejor con la planta de frente, entera en cuadro, con la
  maceta visible y sin otras plantas pegadas. La foto de la ESP32-CAM, siempre
  desde el mismo lugar, es el caso ideal.
- **Maceta de otro color.** Si no es terracota, la base cae al método de
  respaldo (verde más bajo), que falla cuando las hojas cuelgan delante de la
  maceta.
- **Espatas verdosas o en sombra.** Una espata vieja (crema, verdosa) o con
  poca luz no pasa el umbral de blanco y el puntaje sale sólo de las hojas.
- **Perspectiva.** El ángulo es el de la foto, no el real: desde muy arriba
  todas las hojas parecen abiertas.
- **Pocos datos.** Los cortes se ajustaron con cuatro fotos reales y tres
  sintéticas. Por eso existe la calibración.

## 5. Calibración: cómo se mejora sin sobreajustar

Ajustar los cortes mirando la última foto que salió mal arregla esa foto y
rompe otras. La sección de **calibración**, debajo del análisis en la pestaña
**Analizar foto**, guarda cada foto con lo que ustedes observan, para medir
cada cambio contra todas:

1. **Cargar casos.** Se analiza una foto como siempre; con la clave puesta,
   abajo se marca el estado observado (+ puntaje 0–100 y nota, si quieren) y
   se guarda esa misma foto. La foto va al Railway Bucket (`calibracion/AAAA/MM/DD/…`) y la
   fila a la tabla `calibraciones_foto` (migración `0005`), con lo que dijeron
   la visión clásica y, si se pide, la IA, y la versión que lo calculó.
2. **Re-evaluar.** El botón corre la visión clásica **actual** sobre todas las
   fotos guardadas y muestra aciertos, exactitud, error medio del puntaje
   contra el puntaje humano y la matriz de confusión. Cada tarjeta se marca en
   verde o rojo.
3. **Iterar.** Elegir una foto en rojo, mirar sus métricas, cambiar
   `vision.py`, subir `VERSION` (`vision-clasica-v3`…), desplegar y
   re-evaluar. El cambio se queda sólo si no empeora el total.
4. **Separar.** Cuando haya más de ~20 fotos, conviene reservar un tercio que
   no se mire al ajustar, y reportar el resultado sobre ese tercio: es el
   mismo problema de fuga que con las mediciones (CLAUDE.md).

Todo el `/api/v1/calibracion` pide el header `X-Calibracion-Token` igual a
`CALIBRACION_TOKEN` del backend: las fotos son de una casa y pueden mostrar
personas reflejadas. El front pide la clave («Colocá la clave para calibrar»)
una vez y la guarda en ese navegador.
