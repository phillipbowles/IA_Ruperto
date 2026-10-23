"""Arma informe.html e informe.pdf a partir de informe.md (carátula + cuerpo).

    /opt/anaconda3/bin/python docs/entrega2/informe_final/armar_pdf.py

- La carátula sale del bloque `carátula:` del principio del .md.
- Cada marca `> **[figura.png]** — FIGURA n · <ancho> … > *Caption:* …` se
  reemplaza por la imagen de ./figuras/ con su epígrafe. El ancho sale del texto
  de la marca ("ancho completo", "0,8 del ancho", "0,49 del ancho").
- El PDF lo imprime Chrome headless (A4). Al final cuenta las páginas: la consigna
  pide como máximo 3 sin contar la carátula.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import markdown

AQUI = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4; margin: 15mm 16mm 14mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 9.3pt; line-height: 1.32;
       color: #1d1d1f; margin: 0; }
h2 { font-size: 11pt; margin: 9px 0 3px; color: #1f3d6b; }
p { margin: 0 0 5px; text-align: justify; hyphens: auto; }
table { border-collapse: collapse; width: 100%; font-size: 8.2pt; margin: 3px 0 4px; }
th, td { border-bottom: 1px solid #d8dbe0; padding: 1.6px 5px; text-align: left; }
th { background: #eef2f7; font-weight: 600; }
td:nth-child(n+2), th:nth-child(n+2) { text-align: center; }
pre { background: #f5f6f8; border: 1px solid #e1e4e8; border-radius: 4px; padding: 4px 7px; margin: 3px 0 5px;
      font-size: 7.3pt; line-height: 1.28; white-space: pre-wrap; word-break: break-all; }
code { font-family: Menlo, Consolas, monospace; font-size: 0.92em; }
figure { margin: 4px auto 6px; text-align: center; break-inside: avoid; }
figure img { display: block; margin: 0 auto; }
figcaption { font-size: 7.8pt; color: #444; margin-top: 2px; text-align: justify; }
.cuadro { font-size: 8pt; color: #444; margin: 5px 0 1px; }
.caratula { height: 262mm; display: flex; flex-direction: column; justify-content: center; text-align: center;
            break-after: page; }
.caratula .u { font-size: 13pt; color: #1f3d6b; letter-spacing: .02em; }
.caratula .c { font-size: 12pt; margin-top: 30mm; }
.caratula .t { font-size: 22pt; font-weight: 600; margin: 14mm 10mm 6mm; color: #1f3d6b; }
.caratula .p { font-size: 13pt; }
.caratula .i { font-size: 11.5pt; margin-top: 30mm; }
.caratula .f { font-size: 10.5pt; margin-top: 8mm; color: #555; }
.pendiente { background: #fff4d6; border: 1px dashed #c98500; padding: 4px 6px; font-size: 8.5pt; }
"""


def ancho_de(marca: str) -> str:
    if "ancho completo" in marca:
        return "100%"
    m = re.search(r"(\d+,\d+) del ancho", marca)
    return f"{float(m.group(1).replace(',', '.')) * 100:.0f}%" if m else "100%"


def armar(md_texto: str) -> str:
    md_texto = re.sub(r"<!--.*?-->", "", md_texto, flags=re.S)
    m = re.search(r"^---\s*\ncarátula:\n(.*?)\n---\s*$", md_texto, flags=re.S | re.M)
    datos = dict(re.findall(r'^\s+(\w+):\s*"?(.*?)"?\s*$', m.group(1), flags=re.M))
    md_texto = md_texto[:m.start()] + md_texto[m.end():]

    # Figuras: blockquote de dos líneas (marca + caption) → <figure>.
    def figura(mm):
        archivo, marca, caption = mm.group(1), mm.group(2), mm.group(3)
        n = re.search(r"FIGURA (\d+)", marca)
        rotulo = f"<b>Figura {n.group(1)}.</b> " if n else ""
        texto = markdown.markdown(caption).replace("<p>", "").replace("</p>", "")
        return (f'\n<figure><img src="figuras/{archivo}" style="width:{ancho_de(marca)}">'
                f"<figcaption>{rotulo}{texto}</figcaption></figure>\n")
    md_texto = re.sub(r"^> \*\*\[([^\]]+)\]\*\*(.*)\n> \*Caption:\*\s*(.*)$", figura, md_texto, flags=re.M)
    md_texto = re.sub(r"^\*\*Cuadro (\d+):\*\*(.*)$", r'<p class="cuadro"><b>Cuadro \1:</b>\2</p>', md_texto, flags=re.M)
    md_texto = re.sub(r"^\[(LOG DE LA PLACA[^\]]*)\]$", r'<p class="pendiente">\1</p>', md_texto, flags=re.M)

    cuerpo = markdown.markdown(md_texto, extensions=["tables", "fenced_code"])
    caratula = f"""<section class="caratula">
  <div class="u">{datos['universidad']}</div>
  <div class="c">Curso de {datos['curso']} · {datos['tarea']}</div>
  <div class="p" style="margin-top:6mm">{datos['proyecto']}</div>
  <div class="t">{datos['título']}</div>
  <div class="i">{datos['integrantes']}</div>
  <div class="f">{datos['fecha']}</div>
</section>"""
    return (f"<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\"><title>PlantaIa — Tarea 2</title>"
            f"<style>{CSS}</style></head><body>{caratula}<main>{cuerpo}</main></body></html>")


def paginas(pdf: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))


def main():
    html = AQUI / "informe.html"
    pdf = AQUI / "informe.pdf"
    html.write_text(armar((AQUI / "informe.md").read_text(encoding="utf-8")), encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={AQUI / '.chrome'}", f"--print-to-pdf={pdf}", html.as_uri()],
                   check=True, capture_output=True)
    n = paginas(pdf)
    print(f"{pdf.relative_to(AQUI.parents[2])}: {n} páginas (carátula + {n - 1})")
    if n - 1 > 3:
        print("¡MÁS DE 3 PÁGINAS SIN LA CARÁTULA!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
