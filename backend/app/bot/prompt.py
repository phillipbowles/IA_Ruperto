"""Armado del prompt (docs/ENTREGA3.md §5.3).

System = persona + reglas (persona.SYSTEM). Turno de usuario = bloques
ESTADO ACTUAL, ÚLTIMOS 7 DÍAS, FRAGMENTOS (numerados desde 1, con fuente) y
PREGUNTA. Antes del turno van los últimos 6 turnos del chat (memoria corta, en
memoria del proceso: el log persistente es la tabla `conversaciones`).
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from . import persona
from .recuperar import Fragmento

ZONA = ZoneInfo("America/Montevideo")
TURNOS_MEMORIA = 6
MAX_CHARS_FRAGMENTO = 1500


def system() -> str:
    return persona.SYSTEM


def texto_fragmentos(fragmentos: list[Fragmento]) -> str:
    if not fragmentos:
        return "(no se recuperó ningún fragmento)"
    bloques = []
    for n, f in enumerate(fragmentos, 1):
        cab = f"[{n}] fuente: {f.fuente} — {f.titulo}"
        if f.fecha:
            cab += f" — fecha {f.fecha}"
        if f.url:
            cab += f" — {f.url}"
        texto = f.texto if len(f.texto) <= MAX_CHARS_FRAGMENTO else f.texto[:MAX_CHARS_FRAGMENTO] + "…"
        bloques.append(f"{cab}\n{texto}")
    return "\n\n".join(bloques)


def turno_usuario(estado: str, dias: str, fragmentos: list[Fragmento], pregunta: str,
                  simple: str = "") -> str:
    simple = f"EN PALABRAS SIMPLES\n{simple}\n\n" if simple else ""
    return (f"{simple}ESTADO ACTUAL\n{estado}\n\n"
            f"ÚLTIMOS 7 DÍAS\n{dias}\n\n"
            f"FRAGMENTOS\n{texto_fragmentos(fragmentos)}\n\n"
            f"PREGUNTA\n{pregunta}")


# ─── citas (D211) ─────────────────────────────────────────────────────────
# Los [n] sirven para trazar qué fragmento usó cada respuesta (quedan en el log),
# pero en Telegram el usuario no ve los fragmentos: se sacan del texto y las
# fuentes científicas citadas van al pie, con el nombre de la institución.
INSTITUCIONES = {
    "ufifas": "Universidad de Florida (UF/IFAS)",
    "ncstate": "NC State Extension",
    "rhs": "Royal Horticultural Society",
    "aspca": "ASPCA",
    "bmc": "BMC Plant Biology (2024)",
}
_CITA = re.compile(r"\s*\[(\d+(?:\s*,\s*\d+)*)\]")


def _institucion(f: Fragmento) -> str:
    doc = f.id.split("/", 1)[-1].split("#", 1)[0]
    return INSTITUCIONES.get(doc.split("-", 1)[0], f.titulo)


def citas(texto: str, fragmentos: list[Fragmento]) -> tuple[str, set[int]]:
    """Saca los [n] del texto y agrega el pie con las fuentes científicas
    citadas. Devuelve el texto final y los índices (desde 0) citados."""
    citados: set[int] = set()
    for m in _CITA.finditer(texto):
        citados |= {int(n) - 1 for n in m.group(1).split(",")
                    if 0 < int(n) <= len(fragmentos)}
    limpio = _CITA.sub("", texto).strip()
    fuentes = []
    for i in sorted(citados):
        if fragmentos[i].fuente == "ciencia" and (inst := _institucion(fragmentos[i])) not in fuentes:
            fuentes.append(inst)
    if fuentes:
        limpio += "\n\n📚 Fuente: " + ", ".join(fuentes)
    return limpio, citados


# ─── higiene de la respuesta (D217) ───────────────────────────────────────
# En mayúsculas y seguido de dos puntos o raya: así sólo se toca el rótulo
# copiado, no la frase "en palabras simples" dicha con naturalidad.
_ROTULO = re.compile(r"(?:^[ \t]*)?(EN PALABRAS SIMPLES|ESTADO ACTUAL|ÚLTIMOS 7 DÍAS|FRAGMENTOS|PREGUNTA)"
                     r"(?:[ \t]*[:\-—][ \t]*|[ \t]*$)", re.M)


def sin_rotulos(texto: str) -> str:
    """Saca los nombres de los bloques del prompt cuando el modelo los copia
    como rótulo ("EN PALABRAS SIMPLES: tierra húmeda."). El prompt ya lo pide;
    los modelos lite lo hacen igual."""
    limpio = _ROTULO.sub("", texto)
    # Si el rótulo abría la línea, lo que sigue arranca en minúscula.
    limpio = re.sub(r"(^|[.!?]\s+)([a-záéíóúñ])", lambda m: m.group(1) + m.group(2).upper(),
                    limpio, flags=re.M)
    return limpio.strip()


def solo_pasado(fragmentos: list[Fragmento], ahora: datetime) -> list[Fragmento]:
    """El historial indexado aporta sólo días anteriores al de hoy: el día en
    curso lo cuenta el contexto SQL. Así un resumen diario no adelanta lo que
    todavía no pasó (con el reloj inyectado de la evaluación, o si el índice se
    regenera a mitad del día)."""
    hoy = ahora.astimezone(ZONA).date().isoformat()
    return [f for f in fragmentos if not (f.fuente == "historial" and f.fecha and f.fecha >= hoy)]


class Memoria:
    """Últimos `TURNOS_MEMORIA` pares (pregunta, respuesta) por chat, de las
    últimas `VIGENCIA` (D218).

    Se guarda la pregunta pelada, no el turno con los bloques: el estado de
    hace 10 minutos no tiene que competir con el de ahora. Pasada la vigencia
    la charla se da por terminada: "¿y ahora?" de mañana no se refiere a lo de
    hoy. Vive en el proceso; `responder` la reconstruye desde `conversaciones`
    cuando un chat no tiene nada (después de un redeploy).
    """

    VIGENCIA = timedelta(hours=2)

    def __init__(self, turnos: int = TURNOS_MEMORIA, desde_db: bool = False):
        self.turnos = turnos
        self.desde_db = desde_db           # la del proceso sí; las de prueba no
        self._chats: dict[int, deque[tuple[datetime, str, str]]] = defaultdict(
            lambda: deque(maxlen=turnos))

    def agregar(self, chat_id: int, pregunta: str, respuesta: str,
                ts: datetime | None = None) -> None:
        self._chats[chat_id].append((ts or datetime.now(UTC), pregunta, respuesta))

    def _vigentes(self, chat_id: int) -> list[tuple[datetime, str, str]]:
        limite = datetime.now(UTC) - self.VIGENCIA
        return [x for x in self._chats.get(chat_id, ()) if x[0] >= limite]

    def vacia(self, chat_id: int) -> bool:
        return not self._chats.get(chat_id)

    def historial(self, chat_id: int) -> list[dict]:
        out = []
        for _, p, r in self._vigentes(chat_id):
            out += [{"role": "user", "text": p}, {"role": "model", "text": r}]
        return out

    def ultimo_intercambio(self, chat_id: int) -> tuple[str, str] | None:
        v = self._vigentes(chat_id)
        return (v[-1][1], v[-1][2]) if v else None


def contenidos(memoria: Memoria, chat_id: int, turno: str) -> list[dict]:
    return memoria.historial(chat_id) + [{"role": "user", "text": turno}]
