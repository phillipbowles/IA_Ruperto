"""Documentos .md del corpus → chunks del contrato (docs/ENTREGA3.md §4).

Cada documento tiene una cabecera entre `---` con `clave: valor` (título, URL,
fecha de acceso...) y el cuerpo en secciones `## `. Se corta por sección:

- una sección de MIN_PALABRAS a MAX_PALABRAS es un chunk;
- las secciones cortas se juntan con las siguientes del mismo documento
  mientras no pasen de MAX_PALABRAS;
- una sección larga se parte por párrafos (y un párrafo enorme, por palabras).

Un documento entero más corto que MIN_PALABRAS queda como un único chunk:
no se mezcla texto de dos fuentes distintas en un mismo fragmento.

El id es `<fuente>/<documento>#<n>`, con n desde 0 en orden de aparición: es
estable mientras el documento no cambie.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

MIN_PALABRAS = 150
MAX_PALABRAS = 400
FUENTES = ("ciencia", "historial", "proyecto")


@dataclass
class Chunk:
    id: str
    fuente: str
    titulo: str
    url: str | None
    fecha: str | None
    texto: str

    def dict(self) -> dict:
        return asdict(self)


def palabras(texto: str) -> int:
    return len(texto.split())


def leer_cabecera(texto: str) -> tuple[dict, str]:
    """Separa la cabecera `---` (pares `clave: valor` de una línea) del cuerpo."""
    if not texto.startswith("---"):
        return {}, texto
    fin = texto.find("\n---", 3)
    if fin < 0:
        raise ValueError("cabecera sin cerrar")
    meta = {}
    for linea in texto[3:fin].strip().splitlines():
        if not linea.strip() or ":" not in linea:
            continue
        k, v = linea.split(":", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] == '"':
            v = v[1:-1]
        meta[k.strip()] = None if v in ("", "null") else v
    return meta, texto[fin + 4:].lstrip("\n")


def secciones(cuerpo: str) -> list[tuple[str, str]]:
    """[(encabezado, texto)] por cada `## `. Lo anterior al primer `## ` (sin el `# ` título) va con encabezado vacío."""
    out: list[tuple[str, str]] = []
    actual, lineas = "", []
    for linea in cuerpo.splitlines():
        if linea.startswith("## "):
            out.append((actual, "\n".join(lineas).strip()))
            actual, lineas = linea[3:].strip(), []
        elif linea.startswith("# "):
            continue
        else:
            lineas.append(linea)
    out.append((actual, "\n".join(lineas).strip()))
    return [(h, t) for h, t in out if t]


def _partir_largo(texto: str, maximo: int) -> list[str]:
    """Parte por párrafos sin pasar de `maximo` palabras; un párrafo enorme, por palabras."""
    partes, actual = [], []
    for par in re.split(r"\n\s*\n", texto):
        par = par.strip()
        if not par:
            continue
        p = par.split()
        while len(p) > maximo:
            if actual:
                partes.append("\n\n".join(actual))
                actual = []
            partes.append(" ".join(p[:maximo]))
            p = p[maximo:]
            par = " ".join(p)
        if actual and palabras("\n\n".join(actual + [par])) > maximo:
            partes.append("\n\n".join(actual))
            actual = []
        actual.append(par)
    if actual:
        partes.append("\n\n".join(actual))
    return partes


def bloques(secs: list[tuple[str, str]], minimo: int = MIN_PALABRAS,
            maximo: int = MAX_PALABRAS) -> list[str]:
    """Agrupa/parte las secciones en textos de [minimo, maximo] palabras cuando se puede."""
    piezas: list[str] = []
    for enc, txt in secs:
        cuerpo = f"{enc}\n{txt}" if enc else txt
        if palabras(cuerpo) <= maximo:
            piezas.append(cuerpo)
        else:
            trozos = _partir_largo(txt, maximo - palabras(enc) - 3)
            piezas += [f"{enc} ({i + 1}/{len(trozos)})\n{t}" if enc else t
                       for i, t in enumerate(trozos)]
    out: list[str] = []
    for p in piezas:
        if out and palabras(out[-1]) < minimo and palabras(out[-1]) + palabras(p) <= maximo:
            out[-1] = f"{out[-1]}\n\n{p}"
        else:
            out.append(p)
    # Un resto corto al final se pega al anterior si entra.
    if len(out) > 1 and palabras(out[-1]) < minimo and palabras(out[-2]) + palabras(out[-1]) <= maximo:
        out[-2:] = [f"{out[-2]}\n\n{out[-1]}"]
    return out


def chunks_documento(ruta: Path, fuente: str) -> list[Chunk]:
    if fuente not in FUENTES:
        raise ValueError(f"fuente desconocida: {fuente}")
    meta, cuerpo = leer_cabecera(ruta.read_text(encoding="utf-8"))
    titulo = meta.get("titulo") or ruta.stem
    url = meta.get("url")
    fecha = meta.get("fecha")
    return [Chunk(f"{fuente}/{ruta.stem}#{i}", fuente, titulo, url, fecha, t)
            for i, t in enumerate(bloques(secciones(cuerpo)))]


def chunks_corpus(carpeta: Path, fuente: str) -> list[Chunk]:
    """Todos los .md de `carpeta`, en orden alfabético (orden estable)."""
    out: list[Chunk] = []
    for ruta in sorted(carpeta.glob("*.md")):
        out += chunks_documento(ruta, fuente)
    return out
