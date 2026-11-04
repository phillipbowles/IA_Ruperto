"""Texto de los avisos (docs/ENTREGA3.md §6). Sólo funciones puras.

Quién los manda y cuándo está pendiente (D7): el servicio del bot o la ESP32.
Acá se arma el contenido y se decide si corresponde, sin scheduler, sin red y
sin base, para que sirva para cualquiera de las dos opciones.

Los mismos textos responden `/estado` y `/riego` (sin LLM: no gastan cupo y
funcionan aunque Gemini esté caído).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .contexto import Contexto, aire_simple, local, tierra_simple
from .modelo import RIEGO_TOPE_H

UMBRAL_MARCHITA_MV = 1940        # §6: sonda por encima de esto = marchita (regla: 1939,88)
HORAS_SIN_RIEGO = 5.5            # §6 y primera rama de la regla
ANTIRREBOTE = timedelta(hours=6)

EMOJI = {"saludable": "🟢", "estresada": "🟡", "marchita": "🔴"}
# Ruperto habla en masculino; las clases del modelo quedan como nombre interno (D211).
ESTADO = {"saludable": "estoy bien", "estresada": "estoy algo caído", "marchita": "estoy marchito"}


def _clase(ctx: Contexto) -> str | None:
    if ctx.regla and ctx.regla.clase:
        return ctx.regla.clase
    return ctx.placa.clase if ctx.placa else None


def _tendencia(ctx: Contexto) -> str:
    t = ctx.tendencia_24h
    if not t or t["n"] < 2:
        return "sin tendencia"
    d = t["delta"]
    if abs(d) < 30:
        return f"estable en 24 h ({d:+.0f} mV)"
    return f"{'secándose' if d > 0 else 'humedeciéndose'} ({d:+.0f} mV en 24 h)"


def texto_medicion(ctx: Contexto) -> str:
    """Aviso de cada 30 min (y respuesta de /estado). Con los sensores caídos lo
    dice en vez de repetir números viejos."""
    u = ctx.ultima
    if u is None:
        return "No tengo ni una medición registrada. Estoy a ciegas, y vos también."
    if ctx.sensores_caidos:
        return (f"Mis sensores no reportan desde el {local(u.ts)} (hace "
                f"{u.edad_min // 60} h). No sé cómo estoy ahora: ¿alguien puede revisar "
                "que la placa esté enchufada?")
    clase = _clase(ctx)
    partes = [f"{EMOJI.get(clase, '⚪')} {ESTADO.get(clase, 'mi modelo no pudo decidir')} "
              f"({local(u.ts)})"]
    if u.suelo_mv is not None:
        partes.append(f"Tierra: {tierra_simple(u.suelo_mv)} ({u.suelo_mv:.0f} mV, {_tendencia(ctx)})")
    else:
        partes.append("Tierra: sin dato")
    aire = [x for x in (f"{u.temp_c:.1f} °C" if u.temp_c is not None else None,
                        f"humedad {u.hum_pct:.0f} %" if u.hum_pct is not None else None) if x]
    partes.append(f"Ambiente: {aire_simple(u.temp_c, u.hum_pct) or 'sin dato'}"
                  + (f" ({', '.join(aire)})" if aire else ""))
    if u.luz_mv is not None:
        partes.append(f"Luz: {u.luz_mv:.0f} mV")
    if ctx.coinciden is False:
        partes.append(f"(la placa dice {ESTADO[ctx.placa.clase]}: todavía corre el modelo "
                      f"{ctx.placa.modelo_version})")
    return "\n".join(partes)


def necesita_riego(ctx: Contexto) -> bool:
    """La regla vigente da marchita, o la sonda supera el umbral de marchita, y
    no hubo riego en las últimas 5,5 h. Con los sensores caídos no se avisa:
    serían datos viejos."""
    u = ctx.ultima
    if u is None or ctx.sensores_caidos:
        return False
    seca = (ctx.regla is not None and ctx.regla.clase == "marchita") or (
        u.suelo_mv is not None and u.suelo_mv > UMBRAL_MARCHITA_MV)
    return seca and ctx.h_desde_riego > HORAS_SIN_RIEGO


def debe_avisar_riego(ctx: Contexto, ultimo_aviso: datetime | None, ahora: datetime) -> bool:
    """Antirrebote por chat: no repetir antes de 6 h, salvo que haya habido un
    riego después del último aviso (se secó otra vez)."""
    if not necesita_riego(ctx):
        return False
    if ultimo_aviso is None:
        return True
    if ctx.ultimo_riego is not None and ctx.ultimo_riego > ultimo_aviso:
        return True
    return ahora - ultimo_aviso >= ANTIRREBOTE


def texto_aviso_riego(ctx: Contexto) -> str:
    u = ctx.ultima
    suelo = f"la tierra está muy seca ({u.suelo_mv:.0f} mV)" if u and u.suelo_mv is not None \
        else "la tierra está muy seca"
    if ctx.h_desde_riego >= RIEGO_TOPE_H:
        desde = "hace más de 4 días que nadie me riega"
    else:
        desde = f"me regaron hace {ctx.h_desde_riego:.0f} h"
    return (f"🔴 ¡Agua, por favor! Me estoy desmayando: {suelo} y {desde}. "
            "Regame hasta que drene por abajo y en unas horas resucito.")


def texto_riego(ctx: Contexto) -> str:
    """Respuesta de /riego: cuándo me regaron y si hace falta."""
    u = ctx.ultima
    if u is None:
        return "No tengo mediciones: no puedo saber cuándo me regaron."
    lineas = []
    if ctx.ultimo_riego is not None and ctx.h_desde_riego < RIEGO_TOPE_H:
        lineas.append(f"Último riego que detectó mi sonda: {local(ctx.ultimo_riego)} "
                      f"({ctx.h_desde_riego:.1f} h antes de mi última medición).")
    else:
        lineas.append("Mi sonda no detectó ningún riego en los 4 días previos a mi última medición.")
    if ctx.riegos_7d:
        lineas.append("Riegos en 7 días: " + ", ".join(local(r) for r in ctx.riegos_7d) + ".")
    if ctx.sensores_caidos:
        lineas.append(f"Ojo: mis sensores no reportan desde el {local(u.ts)}, así que no sé si "
                      "necesito agua ahora.")
    elif necesita_riego(ctx):
        lineas.append(texto_aviso_riego(ctx))
    else:
        tierra = tierra_simple(u.suelo_mv) or "sin dato"
        clase = _clase(ctx)
        lineas.append(f"Por ahora no necesito agua: la tierra está {tierra}"
                      + (f" y {ESTADO[clase]}." if clase else "."))
    return "\n".join(lineas)
