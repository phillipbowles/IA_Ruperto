# notebooks

| Notebook | Qué hace |
|---|---|
| [`01_eda.ipynb`](01_eda.ipynb) | Análisis exploratorio del dataset — el entregable de la Tarea 1 |
| [`02_analisis_ampliado.ipynb`](02_analisis_ampliado.ipynb) | Práctica posterior a la devolución: tanda real de octubre, datos simulados rotulados como tales, ruido de etiquetas, confusión día/noche y validación por episodio |

El notebook está **commiteado con las salidas ejecutadas**, así que se puede leer
entero sin correr nada.

## Correrlo

Desde la raíz del repo:

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install "pandas>=2.2,<3" numpy matplotlib seaborn scipy jupyter
jupyter lab notebooks/01_eda.ipynb
```

O, si ya está el entorno del backend:

```bash
pip install -e "backend/[ml]"
```

El notebook resuelve solo la raíz del repo, así que corre igual abriéndolo desde
`notebooks/` o desde la raíz.

Para traer datos nuevos de Railway antes de correrlo:

```bash
curl -o data/mediciones_raw_$(date +%F).csv https://backend-production-a379.up.railway.app/api/v1/mediciones.csv
```

Eso escribe un snapshot nuevo en `data/`; hay que apuntar la constante `CRUDO`
del notebook al archivo nuevo. El snapshot viejo no se toca — ver
[data/README.md](../data/README.md).

## Qué escribe

| Salida | Dónde |
|---|---|
| Dataset analizado | `data/dataset.csv` |
| 4 figuras en PNG | Se guardan en `outputs/` al ejecutar (no se versionan; ya están embebidas en el notebook) |

## Cómo está organizado

El notebook sigue el orden de la Tarea 1 y conserva sólo los análisis necesarios:

| § | Contenido |
|---|---|
| 1 | Carga, muestra del CSV y control de calidad |
| 2 | Media, mediana y desvío estándar |
| 3 | Histogramas, boxplots y asociación con la condición |
| 4 | Heatmap de correlación entre sensores |
| 5 | Series temporales y confusión entre etiqueta y tiempo |
| 6 | Conclusiones y mejoras para la próxima recolección |

El hallazgo principal se conserva: las diferencias entre etiquetas son grandes,
pero cada clase se registró en un bloque temporal distinto. Por eso el notebook
las presenta como asociaciones y no como evidencia causal.
