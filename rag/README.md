# rag — corpus e índice de Ruperto (Tarea 3)

Contrato: [docs/ENTREGA3.md](../docs/ENTREGA3.md) §4. Decisiones: D3, D4, D11,
D12 y D101 en adelante.

```
rag/corpus/ciencia/    fuentes públicas sobre Spathiphyllum, una por .md (a mano)
rag/corpus/proyecto/   lo que Ruperto sabe de sí mismo (a mano)
data/mediciones_raw_*.csv + data/episodios.csv → historial (lo genera el script)
rag/construir_indice.py → backend/app/bot/indice/{chunks.jsonl, embeddings.npy, meta.json}
```

`backend/app/bot/indice/` es **GENERADO**: no se edita a mano, se regenera.

## Regenerar el índice

Desde la raíz del repo:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r rag/requirements.txt

# La clave sale del entorno o de un .env (por defecto el .env de la raíz).
.venv/bin/python -m rag.construir_indice --env-file /ruta/al/.env
```

- Usa el `mediciones_raw_*.csv` más nuevo de `data/` (o `--snapshot`).
- Modelo: `GEMINI_MODELO_EMBED` (default `gemini-embedding-001`), dimensión 768
  (`--dim` para cambiarla), `task_type=RETRIEVAL_DOCUMENT`, lotes de 20 con 1 s
  de pausa y reintento con espera exponencial ante un 429.
- Sin `GEMINI_API_KEY` sale con código 2 y no escribe nada. Arma todo en
  memoria y escribe al final, en una carpeta temporal que reemplaza a la vieja.
- `--solo-chunks` lista los chunks (id, palabras, título) sin red.

**Quien consulta el índice** (`backend/app/bot/recuperar.py`) tiene que embeber
la pregunta con el mismo `modelo_embed` y la misma `dim` de `meta.json`, con
`task_type=RETRIEVAL_QUERY`, y normalizarla: el coseno es el producto punto.

## Qué hay en cada fuente

- **ciencia**: extractos textuales (en inglés, el idioma original) de UF/IFAS
  (3 publicaciones EDIS + Gardening Solutions), NC State Extension, RHS (2),
  ASPCA y un artículo open access (BMC Plant Biology 2024, CC BY 4.0). La
  cabecera de cada archivo tiene título, institución, URL y fecha de acceso.
  Para agregar una fuente: un `.md` nuevo con la misma cabecera y secciones `## `.
- **proyecto**: cómo mide la sonda, cómo decide el semáforo, limitaciones,
  datos y etiquetas. Redactado desde CLAUDE.md, docs/CALIBRACION.md,
  docs/ENTREGA2.md y docs/entrega2/RESULTADOS.md. Si cambia el modelo o la
  placa, actualizarlo y regenerar.
- **historial**: un chunk por día (hora de Montevideo) y uno por episodio. Sale
  de `plantaia_ml.dataset.serie_maceta01` (une `maceta-02`, remuestrea a 5 min,
  calcula las features como la placa); los riegos son las filas con
  `h_desde_riego == 0`, la misma regla del contrato de features.

## Tests

```bash
.venv/bin/python -m pytest -q rag/tests     # sin red y sin clave
```
