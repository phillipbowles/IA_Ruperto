"""PlantaIa — código compartido de la Tarea 2 (datos y features).

Lo usan los notebooks y los scripts de `ml/`. Para importarlo desde un
notebook en `notebooks/`:

    import sys; sys.path.insert(0, str(RAIZ / "ml"))
    from plantaia_ml.dataset import serie_maceta01

El contrato de features (orden, nombres, unidades) está en docs/ENTREGA2.md §4
y su gemelo en C en firmware/lib/plantaia_ml/features.{h,cpp}.
"""
from pathlib import Path

# La raíz del repo se busca subiendo desde este archivo, no desde el cwd: así
# funciona igual desde un notebook, desde pytest o desde un script.
RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data"
FIGURAS = RAIZ / "docs" / "entrega2" / "fig"

# Códigos del firmware (CLAUDE.md es la fuente). sin_etiquetar (0) no es clase.
CLASES = ["saludable", "estresada", "marchita"]
CODIGO_CLASE = {"sin_etiquetar": 0, "saludable": 1, "estresada": 2, "marchita": 3}
CLASE_CODIGO = {v: k for k, v in CODIGO_CLASE.items()}

SNAPSHOT_VIGENTE = DATOS / "mediciones_raw_2026-10-21.csv"

__all__ = ["RAIZ", "DATOS", "FIGURAS", "CLASES", "CODIGO_CLASE", "CLASE_CODIGO",
           "SNAPSHOT_VIGENTE"]
