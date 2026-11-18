# PlantaIa — Entrega de la Tarea 2

**Curso de Inteligencia Artificial · Universidad de Montevideo**
Manuel Pérez, Guillermo Storace y Phillip Bowles · Octubre de 2026

Clasificador del estado de un lirio de paz (`saludable` / `estresada` / `marchita`)
que corre en una ESP32 y prende un semáforo de LEDs. Modelo de la placa:
`regla-p3-f07-79b556` (dos umbrales sobre la sonda de suelo + horas desde el
último riego).

## Qué hay en esta carpeta

| Entregable (consigna) | Dónde |
|---|---|
| **Informe en PDF** (carátula + 3 páginas) | `informe/informe.pdf` (fuente: `informe/informe.tex`; figuras en `informe/prism-uploads/`) |
| **Notebook Jupyter** con el procesamiento, los modelos, el análisis y las visualizaciones | `notebook/03_modelos.ipynb` (ejecutado) y `notebook/03_modelos.html` (para leerlo sin Jupyter) |
| **Código fuente de la ESP32** con la inferencia en tiempo real | `firmware/` (PlatformIO) |

Material de soporte, para que el notebook se pueda volver a ejecutar:

- `ml/plantaia_ml/`: el código compartido (features, modelos, exportador a C).
- `data/mediciones_raw_2026-10-23.csv` y `data/episodios.csv`: el dataset de la Tarea 1 y sus etiquetas.

## Firmware (`firmware/`)

- `src/main.cpp`: ciclo de 5 min (leer sensores, buffer, features, predecir, LED, LCD, POST).
- `lib/plantaia_ml/`: la inferencia en C++ sin Arduino.h.
  - `features.{h,cpp}`: las 8 features y la detección de riego.
  - `inferencia.{h,cpp}`: el paso de inferencia y el log `[INF]`.
  - `modelo_plantaia.h`: el modelo, generado por `ml/plantaia_ml/exportar_c.py`.
  - `README.md`: la lógica documentada.
- `test/`: tests de host (`pio test -e native`): paridad Python↔C de features y modelo, y replay de un tramo real.
- `include/secrets.example.h`: plantilla. Para compilar, copiarla como `secrets.h` con el WiFi y el token.

```bash
cd firmware
pio test -e native     # 23 tests en el host
pio run -t upload      # compilar y subir a la placa
```

LEDs: verde GPIO 27 = saludable, amarillo GPIO 26 = estresada, rojo GPIO 25 = marchita.

## Notebook

```bash
cd notebook
jupyter nbconvert --to notebook --execute --inplace 03_modelos.ipynb
```

Requiere Python con pandas, scikit-learn, matplotlib y seaborn (`ml/requirements.txt`).

## Informe

```bash
cd informe
tectonic informe.tex   # o pdflatex; el logo de la UM va en prism-uploads/image.png
```
