# Calibración de sensores

Los valores que están hoy en `firmware/src/main.cpp` son **de ejemplo**. Hasta
que se completen las tablas de abajo, `suelo_pct` y `luz_pct` son indicativos
para el LCD y **no deben usarse como feature del modelo** — para eso están
`suelo_raw`/`suelo_mv` y `luz_raw`/`luz_mv`, que viajan crudos en cada muestra.

---

## 1. Sonda de suelo (resistiva)

### Por qué importa más de lo que parece

Los electrodos se corroen. La misma humedad real se lee distinto en la semana 3
que en la semana 1, y como la condición de la planta **también** progresa con el
tiempo, la deriva del sensor puede meterse en el modelo como si fuera señal.
Es el riesgo metodológico más serio del montaje.

Por eso la calibración no se hace una vez: se repite **todos los lunes** y queda
registrada acá, para poder corregir la deriva a posteriori en el notebook.

### Procedimiento (5 minutos)

1. Placa andando, monitor serie abierto.
2. **Seco:** sonda al aire, limpia y seca. Esperar 3 lecturas. Anotar `suelo_mv`.
3. **Mojado:** sonda en un vaso de agua hasta la marca de inmersión. Esperar 3
   lecturas. Anotar `suelo_mv`.
4. Secar bien la sonda antes de volver a la maceta.
5. Actualizar `SUELO_MV_SECO` y `SUELO_MV_MOJADO` **solo la primera vez**. En las
   semanas siguientes **no tocar el firmware**: anotar el valor y corregir en el
   análisis. Si se cambia la constante a mitad de la recolección, se parte la
   serie en dos tramos incomparables.

### Registro

| Fecha | `suelo_mv` seco | `suelo_mv` mojado | Δ | Aspecto de los electrodos | Quién |
|---|---|---|---|---|---|
| _(pendiente)_ | | | | | |

Una caída sostenida de Δ entre semanas es la firma de la corrosión. Si Δ baja
más de ~30 % respecto de la primera medición, la sonda ya no sirve y hay que
anotar el corte en el dataset.

### Curva de asentamiento (una sola vez)

Para confirmar que 100 ms alcanza y que no conviene alargarlo:

1. Con la sonda enterrada, encender GPIO33 y tomar `suelo_mv` cada 20 ms durante
   2 segundos, sin cortar la alimentación.
2. Esperado en una sonda resistiva: sube al valor final en pocos milisegundos y
   después **deriva lentamente hacia abajo** — esa bajada es la electrólisis.
3. Si la curva se comporta así, queda confirmado que alargar la estabilización
   empeora el dato. Anotar el resultado acá.

_(resultado: pendiente)_

---

## 2. LDR (luz)

`LUZ_MV_MAX 3300` es inalcanzable: el ADC del ESP32 con atenuación 11 dB satura
cerca de 3100 mV y la curva se aplasta arriba de ~2500 mV. `luz_pct` nunca llega
a 100 y está comprimido justo en el rango de luz fuerte.

No se corrige subiendo o bajando la constante a ojo, porque el problema es la
no linealidad, no el tope. Se resuelve en el análisis, a partir de `luz_mv`.

### Procedimiento

Registrar `luz_mv` en las cuatro escenas de luz del diseño experimental, para
poder derivar `luz_nivel` (categórico) en vez de un porcentaje lineal de un
sensor logarítmico:

| Escena | `luz_mv` observado | Notas |
|---|---|---|
| `velo_abierto` | _(pendiente)_ | día claro, mediodía |
| `velo_cerrado` | _(pendiente)_ | |
| `pantalla` | _(pendiente)_ | |
| `lampara` | _(pendiente)_ | |
| oscuridad total | _(pendiente)_ | de noche, luces apagadas |

Con esos cinco puntos se definen los cortes de `luz_nivel` en el notebook.

---

## 3. Termistor NTC

El divisor asume `NTC_VCC 3300`, `R_FIJO 10 k`, `BETA 3950`. Verificación mínima:
comparar `temp_ntc_c` contra `temperatura_c` del DHT11 en régimen estable.

| Fecha | `temp_ntc_c` | `temperatura_c` (DHT) | Δ | Notas |
|---|---|---|---|---|
| _(pendiente)_ | | | | |

Una diferencia constante es un offset corregible. Una diferencia que crece con la
temperatura significa que el BETA nominal no es el del componente real.

> El DHT11 tiene resolución de 1 °C y ±5 % en humedad. Sirve como referencia
> gruesa y para calcular VPD, pero no es patrón de nada.
