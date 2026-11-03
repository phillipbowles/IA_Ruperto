"""Estado en vivo de Ruperto por SQL (docs/ENTREGA3.md §5.1, D3).

Los números de "ahora" salen siempre de la base, nunca del índice. Las
ventanas (24 h, 7 días) se cuentan **hasta la última muestra**, no hasta el
reloj: si la placa está caída, el contexto lo dice (`sensores_caidos`, edad) y
describe los últimos días con datos en vez de devolver vacío.

La hora de cada muestra es la de la placa (`ts_dispositivo`, NTP) y, si falta,
la de recepción. Todo en UTC; se muestra en hora de Montevideo.
"""
from __future__ import annotations

import math
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Medicion
from . import modelo

ZONA = ZoneInfo("America/Montevideo")
DISPOSITIVO_DEFAULT = "maceta-01"
MIN_SENSORES_CAIDOS = 60
DIAS = 7
# h_desde_riego tiene tope de 96 h; la serie arranca 1 h antes para salir del warm-up.
HORAS_SERIE_RIEGO = modelo.RIEGO_TOPE_H + 1


def dispositivo() -> str:
    return os.getenv("BOT_DISPOSITIVO") or DISPOSITIVO_DEFAULT


def _utc(ts: datetime | None) -> datetime | None:
    if ts is None:
        return None
    return ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts.astimezone(UTC)


def local(ts: datetime) -> str:
    return ts.astimezone(ZONA).strftime("%d/%m %H:%M")


def vpd_kpa(t: float | None, hr: float | None) -> float | None:
    if t is None or hr is None:
        return None
    return 0.6108 * math.exp(17.27 * t / (t + 237.3)) * (1 - hr / 100)


@dataclass
class Ultima:
    ts: datetime
    edad_min: int
    suelo_mv: float | None          # None si falta o está saturada
    temp_c: float | None
    hum_pct: float | None
    vpd_kpa: float | None
    luz_mv: float | None
    firmware: str | None
    suelo_nota: str | None = None   # por qué no hay sonda válida, si no la hay


@dataclass
class PrediccionPlaca:
    clase: str
    proba: float | None
    modelo_version: str


@dataclass
class Dia:
    fecha: str                      # YYYY-MM-DD en hora de Montevideo
    n: int
    suelo_media: float | None
    suelo_min: float | None
    suelo_max: float | None
    temp_media: float | None
    hum_media: float | None
    luz_max: float | None


@dataclass
class Contexto:
    dispositivo: str
    ahora: datetime
    ultima: Ultima | None = None
    sensores_caidos: bool = True
    placa: PrediccionPlaca | None = None
    regla: modelo.Resultado | None = None
    h_desde_riego: float = modelo.RIEGO_TOPE_H
    ultimo_riego: datetime | None = None
    riegos_7d: list[datetime] = field(default_factory=list)
    tendencia_24h: dict | None = None     # min, max, delta, n
    dias: list[Dia] = field(default_factory=list)

    @property
    def coinciden(self) -> bool | None:
        """¿La placa y la regla vigente dicen lo mismo? None si falta alguna."""
        if not self.placa or not self.regla or self.regla.clase is None:
            return None
        return self.placa.clase == self.regla.clase


def _media(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def armar_contexto(db: Session, ahora: datetime | None = None,
                   disp: str | None = None) -> Contexto:
    ahora = _utc(ahora) or datetime.now(UTC)
    disp = disp or dispositivo()
    ctx = Contexto(dispositivo=disp, ahora=ahora)
    ts_col = func.coalesce(Medicion.ts_dispositivo, Medicion.ts_servidor)

    ultima = (db.query(Medicion).filter(Medicion.dispositivo == disp)
              .order_by(ts_col.desc(), Medicion.id.desc()).first())
    if ultima is None:
        return ctx
    ts_ult = _utc(ultima.ts_dispositivo or ultima.ts_servidor)
    desde = ts_ult - timedelta(hours=max(HORAS_SERIE_RIEGO, DIAS * 24))
    filas = (db.query(Medicion).filter(Medicion.dispositivo == disp, ts_col >= desde,
                                       ts_col <= ts_ult)
             .order_by(ts_col, Medicion.id).all())

    serie = [modelo.Muestra(ts=_utc(f.ts_dispositivo or f.ts_servidor), suelo_mv=f.suelo_mv,
                            suelo_raw=f.suelo_raw, luz_mv=f.luz_mv, boot_id=f.boot_id)
             for f in filas]
    suelo_ult = modelo.suelo_valido(serie[-1])
    edad = max(0, int((ahora - ts_ult).total_seconds() // 60))
    nota = None
    if suelo_ult is None:
        nota = (f"saturada (suelo_raw {ultima.suelo_raw}): la sonda probablemente está fuera de "
                "la tierra o desconectada" if ultima.suelo_raw in modelo.SUELO_SATURADO
                else "la placa no mandó lectura")
    ctx.ultima = Ultima(ts=ts_ult, edad_min=edad, suelo_mv=suelo_ult, suelo_nota=nota,
                        temp_c=ultima.temperatura_c, hum_pct=ultima.humedad_ambiente_pct,
                        vpd_kpa=vpd_kpa(ultima.temperatura_c, ultima.humedad_ambiente_pct),
                        luz_mv=ultima.luz_mv, firmware=ultima.firmware_version)
    ctx.sensores_caidos = edad > MIN_SENSORES_CAIDOS

    p = ultima.predicciones[-1] if ultima.predicciones else None
    if p is not None:
        ctx.placa = PrediccionPlaca(p.clase, p.proba, p.modelo_version)

    riegos = modelo.detectar_riegos(serie)
    ctx.h_desde_riego, ctx.ultimo_riego = riegos.h_desde_riego, riegos.ultimo
    ctx.riegos_7d = [r for r in riegos.detectados if r >= ts_ult - timedelta(days=DIAS)]
    ctx.regla = modelo.evaluar({"suelo_mv": suelo_ult, "h_desde_riego": riegos.h_desde_riego})

    validas = [(m.ts, s) for m in serie if (s := modelo.suelo_valido(m)) is not None]
    ult24 = [s for ts, s in validas if ts >= ts_ult - timedelta(hours=24)]
    if ult24:
        ctx.tendencia_24h = {"min": min(ult24), "max": max(ult24),
                             "delta": ult24[-1] - ult24[0], "n": len(ult24)}

    por_dia: dict[str, list[tuple[Medicion, modelo.Muestra]]] = defaultdict(list)
    for f, m in zip(filas, serie):
        if m.ts >= ts_ult - timedelta(days=DIAS):
            por_dia[m.ts.astimezone(ZONA).date().isoformat()].append((f, m))
    for fecha in sorted(por_dia):
        fs = por_dia[fecha]
        suelos = [s for _, m in fs if (s := modelo.suelo_valido(m)) is not None]
        temps = [f.temperatura_c for f, _ in fs if f.temperatura_c is not None]
        hums = [f.humedad_ambiente_pct for f, _ in fs if f.humedad_ambiente_pct is not None]
        luces = [f.luz_mv for f, _ in fs if f.luz_mv is not None]
        ctx.dias.append(Dia(fecha=fecha, n=len(fs), suelo_media=_media(suelos),
                            suelo_min=min(suelos, default=None), suelo_max=max(suelos, default=None),
                            temp_media=_media(temps), hum_media=_media(hums),
                            luz_max=max(luces, default=None)))
    return ctx


# ─── texto para el prompt ─────────────────────────────────────────────────
def _f(v: float | None, fmt: str = ".0f", unidad: str = "") -> str:
    return "sin dato" if v is None else f"{v:{fmt}}{unidad}"


def _edad(minutos: int) -> str:
    if minutos < 60:
        return f"{minutos} min"
    h = minutos // 60
    if h < 48:
        return f"{h} h {minutos % 60} min"
    return f"{h // 24} días {h % 24} h"


def texto_estado(ctx: Contexto) -> str:
    """Bloque ESTADO ACTUAL del prompt. Todo número que Ruperto diga sale de acá."""
    u = ctx.ultima
    if u is None:
        return (f"No hay ninguna medición registrada del dispositivo {ctx.dispositivo}. "
                "No sé cómo estoy.")
    lineas = [f"Ahora son las {local(ctx.ahora)} (hora de Montevideo)."]
    lineas.append(f"Última medición: {local(u.ts)}, hace {_edad(u.edad_min)}"
                  f" (firmware {u.firmware or 'desconocido'}).")
    if ctx.sensores_caidos:
        lineas.append(f"SENSORES CAÍDOS: no llegan datos desde {local(u.ts)}. Los valores que siguen "
                      "son de esa última medición, NO de ahora.")
    if u.suelo_mv is not None:
        lineas.append(f"Sonda de suelo: {u.suelo_mv:.0f} mV (más mV = más seca; resistiva).")
    else:
        lineas.append(f"Sonda de suelo: sin dato válido en la última medición ({u.suelo_nota}).")
    lineas.append(f"Aire: {_f(u.temp_c, '.1f', ' °C')}, HR {_f(u.hum_pct, '.0f', ' %')}, "
                  f"VPD {_f(u.vpd_kpa, '.2f', ' kPa')}. Luz (LDR): {_f(u.luz_mv, unidad=' mV')}.")
    if ctx.ultimo_riego is not None and ctx.h_desde_riego < modelo.RIEGO_TOPE_H:
        lineas.append(f"Último riego detectado por la sonda: {local(ctx.ultimo_riego)}, "
                      f"{ctx.h_desde_riego:.1f} h antes de la última medición.")
    else:
        lineas.append(f"No se detectó ningún riego en las {modelo.RIEGO_TOPE_H:.0f} h previas a la "
                      "última medición (h_desde_riego en el tope).")
    if ctx.placa:
        proba = f", confianza {ctx.placa.proba:.2f}" if ctx.placa.proba is not None else ""
        lineas.append(f"Predicción de la placa: {ctx.placa.clase}{proba} "
                      f"(modelo {ctx.placa.modelo_version}).")
    else:
        lineas.append("Predicción de la placa: no mandó ninguna con la última medición.")
    r = ctx.regla
    if r and r.clase:
        lineas.append(f"Regla vigente {r.version} recalculada en el server: {r.clase} "
                      f"(proba {r.proba:.2f}); rama: {' → '.join(r.rama)}.")
    elif r:
        lineas.append(f"Regla vigente {r.version}: no se puede evaluar ({r.motivo}).")
    if ctx.coinciden is False:
        viejo = (ctx.placa.modelo_version != r.version)
        lineas.append("La placa y la regla vigente NO coinciden"
                      + (" (la placa todavía corre un modelo viejo)." if viejo else "."))
    return "\n".join(f"- {l}" for l in lineas)


def texto_dias(ctx: Contexto) -> str:
    """Bloque ÚLTIMOS 7 DÍAS (hasta la última muestra)."""
    if ctx.ultima is None:
        return "- Sin datos."
    lineas = []
    t = ctx.tendencia_24h
    if t:
        lineas.append(f"Sonda en las 24 h previas a la última medición: mín {t['min']:.0f} mV, "
                      f"máx {t['max']:.0f} mV, cambio {t['delta']:+.0f} mV ({t['n']} lecturas).")
    if ctx.riegos_7d:
        lineas.append("Riegos detectados en 7 días: " + ", ".join(local(r) for r in ctx.riegos_7d) + ".")
    else:
        lineas.append("Riegos detectados en 7 días: ninguno.")
    for d in ctx.dias:
        lineas.append(f"{d.fecha}: sonda media {_f(d.suelo_media, unidad=' mV')} "
                      f"(mín {_f(d.suelo_min)}, máx {_f(d.suelo_max)}), "
                      f"T media {_f(d.temp_media, '.1f', ' °C')}, HR media {_f(d.hum_media, '.0f', ' %')}, "
                      f"luz máx {_f(d.luz_max, unidad=' mV')}, {d.n} muestras.")
    return "\n".join(f"- {l}" for l in lineas)
