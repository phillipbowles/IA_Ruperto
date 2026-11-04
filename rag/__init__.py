"""Corpus e índice del RAG de Ruperto (Tarea 3) — contrato en docs/ENTREGA3.md §4.

Se corre desde la raíz del repo:  python -m rag.construir_indice
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CORPUS = RAIZ / "rag" / "corpus"
INDICE = RAIZ / "backend" / "app" / "bot" / "indice"

# El historial reutiliza plantaia_ml (carga del snapshot, unificación de
# maceta-02 y la regla de riego del contrato de features) en vez de reimplementarlo.
if str(RAIZ / "ml") not in sys.path:
    sys.path.insert(0, str(RAIZ / "ml"))
