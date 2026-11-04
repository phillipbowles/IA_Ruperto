"""Armado del prompt (docs/ENTREGA3.md §5.3).

System = persona + reglas (persona.SYSTEM). Turno de usuario = bloques
ESTADO ACTUAL, ÚLTIMOS 7 DÍAS, FRAGMENTOS (numerados desde 1, con fuente) y
PREGUNTA. Antes del turno van los últimos 6 turnos del chat (memoria corta, en
memoria del proceso: el log persistente es la tabla `conversaciones`).
"""
from __future__ import annotations

import re
from collections import defaultdict, deque

from . import persona
from .recuperar import Fragmento

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


class Memoria:
    """Últimos `TURNOS_MEMORIA` pares (pregunta, respuesta) por chat.

    Se guarda la pregunta pelada, no el turno con los bloques: el estado de
    hace 10 minutos no tiene que competir con el de ahora.
    """

    def __init__(self, turnos: int = TURNOS_MEMORIA):
        self._chats: dict[int, deque[tuple[str, str]]] = defaultdict(lambda: deque(maxlen=turnos))

    def agregar(self, chat_id: int, pregunta: str, respuesta: str) -> None:
        self._chats[chat_id].append((pregunta, respuesta))

    def historial(self, chat_id: int) -> list[dict]:
        out = []
        for p, r in self._chats.get(chat_id, ()):
            out += [{"role": "user", "text": p}, {"role": "model", "text": r}]
        return out


def contenidos(memoria: Memoria, chat_id: int, turno: str) -> list[dict]:
    return memoria.historial(chat_id) + [{"role": "user", "text": turno}]
