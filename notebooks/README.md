# notebooks

| Notebook | Qué hace |
|---|---|
| [`01_eda.ipynb`](01_eda.ipynb) | Análisis exploratorio del dataset — el entregable de la Tarea 1 |
| [`02_analisis_ampliado.ipynb`](02_analisis_ampliado.ipynb) | Análisis posterior a la devolución: tanda real de octubre, cadencia, confusión día/noche y validación por episodio |
| [`03_modelos.ipynb`](03_modelos.ipynb) | Tarea 2: comparación de clasificadores por episodio, costo en la ESP32 y elección del modelo que se exporta a la placa |

Los notebooks están **commiteados con las salidas ejecutadas**, así que se
pueden leer enteros sin correr nada.

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

## `03_modelos.ipynb` — Tarea 2

Sigue el plan de [docs/ENTREGA2.md](../docs/ENTREGA2.md) §5. No calcula nada
por su cuenta que tenga que coincidir con la placa: importa el paquete
`ml/plantaia_ml` (`dataset.serie_maceta01()` para la tabla a 5 min con las 7
features del contrato §4, `modelos.py` para los candidatos, la partición y el
costo). Los resultados y el modelo elegido están en el propio notebook y en
`docs/entrega2/RESULTADOS.md`; este README no los repite.

- **Datos**: la serie de `maceta-01` a 5 min. Si existen los datos simulados
  locales de `data/sintetico/` (o de `$PLANTAIA_SINTETICO`; no versionados, se
  regeneran con `cd ml && /opt/anaconda3/bin/python -m plantaia_ml.relleno`,
  ver [ml/README.md](../ml/README.md)) se suman con su propia `fuente`; sin
  ellos, el notebook corre sólo con lo medido y los números cambian. La
  ejecución commiteada usa el relleno simulado **v2**, recalibrado tras
  [docs/entrega2/AUDITORIA_DATOS.md](../docs/entrega2/AUDITORIA_DATOS.md).
- **Protocolo**: partición por episodio (5 folds, ninguno partido entre train
  y test), búsqueda de hiperparámetros anidada también por episodio. Test
  externo sobre los episodios medidos (`fuente == 'real'`), con y sin los
  episodios dudosos (`EPISODIOS_DUDOSOS = {8, 9, 11, 14}`), y la referencia de
  entrenar sólo con reales, que reproduce el hallazgo del notebook 02.
- **Baselines**: clase mayoritaria y un umbral único sobre `suelo_mv`.
- **Candidatos**: regresión logística, árbol de decisión, Random Forest chico,
  Naive Bayes gaussiano, k-NN, SVM RBF y MLP chico.
- **Métricas**: exactitud balanceada, F1 macro, recall de `marchita`, matriz de
  confusión y ROC-AUC OvR cuando hay probabilidades, más la versión binaria
  *requiere cuidado* como análisis secundario.
- **Costo en la ESP32**: flash, RAM, operaciones por predicción y si se puede
  exportar sin librerías. La selección sigue el criterio de §5.3 (flash
  < 32 KB, sin memoria dinámica, < 1 ms por inferencia).
- **Modelo elegido**: `rf-f0-c42286`, Random Forest de 30 árboles,
  `max_depth=5`, `min_samples_leaf=20`, sólo `suelo_mv`. No supera con
  claridad al baseline de dos umbrales (ver `docs/entrega2/RESULTADOS.md`).
- **Export**: el modelo elegido se escribe en
  `firmware/lib/plantaia_ml/modelo_plantaia.h` con
  `cd ml && /opt/anaconda3/bin/python -m plantaia_ml.exportar_c`.

Las figuras se guardan en `docs/entrega2/fig/`. Se corre con el Python de
`/opt/anaconda3/bin/python` y las versiones de `ml/requirements.txt`.
