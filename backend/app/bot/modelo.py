"""El modelo de la Tarea 2 visto desde el server (docs/ENTREGA3.md D8).

Dos caminos: la predicción que mandó la placa (tabla `predicciones`, la lee
`contexto.py`) y la **regla vigente recalculada acá** desde
`modelo_placa.json`, que genera `ml/plantaia_ml/exportar_c.py` (no se edita a
mano). La placa todavía puede correr un modelo viejo; recalcular la regla en el
server permite decir qué diría el modelo vigente con la misma muestra.

`h_desde_riego` se calcula sobre la serie de la base con la semántica del
contrato (docs/ENTREGA2.md §4, réplica de `ml/plantaia_ml/features.py`):

- un **tramo** es una corrida del mismo `boot_id` sin huecos de más de 7,5 min;
  al empezar cada tramo la ventana se vacía, pero el último riego se conserva
  (la placa lo guarda en Preferences);
- la sonda faltante o saturada (`suelo_raw` 0 o 4095) repite el último valor
  empujado y no cuenta como lectura real; con la ventana vacía la muestra no
  entra;
- hay riego si la lectura es real, la ventana ya tenía 12 muestras antes y la
  sonda cayó ≥ 250 mV respecto de la última empujada;
- `h_desde_riego = (ts − riego) / 3600` con tope 96 h (también sin riego visto).

Sin pandas ni numpy: corre en la imagen de producción del backend.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

RUTA_MODELO = Path(__file__).with_name("modelo_placa.json")

VENTANA = 13
LAG_DELTA = 12
HUECO_MAX = timedelta(minutes=7.5)
RIEGO_CAIDA_MV = 250.0
RIEGO_TOPE_H = 96.0
SUELO_SATURADO = (0, 4095)


@dataclass(frozen=True)
class Muestra:
    """Lo mínimo de una fila de `mediciones` que hace falta para el riego."""

    ts: datetime                    # con zona (UTC)
    suelo_mv: float | None
    suelo_raw: int | None = None
    luz_mv: float | None = 0.0      # sólo importa si falta con la ventana vacía
    boot_id: int | None = None


@dataclass
class Riegos:
    """Resultado de recorrer la serie: riegos detectados y horas desde el último."""

    detectados: list[datetime] = field(default_factory=list)
    h_desde_riego: float = RIEGO_TOPE_H   # en la última muestra de la serie
    ultimo: datetime | None = None


def _finito(v) -> bool:
    return v is not None and isinstance(v, (int, float)) and math.isfinite(v)


def suelo_valido(m: Muestra) -> float | None:
    """La sonda saturada cuenta como faltante (contrato §4)."""
    if not _finito(m.suelo_mv) or m.suelo_raw in SUELO_SATURADO:
        return None
    return float(m.suelo_mv)


def detectar_riegos(serie: list[Muestra]) -> Riegos:
    """Recorre la serie (se ordena por `ts`) como lo haría la placa."""
    serie = sorted(serie, key=lambda m: m.ts)
    res = Riegos()
    riego_ts: datetime | None = None
    n = 0                    # muestras en la ventana del tramo (tope 13)
    ultimo_suelo = 0.0       # última empujada (puede ser una repetición)
    previa: Muestra | None = None
    for m in serie:
        if previa is None or m.boot_id != previa.boot_id or m.ts - previa.ts > HUECO_MAX:
            n = 0            # tramo nuevo: ventana vacía, riego conservado
        previa = m
        suelo = suelo_valido(m)
        real = suelo is not None
        if not real:
            if n == 0:
                continue     # sin con qué rellenar: no entra al buffer
            suelo = ultimo_suelo
        if not _finito(m.luz_mv) and n == 0:
            continue         # la luz también hace falta para entrar a una ventana vacía
        if real and n >= LAG_DELTA and ultimo_suelo - suelo >= RIEGO_CAIDA_MV:
            riego_ts = m.ts
            res.detectados.append(m.ts)
        ultimo_suelo = suelo
        n = min(n + 1, VENTANA)
    res.ultimo = riego_ts
    if serie:
        res.h_desde_riego = horas_desde(riego_ts, serie[-1].ts)
    return res


def horas_desde(riego: datetime | None, ts: datetime) -> float:
    if riego is None or ts < riego:
        return RIEGO_TOPE_H
    return min(RIEGO_TOPE_H, (ts - riego).total_seconds() / 3600.0)


# ─── la regla vigente ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class Regla:
    version: str
    features: tuple[str, ...]
    nodos: tuple[dict, ...]
    clases: tuple[str, ...] = ("saludable", "estresada", "marchita")


@dataclass(frozen=True)
class Resultado:
    version: str
    clase: str | None                # None = no se puede evaluar
    proba: float | None = None
    rama: tuple[str, ...] = ()       # condiciones recorridas, legibles
    motivo: str | None = None        # por qué no hay clase


@lru_cache(maxsize=1)
def cargar_regla(ruta: Path = RUTA_MODELO) -> Regla:
    datos = json.loads(Path(ruta).read_text())
    if not datos.get("nodos"):
        raise ValueError(f"{ruta}: el modelo exportado no es un árbol (sin nodos)")
    return Regla(version=datos["version"], features=tuple(datos["features"]),
                 nodos=tuple(datos["nodos"]))


def umbrales_suelo(regla: Regla | None = None) -> tuple[float, ...]:
    """Cortes de `suelo_mv` de la regla, de menor a mayor: en palabras, húmeda
    hasta el primero, secándose hasta el segundo, muy seca después."""
    regla = regla or cargar_regla()
    return tuple(sorted(n["umbral"] for n in regla.nodos if n.get("feature") == "suelo_mv"))


def _num(v: float) -> str:
    return f"{v:g}"


def evaluar(x: dict[str, float | None], regla: Regla | None = None) -> Resultado:
    """Recorre el árbol: `x[feature] <= umbral` va por `si`, si no por `no`.

    Con una feature faltante no se predice: la placa tampoco inventa datos.
    """
    regla = regla or cargar_regla()
    faltan = [f for f in regla.features if not _finito(x.get(f))]
    if faltan:
        return Resultado(regla.version, None, motivo=f"faltan datos: {', '.join(faltan)}")
    i, rama = 0, []
    while "clase" not in regla.nodos[i]:
        nodo = regla.nodos[i]
        v = float(x[nodo["feature"]])
        if v <= nodo["umbral"]:
            rama.append(f"{nodo['feature']} = {_num(round(v, 1))} ≤ {_num(nodo['umbral'])}")
            i = nodo["si"]
        else:
            rama.append(f"{nodo['feature']} = {_num(round(v, 1))} > {_num(nodo['umbral'])}")
            i = nodo["no"]
    hoja = regla.nodos[i]
    k = regla.clases.index(hoja["clase"])
    return Resultado(regla.version, hoja["clase"], float(hoja["proba"][k]), tuple(rama))
