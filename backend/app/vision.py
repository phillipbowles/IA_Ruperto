"""Visión por computadora clásica (sin IA generativa) para estimar cuánto están
caídas las hojas y las flores de un lirio de paz en una foto.

1. **Segmentación por color.** Hojas: índice ExG = 2G − R − B. Espatas: blanco
   (poca saturación, mucho brillo) cerca del follaje, para no confundirlas con
   una pared clara.
2. **Base de la planta.** Los pecíolos convergen en el centro de la maceta: se
   toma el píxel verde más bajo de la franja central (alrededor de la mediana
   horizontal del follaje).
3. **Ángulo de elevación.** Para cada píxel verde, el ángulo sobre la
   horizontal visto desde la base: ~70–90° en una hoja erguida, ~20–30° en una
   que se abre hacia los costados, y negativo en una que cuelga por debajo del
   borde de la maceta. El puntaje de las hojas sale del ángulo medio; el de las
   flores, del ángulo de las espatas, y pesa 40 %: en el lirio de paz la espata
   caída es la primera señal visible de falta de agua.

Los cortes (CORTES) son heurísticos. El único ajuste con una foto real fue uno
(22/10): un lirio con las hojas a ~48° y las espatas caídas, que a ojo está mal
pero no en el peor estado, tiene que caer en la franja roja clara (~30). Sirven
para comparar fotos tomadas desde el mismo ángulo, de frente y con la planta
entera en cuadro.
"""

from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter, ImageOps

LADO_MAX = 512

# Ángulo medio (grados) que da 0 y que da 1, interpolado lineal.
CORTES = {
    "angulo_hojas": (20.0, 75.0),
    "angulo_flores": (20.0, 70.0),
}
MIN_FRACCION_VERDE = 0.015
MIN_FRACCION_FLOR = 0.001
PESO_FLORES = 0.4
FRANJA_CENTRAL = 0.06     # ± fracción del ancho del follaje alrededor de la mediana


@dataclass
class ResultadoVision:
    es_planta: bool
    puntaje: int | None
    hojas: str
    flores: str
    explicacion: str
    metricas: dict[str, float]


def _escala(valor: float, metrica: str) -> float:
    cero, uno = CORTES[metrica]
    return float(np.clip((valor - cero) / (uno - cero), 0.0, 1.0))


def _angulos(ys: np.ndarray, xs: np.ndarray, base_y: float, base_x: float) -> np.ndarray:
    return np.degrees(np.arctan2(base_y - ys, np.abs(xs - base_x) + 1.0))


def _adjetivo(s: float, alto: str, medio: str, bajo: str) -> str:
    return alto if s >= 0.66 else medio if s >= 0.33 else bajo


def analizar(datos: bytes) -> ResultadoVision:
    img = ImageOps.exif_transpose(Image.open(BytesIO(datos))).convert("RGB")
    img.thumbnail((LADO_MAX, LADO_MAX))
    rgb = np.asarray(img, dtype=np.int16)
    hsv = np.asarray(img.convert("HSV"), dtype=np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    verde = ((2 * g - r - b) > 25) & (g > 45)
    frac_verde = float(verde.mean())
    if frac_verde < MIN_FRACCION_VERDE:
        return ResultadoVision(
            es_planta=False, puntaje=None, hojas="", flores="",
            explicacion=f"Sólo {frac_verde:.1%} de la imagen es verde: no se encontró follaje.",
            metricas={"fraccion_verde": round(frac_verde, 4)},
        )

    ys, xs = np.nonzero(verde)
    # Percentiles y no mín./máx.: unos pocos píxeles verdes sueltos del fondo
    # no deben mover la base.
    izq, der = np.percentile(xs, [1, 99])
    base_x = float(np.median(xs))
    central = np.abs(xs - base_x) <= FRANJA_CENTRAL * max(der - izq, 1.0)
    base_y = float(np.percentile(ys[central], 98))

    ang_hojas = _angulos(ys, xs, base_y, base_x)
    angulo_hojas = float(ang_hojas.mean())
    colgando = float((ys > base_y + 2).mean())
    s_hojas = _escala(angulo_hojas, "angulo_hojas")

    # Espatas: blanco a menos de ~10 px del follaje y por encima del fondo de
    # la maceta.
    cerca = np.asarray(Image.fromarray(verde.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(21))) > 0
    flor = (hsv[..., 1] < 22) & (hsv[..., 2] > 215) & cerca
    frac_flor = float(flor.mean())

    metricas = {
        "fraccion_verde": round(frac_verde, 4),
        "angulo_hojas": round(angulo_hojas, 1),
        "fraccion_colgando": round(colgando, 3),
        "fraccion_flor": round(frac_flor, 4),
    }

    if frac_flor >= MIN_FRACCION_FLOR:
        fy, fx = np.nonzero(flor)
        angulo_flores = float(_angulos(fy, fx, base_y, base_x).mean())
        s_flor = _escala(angulo_flores, "angulo_flores")
        metricas["angulo_flores"] = round(angulo_flores, 1)
        puntaje = 100 * ((1 - PESO_FLORES) * s_hojas + PESO_FLORES * s_flor)
        flores = (f"Las espatas están a {angulo_flores:.0f}° sobre la horizontal desde la base: "
                  + _adjetivo(s_flor, "erguidas.", "inclinadas.", "caídas."))
    else:
        puntaje = 100 * s_hojas
        flores = "No se detectaron espatas blancas: el puntaje sale sólo de las hojas."

    hojas = (f"Ángulo medio de las hojas: {angulo_hojas:.0f}° sobre la horizontal; "
             f"{colgando:.0%} del follaje cuelga por debajo de la base. "
             + _adjetivo(s_hojas, "Hojas erguidas.", "Hojas cediendo hacia los costados.",
                         "Hojas caídas sobre la maceta."))
    return ResultadoVision(
        es_planta=True,
        puntaje=int(round(puntaje)),
        hojas=hojas,
        flores=flores,
        explicacion="Segmentación por color y ángulo del follaje desde la base (sin IA "
                    "generativa). Los cortes son heurísticos: compará fotos tomadas desde el "
                    "mismo ángulo.",
        metricas=metricas,
    )
