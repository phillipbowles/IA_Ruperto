# Calibración de sensores

La calibración de la sonda de suelo sigue pendiente. Hasta que se complete la
tabla de abajo, `suelo_pct` es indicativo para el LCD y **no debe usarse como
feature del modelo** — para eso están
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

### Observado en el dataset del 12–17/09/2026

No reemplaza la medición de banco de arriba —eso hay que hacerlo con la sonda en
la mano— pero acota el rango real de la serie ([notebooks/01_eda.ipynb](../notebooks/01_eda.ipynb),
secciones 1 y 5):

| | `suelo_mv` | Nota |
|---|---|---|
| Mínimo observado | 996 | Sustrato recién regado |
| Máximo observado | 3124 | **Es el techo del ADC**, no una medición: la sonda saturó en 78 muestras |
| Riego del 16/09 | 3124 → 1750 | En menos de 6 minutos. Es la respuesta más limpia del sensor en todo el dataset |

Que el extremo seco esté clavado en el techo significa que **`SUELO_MV_SECO` debe
fijarse en 3124 o menos**: cualquier valor por encima es inalcanzable y deja
`suelo_pct` sin definir, que es exactamente lo que pasó —el 98 % de las filas
llegaron con `suelo_pct` en `null`.

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

**Siguen pendientes porque nunca se registraron eventos de escena de luz**: sin
la tabla `eventos` no hay forma de saber qué escena corresponde a cada muestra.
Lo que sí se puede acotar desde el dataset del 12–17/09/2026:

| | p05 | mediana | p95 |
|---|---|---|---|
| De noche (20 h – 07 h) | 142 | 153 | 1451 |
| De día | 147 | 2659 | 3124 |

La oscuridad total se lee alrededor de **142–155 mV** —ese es el piso del
divisor, no cero— y el extremo alto está **censurado en 3124 mV**: 370 muestras
exactamente en el techo y 727 marcadas por el firmware con `luz_saturada`. Los
p05 casi iguales de día y de noche confirman que hubo horas diurnas con el velo
cerrado y la habitación a oscuras.

Conclusión operativa: desde el firmware 2.1.1, `LUZ_MV_MAX` se fijó en 3124 mV,
el techo observado del ADC. Esto mejora el porcentaje mostrado en el LCD, pero
**no arregla la compresión** en el rango alto, que viene de la respuesta
logarítmica del LDR. Para el modelo hay que derivar `luz_nivel` categórico.

---

## 3. Termistor NTC

El divisor asume `NTC_VCC 3300`, `R_FIJO 10 k`, `BETA 3950`. Verificación mínima:
comparar `temp_ntc_c` contra `temperatura_c` del DHT11 en régimen estable.

| Fecha | `temp_ntc_c` | `temperatura_c` (DHT) | Δ | Notas |
|---|---|---|---|---|
| 2026-09-20 | −28,2 a 41,9 °C | 8,1 a 35,6 °C | mediana **+23,3 °C** | Sobre 3007 muestras del 12–17/09. Ver abajo |

Una diferencia constante es un offset corregible. Una diferencia que crece con la
temperatura significa que el BETA nominal no es el del componente real.

### El termistor está invertido, no descalibrado

**Resuelto el 2026-09-20** a partir del dataset. Los tres números que
lo definen, sobre las 2921 muestras con hora válida en que el ADC no estaba saturado:

| Medida | Valor | Qué significa |
|---|---|---|
| `corr(temp_ntc_c, temperatura_c)` | **−0,982** | La temperatura calculada sigue a la real **con el signo cambiado** |
| `corr(termistor_mv, temperatura_c)` | **+0,973** | El milivoltaje crudo, en cambio, la sigue bien |
| Rango de `termistor_mv` | 614 – 2709 mV | Recorrido amplio y sin saturar: el sensor discrimina |

Un sensor roto no correlaciona con nada. Uno descalibrado correlaciona +0,98 con
un offset o una pendiente equivocada. Este correlaciona −0,98, y el crudo
correlaciona +0,97: **el hardware anda y la fórmula recorre la curva al revés.**

La causa es la posición del termistor en el divisor. En un NTC la resistencia
baja cuando sube la temperatura; según el NTC esté del lado de VCC o del lado de
GND, `termistor_mv` sube o baja con el calor. El firmware asume una disposición y
el montaje tiene la otra.

La conversión se corrigió en el firmware 2.1.1 para el montaje
`VCC → NTC → VOUT → R_FIJO → GND` (el crudo se guardó en cada muestra, así que las
filas viejas se pueden recalcular sin volver a medir). Hasta que la placa se
vuelva a flashear, la base sigue recibiendo `temp_ntc_c` con el signo cambiado.

**Verificación con datos posteriores** (`data/mediciones_raw_2026-11-03.csv`,
`maceta-01`, ADC sin saturar). La inversión no era un efecto de los pines cruzados
que se corrigieron el 12/09: persiste igual después.

| Período | Firmware | n | `corr(temp_ntc_c, DHT)` | `corr(termistor_mv, DHT)` |
|---|---|---|---|---|
| 12–17/09 | 1.1.0 | 2 919 | −0,984 | +0,979 |
| 18/09 – 4/10 | 1.1.0 | 3 512 | −0,886 | +0,886 |
| 5–30/10 | 1.1.0 | 10 963 | −0,946 | +0,948 |

**`NTC_R0` hay que recalibrarlo.** El valor desplegado (4150) se ajustó el 12/09 con
la fórmula vieja y deja de valer con la nueva. Como el divisor sólo depende del
cociente `R_FIJO / NTC_R0`, se ajustó ese cociente por mínimos cuadrados contra el
DHT11 sobre las 14 483 muestras del 18/09 al 3/11 (DHT entre 17 y 26 °C):

| | Valor |
|---|---|
| `R_FIJO / NTC_R0` óptimo | 0,50 → `NTC_R0 = 20 000` con `R_FIJO = 10 k` |
| RMSE contra el DHT11 | 0,65 °C |
| Correlación / pendiente del modelo vs DHT11 | +0,78 / 0,73 |
| Fórmula vieja con `R0 = 4150` (lo desplegado) | corr −0,78, RMSE 6,3 °C |

Es un ajuste en un rango chico (17–26 °C) contra un DHT11 de ±2 °C y 1 °C de
resolución, con el termistor en otro punto de la maceta; la pendiente de 0,73 sugiere
que el BETA efectivo no es 3950. Sirve para cerca de la temperatura ambiente. **Falta
la verificación de banco**: un segundo punto (heladera o agua tibia) con un termómetro
de referencia, anotado en la tabla de arriba. El termistor sigue sin entrar al modelo
(contrato §4 de ENTREGA2): esto sólo afecta a `temp_ntc_c`, al log y al front.

> El DHT11 tiene resolución de 1 °C y ±5 % en humedad. Sirve como referencia
> gruesa y para calcular VPD, pero no es patrón de nada.
