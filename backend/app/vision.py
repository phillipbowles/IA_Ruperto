"""Visión por computadora clásica (sin IA generativa) para estimar cuánto están
caídas las hojas y las flores de un lirio de paz en una foto.

1. **Segmentación por color.** Hojas: índice ExG = 2G − R − B. De todo lo verde
   se queda con el bloque principal (la planta del frente): así no cuentan los
   reflejos en un espejo ni otras plantas de la mesada.
2. **Base de la planta = borde de la maceta.** Se busca la maceta de terracota
   debajo del centro de la planta y se toma su borde superior: lo que queda por
   debajo de esa línea es follaje que cuelga. Si no hay maceta de ese color a la
   vista, la base es el píxel verde más bajo de la franja central (donde
   convergen los pecíolos).
3. **Ángulo de elevación.** Para cada píxel verde, el ángulo sobre la
   horizontal visto desde la base: ~70° en una hoja erguida, ~30–40° en una que
   se abre hacia los costados, y negativo en una que cuelga sobre el borde de la
   maceta. El puntaje de las hojas sale del ángulo medio.
4. **Espatas.** Manchas blancas de tamaño razonable pegadas a la planta (un
   puntito de luz o un reflejo no cuenta). Pesan 40 %: en el lirio de paz la
   espata caída es la primera señal visible de falta de agua.

Los cortes (CORTES) son heurísticos, ajustados el 22/10 con cuatro fotos reales
de maceta-01 juzgadas a ojo (de «mal pero no en el peor estado» a «toda caída,
flores en el piso») y con plantas sintéticas. Rinden mejor con la planta de
frente, entera en cuadro y con la maceta visible.
"""

from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage as ndi

# Cambia cada vez que cambia el algoritmo o los cortes: la calibración guarda
# con qué versión se evaluó cada foto.
VERSION = "vision-clasica-v2"

LADO_MAX = 512

# Ángulo medio (grados) que da 0 y que da 1, interpolado lineal.
CORTES = {
    "angulo_hojas": (5.0, 70.0),
    "angulo_flores": (20.0, 70.0),
}
MIN_FRACCION_VERDE = 0.015
MIN_FRACCION_MANCHA_FLOR = 0.0005   # por mancha blanca, sobre el total de la imagen
MIN_FRACCION_MACETA = 0.002
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


def _planta_principal(verde: np.ndarray) -> np.ndarray:
    # El cierre une las hojas de una misma planta separadas por pocos píxeles.
    etiquetas, n = ndi.label(ndi.binary_closing(verde, iterations=3))
    areas = ndi.sum(verde, etiquetas, range(1, n + 1))
    return verde & (etiquetas == int(np.argmax(areas)) + 1)


def _borde_maceta(hsv: np.ndarray, ys: np.ndarray, izq: float, der: float) -> tuple[float, float] | None:
    tono = hsv[..., 0].astype(np.float32) * 360 / 255
    sat, val = hsv[..., 1], hsv[..., 2]
    terracota = (tono >= 5) & (tono <= 35) & (sat > 90) & (val > 70) & (val < 235)
    # Debajo del cuarto superior de la planta: más arriba puede haber frutas del
    # mismo color, y con las hojas colgando la maceta queda a media altura.
    zona = np.zeros_like(terracota)
    zona[int(np.percentile(ys, 25)):, int(izq):int(der) + 1] = True
    etiquetas, n = ndi.label(ndi.binary_opening(terracota & zona, iterations=2))
    if not n:
        return None
    areas = ndi.sum(np.ones_like(etiquetas), etiquetas, range(1, n + 1))
    k = int(np.argmax(areas)) + 1
    if areas[k - 1] < MIN_FRACCION_MACETA * terracota.size:
        return None
    py, px = np.nonzero(etiquetas == k)
    return float(np.percentile(py, 3)), float(np.median(px))


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

    planta = _planta_principal(verde)
    ys, xs = np.nonzero(planta)
    # Percentiles y no mín./máx.: unos pocos píxeles sueltos no deben mover nada.
    izq, der = np.percentile(xs, [1, 99])
    maceta = _borde_maceta(hsv, ys, izq, der)
    if maceta:
        base_y, base_x = maceta
    else:
        base_x = float(np.median(xs))
        central = np.abs(xs - base_x) <= FRANJA_CENTRAL * max(der - izq, 1.0)
        base_y = float(np.percentile(ys[central], 98))

    angulo_hojas = float(_angulos(ys, xs, base_y, base_x).mean())
    colgando = float((ys > base_y + 2).mean())
    s_hojas = _escala(angulo_hojas, "angulo_hojas")

    cerca = ndi.binary_dilation(planta, iterations=10)
    blanco = (hsv[..., 1] < 28) & (hsv[..., 2] > 205) & cerca
    etiquetas, n = ndi.label(blanco)
    areas = ndi.sum(blanco, etiquetas, range(1, n + 1))
    grandes = [i + 1 for i, a in enumerate(areas) if a >= MIN_FRACCION_MANCHA_FLOR * blanco.size]
    flor = np.isin(etiquetas, grandes)
    frac_flor = float(flor.mean())

    metricas = {
        "fraccion_verde": round(float(planta.mean()), 4),
        "angulo_hojas": round(angulo_hojas, 1),
        "fraccion_colgando": round(colgando, 3),
        "fraccion_flor": round(frac_flor, 4),
    }

    if grandes:
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

    referencia = "del borde de la maceta" if maceta else "de la base de la planta"
    hojas = (f"Ángulo medio de las hojas: {angulo_hojas:.0f}° sobre la horizontal; "
             f"{colgando:.0%} del follaje cuelga por debajo {referencia}. "
             + _adjetivo(s_hojas, "Hojas erguidas.", "Hojas cediendo hacia los costados.",
                         "Hojas caídas sobre la maceta."))
    return ResultadoVision(
        es_planta=True,
        puntaje=int(round(puntaje)),
        hojas=hojas,
        flores=flores,
        explicacion="Segmentación por color, borde de la maceta y ángulo del follaje (sin IA "
                    "generativa). Los cortes son heurísticos: rinde mejor con la planta de frente "
                    "y la maceta visible.",
        metricas=metricas,
    )
