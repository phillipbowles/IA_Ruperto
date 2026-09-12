# Backend — API de PlantaIa

Todo se levanta desde la raíz del repo con `docker compose up --build`.
Este README solo documenta lo específico del servicio.

## Migraciones

El esquema lo administra **Alembic**, no `create_all()`. Las migraciones se
aplican solas en los dos entornos, por dos caminos distintos y a propósito:

| Entorno | Quién las corre | Si falla |
|---|---|---|
| local (compose) | `scripts/entrypoint.sh`, antes de uvicorn | el contenedor no arranca |
| Railway | `preDeployCommand` del servicio | **el deploy se aborta y la versión vieja sigue sirviendo** |

En Railway el `preDeployCommand` es el que importa: corre una sola vez, antes de
que la instancia nueva tome tráfico, y un error cancela el deploy en vez de
dejar la app arriba contra un esquema viejo. El entrypoint igual sigue
corriendo `upgrade head` — cuando ya está al día es una consulta y nada más, y
es lo que hace que el compose local funcione sin configuración extra.

> **`railway.json` está deprecado y Railway lo ignora en silencio.** Por eso este
> repo ya no lo tiene: un archivo que parece la configuración pero no la es
> cuesta más que no tenerlo. Los settings viven en el servicio y se ven con
> `railway api`. Para cambiarlos, el dashboard o:
>
> ```bash
> railway api 'mutation($s:String!,$e:String!,$i:ServiceInstanceUpdateInput!){serviceInstanceUpdate(serviceId:$s,environmentId:$e,input:$i)}' \
>   --variables '{"s":"<serviceId>","e":"<envId>","i":{"healthcheckPath":"/health"}}'
> ```
>
> Si en algún momento se quiere la config versionada en el repo, el camino que
> Railway soporta hoy es IaC (`.railway/railway.ts`).

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

## Producción

| | |
|---|---|
| API (la que usa la ESP32) | `https://backend-production-a379.up.railway.app` |
| Dashboard | `https://frontend-production-a3ff.up.railway.app` |

Settings del servicio Backend en Railway, ya configurados:

| Setting | Valor | Por qué |
|---|---|---|
| Root Directory | `backend` | si no, no encuentra el Dockerfile |
| `PORT` | `8000` | fijo, para que el puerto del dominio sea predecible |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | referencia, no la contraseña copiada |
| `DEVICE_TOKEN` | el mismo de `firmware/include/secrets.h` | |
| `CORS_ORIGENES` | la URL del Frontend | |
| Healthcheck | `/health` | |

### uvicorn escucha en 0.0.0.0, no en `::`

Parece que `::` sería mejor porque cubriría IPv4 e IPv6, pero **asyncio pone
`IPV6_V6ONLY=1` en todo socket IPv6**: con `--host ::` uvicorn acepta *solo*
IPv6. La red privada de Railway es IPv6 y el edge público llega por IPv4, así
que con `::` el front entra pero la ESP32 se come un 502.

Como la ESP32 necesita el endpoint público, el backend escucha en `0.0.0.0` y el
Frontend tiene `BACKEND_URL` apuntando a la URL pública en vez de a
`*.railway.internal`. Para servir las dos familias a la vez haría falta gunicorn
con dos `-b`; para este proyecto no vale la pena.
