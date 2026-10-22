"""Features del modelo — contrato docs/ENTREGA2.md §4, gemelo de
firmware/lib/plantaia_ml/features.{h,cpp}.

Si se toca la semántica acá, se toca allá en el mismo commit: el test de
paridad (`pio test -e native`) pasa la misma secuencia cruda por los dos y
exige el mismo vector con tolerancia 1e-3.

Semántica exacta (la del buffer circular de 13 muestras de la placa)
-------------------------------------------------------------------
Las muestras llegan cada 5 min. Un **tramo** es una corrida continua:
mismo `dispositivo` y `boot_id`, sin huecos de más de 7,5 min entre muestras
consecutivas. Al empezar cada tramo el buffer se vacía (`features_reset`), que
es lo que hace la placa al reiniciar: la ventana vive en RAM.

Por cada muestra, en orden:

1. **Suelo y luz faltantes** (NaN; el llamador pasa NaN también cuando la sonda
   está saturada, igual que `main.cpp`): se repite el último valor *empujado*
   al buffer (que a su vez puede ser una repetición). Si el buffer está vacío
   no hay con qué rellenar: la muestra **no entra** al buffer, tampoco
   actualiza T/HR, y la fila sale `valido=False`.
2. **T y HR** salen sólo del DHT11 y se siguen por separado. Si el DHT dio un
   valor válido, ese pasa a ser el "último válido" del tramo. Si no, se usa el
   último válido. Si nunca hubo T (o HR) válida en el tramo, la fila sale con
   esa feature y `vpd_kpa` en NaN y `valido=False` (no se infiere), **pero suelo
   y luz sí entran al buffer** (sirven para las muestras siguientes). El
   termistor **no** es respaldo de T (contrato §4): la conversión del firmware
   1.1.0 está invertida y, aunque estuviera bien, sin DHT tampoco hay HR.
3. Se empujan suelo y luz al buffer; `n = min(n + 1, 13)` cuenta la actual.
4. `warmup = n <= 12` (menos de 12 muestras *anteriores* a la actual).
   `suelo_delta_1h = suelo(t) − suelo(t − 12 muestras)` fuera de warm-up, y
   **0** en warm-up.
5. `luz_media_1h` = media de las `n` muestras de la ventana (≤ 13, incluida la
   actual). En warm-up usa lo que haya; en la primera muestra es la luz actual.
6. `vpd_kpa = 0.6108·exp(17.27·T/(T+237.3))·(1 − HR/100)`, sin recortar HR > 100
   (C tampoco lo recorta: un solo comportamiento que mantener).

La "1 h" son 12 pasos, no 60 minutos de reloj: dentro de un tramo los pasos
son de 5 min por construcción. En el dato remuestreado dos bins consecutivos
están a 5 min o a ≥ 10 min, y los segundos cortan el tramo; no se interpola.

Python calcula en float64; C en float32. Las entradas son mV enteros y T/HR
con un decimal, así que la diferencia queda muy por debajo de 1e-3.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

FEATURES = ["suelo_mv", "suelo_delta_1h", "temp_c", "hum_aire_pct", "vpd_kpa",
            "luz_mv", "luz_media_1h"]
N_FEATURES = len(FEATURES)
VENTANA = 13          # la actual + 12 anteriores = 1 h a 5 min
LAG_DELTA = 12
HUECO_MAX = pd.Timedelta(minutes=7.5)

# Mismos bits que FEAT_MARCA_* de features.h, para que el log de Python y el
# de la placa se puedan comparar línea a línea.
MARCA_SUELO_REPETIDO = 0x01
MARCA_LUZ_REPETIDA = 0x02
MARCA_DHT_ANTERIOR = 0x04
# 0x08 quedó libre: era el respaldo de T con el termistor, que ya no existe.
MARCA_SIN_SUELO = 0x10
MARCA_SIN_LUZ = 0x20
MARCA_SIN_TEMP = 0x40
MARCA_SIN_HUM = 0x80


def vpd_kpa(temp_c, hum_pct):
    """Déficit de presión de vapor (Tetens), kPa. Vectorizado."""
    temp_c = np.asarray(temp_c, dtype=float)
    hum_pct = np.asarray(hum_pct, dtype=float)
    return 0.6108 * np.exp(17.27 * temp_c / (temp_c + 237.3)) * (1.0 - hum_pct / 100.0)


def _finito(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v)) and math.isfinite(v)


class BufferFeatures:
    """Réplica 1:1 de `BufferFeatures` + `features_empujar` de la placa."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.suelo = [0.0] * VENTANA
        self.luz = [0.0] * VENTANA
        self.cabeza = 0
        self.n = 0
        self.total = 0
        self.temp_ult = math.nan
        self.hum_ult = math.nan
        self.hay_temp_dht = False
        self.hay_hum = False
        self.marcas = 0

    def _atras(self, k: int) -> int:
        return (self.cabeza - 1 - k) % VENTANA

    def empujar(self, suelo, luz, temp_dht, hum, temp_ntc=math.nan):
        """Devuelve `(x, valido, warmup, marcas)`; `x` es una lista de 7 floats.

        `temp_ntc` se acepta para que la firma sea la de `MuestraCruda` en C, pero
        no se usa: el termistor no entra a las features (contrato §4).
        """
        marcas = 0
        if not _finito(suelo):
            if self.n > 0:
                suelo = self.suelo[self._atras(0)]
                marcas |= MARCA_SUELO_REPETIDO
            else:
                marcas |= MARCA_SIN_SUELO
        if not _finito(luz):
            if self.n > 0:
                luz = self.luz[self._atras(0)]
                marcas |= MARCA_LUZ_REPETIDA
            else:
                marcas |= MARCA_SIN_LUZ
        if marcas & (MARCA_SIN_SUELO | MARCA_SIN_LUZ):
            self.marcas = marcas
            return [math.nan] * N_FEATURES, False, True, marcas

        t_ok, h_ok = _finito(temp_dht), _finito(hum)
        if t_ok:
            self.temp_ult, self.hay_temp_dht = float(temp_dht), True
        if h_ok:
            self.hum_ult, self.hay_hum = float(hum), True
        if not (t_ok and h_ok):
            marcas |= MARCA_DHT_ANTERIOR

        temp = self.temp_ult if self.hay_temp_dht else math.nan
        if not self.hay_temp_dht:
            marcas |= MARCA_SIN_TEMP
        hum_v = self.hum_ult if self.hay_hum else math.nan
        if not self.hay_hum:
            marcas |= MARCA_SIN_HUM
        if not self.hay_temp_dht and not self.hay_hum:
            marcas &= ~MARCA_DHT_ANTERIOR

        self.suelo[self.cabeza] = float(suelo)
        self.luz[self.cabeza] = float(luz)
        self.cabeza = (self.cabeza + 1) % VENTANA
        self.n = min(self.n + 1, VENTANA)
        self.total += 1
        self.marcas = marcas

        warmup = self.n <= LAG_DELTA
        delta = 0.0 if warmup else float(suelo) - self.suelo[self._atras(LAG_DELTA)]
        # De la más vieja a la más nueva, como el for de C.
        suma = 0.0
        for k in range(self.n - 1, -1, -1):
            suma += self.luz[self._atras(k)]
        luz_media = suma / self.n

        ok = _finito(temp) and _finito(hum_v)
        vpd = float(vpd_kpa(temp, hum_v)) if ok else math.nan
        x = [float(suelo), delta, temp, hum_v, vpd, float(luz), luz_media]
        return x, ok, warmup, marcas


def asignar_tramos(df: pd.DataFrame, col_ts: str = "ts") -> pd.Series:
    """Id de tramo continuo: cambia con `dispositivo`, `boot_id` o un hueco > 7,5 min."""
    orden = df.sort_values(["dispositivo", col_ts], kind="stable")
    nuevo = ((orden.dispositivo != orden.dispositivo.shift())
             | (orden.boot_id != orden.boot_id.shift())
             | (orden[col_ts].diff() > HUECO_MAX))
    return nuevo.cumsum().reindex(df.index).rename("tramo")


def calcular_features(df: pd.DataFrame, col_ts: str = "ts", col_suelo: str = "suelo_mv",
                      col_luz: str = "luz_mv", col_temp: str = "temp_c",
                      col_hum: str = "hum_aire_pct", col_ntc: str | None = "temp_ntc_c") -> pd.DataFrame:
    """Vector de features por fila, imitando el buffer de la placa tramo por tramo.

    `df` tiene una fila cada 5 min con las lecturas *crudas* de ese tick (NaN
    donde faltan). Devuelve un DataFrame con el mismo índice y las columnas
    `FEATURES` (en ese orden) + `warmup`, `valido`, `marcas`, `tramo`.
    """
    tramo = asignar_tramos(df, col_ts)
    orden = df.assign(_tramo=tramo).sort_values(["_tramo", col_ts], kind="stable")
    s = orden[col_suelo].to_numpy(float)
    lz = orden[col_luz].to_numpy(float)
    t = orden[col_temp].to_numpy(float)
    h = orden[col_hum].to_numpy(float)
    ntc = orden[col_ntc].to_numpy(float) if col_ntc and col_ntc in orden else np.full(len(orden), np.nan)
    tr = orden._tramo.to_numpy()

    X = np.empty((len(orden), N_FEATURES))
    valido = np.zeros(len(orden), bool)
    warm = np.zeros(len(orden), bool)
    marcas = np.zeros(len(orden), np.uint8)
    buf = BufferFeatures()
    previo = None
    for i in range(len(orden)):
        if tr[i] != previo:
            buf.reset()
            previo = tr[i]
        X[i], valido[i], warm[i], marcas[i] = buf.empujar(s[i], lz[i], t[i], h[i], ntc[i])

    out = pd.DataFrame(X, index=orden.index, columns=FEATURES)
    out["warmup"] = warm
    out["valido"] = valido
    out["marcas"] = marcas
    out["tramo"] = tr
    return out.reindex(df.index)
