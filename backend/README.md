# Backend — API de PlantaIa

Todo se levanta desde la raíz del repo con `docker compose up --build`.
Este README solo documenta lo específico del servicio.

## Migraciones

El esquema lo administra **Alembic**, no `create_all()`. Las migraciones se
aplican solas en los dos entornos, por dos caminos distintos y a propósito:

| Entorno | Quién las corre | Si falla |
|---|---|---|
| local (compose) | `scripts/entrypoint.sh`, antes de uvicorn | el contenedor no arranca |
| Railway | `preDeployCommand` de `railway.json` | **el deploy se aborta y la versión vieja sigue sirviendo** |

En Railway el `preDeployCommand` es el que importa: corre una sola vez, antes de
que la instancia nueva tome tráfico, y un error cancela el deploy en vez de
dejar la app arriba contra un esquema viejo. El entrypoint igual sigue
corriendo `upgrade head` — cuando ya está al día es una consulta y nada más, y
es lo que hace que el compose local funcione sin configuración extra.

Como los dos caminos pueden solaparse (Railway levanta la instancia nueva
mientras la vieja sigue viva), `alembic/env.py` toma un **advisory lock de
Postgres** antes de migrar: el segundo proceso espera en lugar de intentar
aplicar la misma revisión.

```bash
# crear una revisión nueva a partir de los cambios en app/models.py
docker compose exec backend alembic revision --autogenerate -m "descripcion corta"

# aplicar / revertir a mano
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1

# ¿los modelos y el esquema están sincronizados?
docker compose exec backend alembic check
```

`alembic check` es el que conviene correr antes de commitear: si devuelve
operaciones pendientes, alguien tocó `models.py` sin generar la migración.

### Primera vez sobre la base de Railway

Depende de si la tabla `mediciones` ya existe en producción. Para saberlo:

```bash
railway connect Postgres
\dt
```

- **Si `mediciones` NO aparece** (el caso al 2026-09-11: el servicio del backend
  tuvo un solo deploy y falló, así que `create_all()` nunca llegó a correr):
  no hay que hacer nada. `alembic upgrade head` crea la cadena entera.

- **Si `mediciones` SÍ aparece** pero no hay tabla `alembic_version`: la creó
  `create_all()` antes de que existieran las migraciones. Alembic no lo sabe y
  va a intentar crearla de nuevo. Hay que marcar la revisión inicial como
  aplicada **una sola vez**, antes del primer deploy con migraciones:

  ```bash
  railway run alembic stamp 0001
  ```

  A partir de ahí `upgrade head` aplica 0002 en adelante con normalidad.

En local nunca hace falta: la base del compose nace vacía y corre todo.

## Variables de entorno

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | Postgres. Railway la entrega como referencia al servicio |
| `DEVICE_TOKEN` | el mismo valor que en `firmware/include/secrets.h` |
| `CORS_ORIGENES` | orígenes del front, separados por coma |
| `PORT` | lo inyecta Railway; en local cae a 8000 |

## Notebooks

`features.py` tiene que ser el mismo código en el entrenamiento y en la
inferencia, o el modelo anda en el notebook y falla en producción sin avisar:

```bash
pip install -e "backend/[ml]"
# from app.ml.features import construir_features
```
