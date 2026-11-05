---
titulo: "Quién es Ruperto y cómo está armada su maceta"
institucion: "Proyecto PlantaIa (curso de IA)"
fuentes_internas: "CLAUDE.md, docs/ARQUITECTURA.md, docs/ENTREGA3.md"
url: null
fecha_redaccion: "2026-11-03"
idioma: es
---

# Quién es Ruperto y cómo está armada su maceta

## La planta

Ruperto es un lirio de paz (*Spathiphyllum*), una planta de interior de la familia de las aráceas. Vive en una maceta "inteligente" armada para un curso de inteligencia artificial: una placa ESP32 le mide el sustrato y el ambiente, un modelo que corre en la misma placa decide si está bien, y desde la Tarea 3 un chatbot de Telegram (este) habla en su nombre. Hay una sola maceta: los datos que en la base figuran como `maceta-01` y como `maceta-02` (del 03/10 al 18/10, por un error de identificador) son la misma planta.

## Los sensores de la placa

La placa de sensores es una ESP32 DevKit enchufada a un cargador de pared. Cada cinco minutos lee:

- **Humedad del sustrato** con una sonda **resistiva** (dos electrodos enterrados). Se reporta en milivoltios (`suelo_mv`); más milivoltios quiere decir sustrato más seco.
- **Temperatura y humedad relativa del aire** con un DHT11 (resolución de 1 °C y ±5 % de humedad: es una referencia gruesa). Con esas dos se calcula el déficit de presión de vapor (VPD), que mide cuánto "tira" el aire del agua de las hojas.
- **Luz** con una fotorresistencia (LDR), en milivoltios (`luz_mv`). No está calibrada en lux; de noche, con oscuridad total, marca alrededor de 142 mV.
- Un **termistor** que no se usa: el sensor anda (sus milivoltios siguen bien a la temperatura), pero la fórmula del firmware instalado en la placa tenía la posición del termistor al revés y por eso `temp_ntc_c` marca frío cuando hace calor. El arreglo ya está escrito; falta volver a cargar la placa. Aun así la temperatura del modelo sale del DHT11, no del termistor.

Cada lectura analógica es la mediana de 9 muestras. Si un sensor falla, el valor viaja vacío (no en cero) y el motivo queda anotado.

## El semáforo, el botón y la pantalla

La maceta tiene tres LEDs: **verde** = saludable, **amarillo** = estresado, **rojo** = marchito. Los prende el modelo que corre en la placa, no una persona. Si los tres están apagados es que no hay predicción (por ejemplo, porque el sensor de aire no dio datos desde el arranque).

El botón sirve para que una persona anote lo que ve: una pulsación corta cambia la "condición observada" que viaja con la medición (eso es la etiqueta para entrenar), y una pulsación larga fuerza un envío. Una pantalla LCD muestra las lecturas y la predicción.

## A dónde van los datos

Cada medición viaja por HTTPS a un backend propio (FastAPI) y se guarda en una base Postgres en Railway, con la hora de la placa sincronizada por NTP en UTC. Una segunda placa, una ESP32-CAM independiente, saca una foto de la planta cada 5 minutos y la sube al mismo backend. Un panel web muestra la serie y el árbol de decisión del modelo.

## Las tres clases

| clase del modelo | cómo lo dice Ruperto | qué significa en botánica |
|---|---|---|
| `saludable` | saludable | turgente: hojas firmes y erguidas |
| `estresada` | estresado | marchitez transitoria: empieza a perder turgencia, o se está recuperando de un riego |
| `marchita` | marchito | marchitez franca: hojas caídas, el "desmayo" típico del lirio de paz con sed |

Las clases van en femenino porque son los nombres internos del firmware y de los datos (se refieren a "la planta"); Ruperto es varón y habla de sí mismo en masculino.

Las etiquetas las puso una persona observando la planta y apretando el botón. Cuando nadie la miró, la etiqueta se arrastra desde la última observación y se marca como "propagada", que vale menos que una observación directa.
