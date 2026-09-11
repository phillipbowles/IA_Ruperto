# Arquitectura — PlantaIa

> Documento de decisiones. Complementa a [CLAUDE.md](../CLAUDE.md), que sigue
> siendo la fuente de verdad para pines, etiquetas y vocabulario de datos.

## 1. El problema real

No es "guardar mediciones". Es producir un dataset con el que se pueda
**entrenar y evaluar honestamente** un clasificador de 3 clases, sabiendo que:

- las etiquetas son humanas, escasas y llegan **en rachas**, no fila por fila;
- se corrigen a posteriori ("el martes ya estaba estresada y no me di cuenta");
- lo que discrimina marchitez es la **dinámica** (deltas, medias móviles), no el
  valor instantáneo;
- el sensor de suelo se degrada a lo largo de las semanas.

Cada decisión de abajo sale de alguno de esos cuatro puntos.

---

## 2. Vista general

```
┌───────────────┐   POST /mediciones        ┌──────────────────────────────┐
│    ESP32      │   POST /mediciones/lote   │   backend  (FastAPI/Railway) │
│  + LittleFS   │ ────────────────────────► │   ├─ ingesta (idempotente)   │
│  (buffer)     │ ◄──────────────────────── │   ├─ ml/features.py ◄──┐     │
└───────────────┘  {prediccion, proba}      │   ├─ ml/inferencia.py  │     │
                                            │   └─ /dataset.csv      │     │
┌───────────────┐  POST /etiquetas          └───────────┬────────────┼─────┘
│   frontend    │  POST /eventos                        │            │
│ (React/Vite)  │ ────────────────────────►        ┌────▼─────┐      │
│               │ ◄── GET /estado /serie           │ Postgres │      │
└───────────────┘                                  └────┬─────┘      │
                                                        │            │
┌───────────────┐   GET /dataset.csv                    │            │
│   notebooks   │ ◄─────────────────────────────────────┘            │
│   (sklearn)   │ ── entrena ── modelo.joblib ── commit ── deploy ────┘
└───────────────┘        (importa el MISMO features.py)
```

La flecha que cierra el círculo es la clave: **el notebook y la API comparten
`features.py`**. Si el entrenamiento y la inferencia calculan las features con
código distinto, el modelo anda en el notebook y falla en producción, y el error
es silencioso. Un solo módulo, importado desde los dos lados.

---

## 3. Modelo de datos: cuatro tablas, no una

La tabla plana actual mezcla cosas con ciclos de vida incompatibles. Separarlas
resuelve de una vez el esquema del CSV, el `etiqueta_origen` y el leakage.

### 3.1 `mediciones` — hechos inmutables

Lo que la placa midió. **Nunca se edita ni se borra.** Ya implementada.
Clave de idempotencia: `(dispositivo, numero_muestra)`.

### 3.2 `etiquetas` — episodios, no filas

**Esta es la decisión central del diseño.** La verdad de campo no es un valor por
muestra: es un intervalo de tiempo durante el cual la planta estuvo en un estado.

```sql
CREATE TABLE etiquetas (
    id           SERIAL PRIMARY KEY,
    dispositivo  VARCHAR(50)  NOT NULL,
    ts_inicio    TIMESTAMPTZ  NOT NULL,
    ts_fin       TIMESTAMPTZ,              -- NULL = episodio abierto, en curso
    clase        VARCHAR(30)  NOT NULL,    -- saludable | estresada | marchita
    origen       VARCHAR(20)  NOT NULL,    -- manual | corregida
    autor        VARCHAR(50),
    nota         TEXT,
    creado_en    TIMESTAMPTZ  DEFAULT now(),
    CHECK (ts_fin IS NULL OR ts_fin > ts_inicio)
);

-- Dos episodios del mismo dispositivo no pueden pisarse en el tiempo.
-- Sin esto, una corrección mal hecha produce filas con dos etiquetas y el bug
-- aparece recién en el notebook, semanas después.
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE etiquetas ADD CONSTRAINT sin_solapamiento
    EXCLUDE USING gist (
        dispositivo WITH =,
        tstzrange(ts_inicio, COALESCE(ts_fin, 'infinity')) WITH &&
    );
```

Lo que se gana:

| | Etiqueta por fila (hoy) | Episodios |
|---|---|---|
| Corregir un día entero | `UPDATE` de ~300 filas | `UPDATE` de 1 fila |
| Saber qué fue observación real | imposible | `origen` del episodio |
| Grupo para el CV | hay que inventarlo | `episodio_id`, gratis |
| Reetiquetar el pasado | reescribe hechos | no toca `mediciones` |

La propagación deja de ser un dato guardado y pasa a ser un `JOIN`.

### 3.3 `eventos` — lo que hace el humano

Riegos, cambios de escena de luz, pesajes, fotos, notas. Hoy no tienen dónde ir.

```sql
CREATE TABLE eventos (
    id           SERIAL PRIMARY KEY,
    dispositivo  VARCHAR(50)  NOT NULL,
    ts           TIMESTAMPTZ  NOT NULL,
    tipo         VARCHAR(20)  NOT NULL,   -- riego|cambio_luz|lampara_on|lampara_off
    escena_luz   VARCHAR(20),             -- velo_abierto|velo_cerrado|pantalla|lampara
    peso_g       REAL,
    foto_url     TEXT,
    nota         TEXT,
    autor        VARCHAR(50),
    creado_en    TIMESTAMPTZ  DEFAULT now()
);
CREATE INDEX ix_eventos_ts ON eventos (dispositivo, ts);
```

`horas_desde_riego` sale de acá y es, casi seguro, una de las features más
predictivas del modelo.

### 3.4 `predicciones` — salida del modelo, separada de la verdad

```sql
CREATE TABLE predicciones (
    id             SERIAL PRIMARY KEY,
    medicion_id    INTEGER     NOT NULL REFERENCES mediciones(id) ON DELETE CASCADE,
    modelo_version VARCHAR(40) NOT NULL,
    clase          VARCHAR(30) NOT NULL,
    proba          REAL,
    ts             TIMESTAMPTZ DEFAULT now(),
    UNIQUE (medicion_id, modelo_version)
);
```

**Nunca** en la misma columna que la etiqueta humana. Si se mezclan, en dos
semanas nadie va a poder decir cuál dato era observación y cuál era el modelo
prediciéndose a sí mismo.

### 3.5 La vista de dataset

El CSV de 20 columnas de CLAUDE.md **es esto**, no una tabla:

```sql
CREATE VIEW v_dataset AS
SELECT m.*,
       e.id     AS episodio_id,     -- el grupo para GroupKFold
       e.clase  AS etiqueta,
       e.origen AS etiqueta_origen
  FROM mediciones m
  LEFT JOIN etiquetas e
         ON e.dispositivo = m.dispositivo
        AND m.ts_dispositivo >= e.ts_inicio
        AND (e.ts_fin IS NULL OR m.ts_dispositivo < e.ts_fin);
```

Las filas sin episodio quedan con `etiqueta NULL` — que es exactamente lo que
hay que excluir del entrenamiento, sin inventar una clase `sin_etiquetar`.

---

## 4. Estructura del repo

```
IA_Ruperto/
├── docker-compose.yml           dev local: db + backend + frontend
├── .env.example                 variables del compose (copiar a .env)
├── CLAUDE.md                    fuente de verdad: pines, etiquetas, datos
│
├── firmware/                    ESP32 — PlatformIO
│   ├── platformio.ini           versiones de librerías FIJADAS
│   ├── src/main.cpp
│   ├── include/
│   │   ├── secrets.h            gitignored
│   │   └── secrets.example.h
│   └── test/test_dht/           sketch de diagnóstico aislado
│
├── backend/                     API — Python 3.11
│   ├── Dockerfile               targets: dev (reload) y prod (sin root)
│   ├── .dockerignore
│   ├── pyproject.toml           dependencias + extras [dev] y [ml]
│   ├── railway.json             builder DOCKERFILE
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py               toma la URL de DATABASE_URL, nunca del .ini
│   │   └── versions/            0001_, 0002_… numeradas a mano
│   ├── scripts/entrypoint.sh    alembic upgrade head && uvicorn
│   ├── app/
│   │   ├── main.py              app, routers, CORS
│   │   ├── database.py
│   │   ├── models/              una tabla por archivo
│   │   ├── schemas/             Pydantic de entrada y salida
│   │   ├── routers/
│   │   │   ├── mediciones.py    ingesta y series
│   │   │   ├── etiquetas.py     episodios
│   │   │   ├── eventos.py       riegos, luz, peso, fotos
│   │   │   ├── dataset.py       /dataset.csv
│   │   │   └── modelo.py        metadatos y métricas del modelo activo
│   │   ├── servicios/           lógica que no es HTTP ni SQL
│   │   └── ml/
│   │       ├── features.py      ◄── COMPARTIDO con los notebooks
│   │       ├── inferencia.py    carga el .joblib y predice
│   │       └── artefactos/modelo_v1.joblib
│   └── tests/
│
├── frontend/                    dashboard — React + TypeScript + Vite
│   ├── Dockerfile               dev (vite) · build · prod (nginx)
│   ├── nginx.conf.template      estáticos + proxy /api
│   ├── package.json
│   └── src/
│       ├── api/                 cliente tipado + hooks de TanStack Query
│       ├── componentes/
│       ├── paginas/
│       │   ├── Estado.tsx       semáforo, última lectura, placa online
│       │   ├── Series.tsx       series temporales con eventos marcados
│       │   ├── Anotar.tsx       episodios y eventos — mobile first
│       │   └── Modelo.tsx       matriz de confusión, predicho vs real
│       └── tipos.ts
│
├── notebooks/                   01_eda · 02_features · 03_modelo
├── docs/                        ARQUITECTURA · CALIBRACION · paso_a_paso
└── outputs/
```

### El detalle que hace que `features.py` se comparta

`backend/pyproject.toml` declara el paquete como instalable. Desde la raíz:

```bash
pip install -e "backend/[ml]"
```

y los notebooks hacen `from app.ml.features import construir_features`. Es el
mismo código que corre en la API. Sin esto, la separación de carpetas garantiza
el train/serve skew en vez de evitarlo.

---

## 5. Manejo del stack

Cada servicio corre en su propio contenedor, en desarrollo y en producción. La
razón concreta: la máquina de Manuel y la tuya dejan de importar, y el backend
que se despliega en Railway es **la misma imagen** que probaste en local.

| Capa | Runtime | Dependencias | Imagen | Despliegue |
|---|---|---|---|---|
| firmware | Arduino core 2.0.x (`espressif32@6.9.0`) | `platformio.ini`, versiones fijas | — | `pio run -t upload` |
| backend | Python 3.11 | `pyproject.toml` (+ extras `[dev]`, `[ml]`) | `python:3.11-slim`, targets `dev`/`prod` | Railway, builder `DOCKERFILE` |
| base | Postgres 16 | — | `postgres:16-alpine` | Railway Postgres |
| frontend | Node 20 | `package.json` | `node:20-alpine` → `nginx:1.27-alpine` | Railway o Vercel |
| notebooks | el venv del backend | `pip install -e "backend/[ml]"` | — | — |

### Levantar todo en local

```bash
cp .env.example .env          # completar DEVICE_TOKEN
docker compose up --build
```

Deja andando:

| Servicio | Dónde | Qué hace |
|---|---|---|
| `db` | `localhost:5432` | Postgres 16, datos en el volumen `datos_pg` |
| `backend` | `localhost:8000` | migra y arranca con `--reload`; `/docs` tiene el Swagger |
| `frontend` | `localhost:5173` | Vite con hot reload, proxy a `/api` |

`docker compose down` para; `down -v` borra también los datos.

### Migraciones automáticas

`backend/scripts/entrypoint.sh` corre `alembic upgrade head` **antes** de
levantar uvicorn. Tres decisiones detrás de eso:

- **`set -e`**: si una migración falla, el contenedor no arranca. Es preferible
  un servicio caído a uno sirviendo contra una base a medio migrar.
- **`head` y no `heads`**: `heads` aplica todas las ramas de un árbol de
  revisiones bifurcado. Acá la historia es lineal a propósito; si algún día
  aparece una bifurcación, lo que corresponde es mergearla, no aplicar las dos.
- **`depends_on: service_healthy`**: sin el healthcheck de Postgres, Alembic
  corre contra una base que todavía no acepta conexiones y el primer arranque
  muere.

En **producción** el que manda es el `preDeployCommand` de `railway.json`: corre
`alembic upgrade head` una sola vez antes de que la instancia nueva tome
tráfico, y si falla **aborta el deploy** dejando la versión vieja sirviendo —
mejor que el entrypoint, que solo puede negarse a arrancar. Los dos caminos
pueden solaparse, así que `env.py` toma un advisory lock de Postgres antes de
migrar y el segundo proceso espera.

`create_all()` ya no existe en el código: dos mecanismos creando tablas es la
forma más rápida de que el esquema de local y el de producción se separen sin
que nadie se entere.

> ⚠️ **La base de Railway ya tiene la tabla `mediciones`**, creada por
> `create_all()` antes de que hubiera migraciones. Antes del primer deploy con
> Alembic hay que correr `railway run alembic stamp 0001` una sola vez, o la
> revisión inicial va a fallar intentando crear una tabla que ya existe. El
> detalle está en [backend/README.md](../backend/README.md).

> ⚠️ **Railway: Settings → Root Directory = `backend`.** Sin eso no encuentra el
> Dockerfile ni el `railway.json`.

### Reglas que valen para las tres capas

1. **Todo pineado.** Nada de `*` ni de `latest`, tampoco en las imágenes base.
   El mismo commit tiene que producir el mismo build en cualquier máquina.
2. **Los secretos nunca en el repo.** `firmware/include/secrets.h` y el `.env`
   de la raíz están en `.gitignore`, con un `.example` al lado.
3. **El esquema se cambia solo por migración.** Tocar `models.py` sin generar la
   revisión correspondiente lo detecta `alembic check`.

## 6. Superficie de la API

| Método | Ruta | Quién | Para qué |
|---|---|---|---|
| `POST` | `/api/v1/mediciones` | placa | ingesta, idempotente |
| `POST` | `/api/v1/mediciones/lote` | placa | vaciar el buffer de LittleFS |
| `GET` | `/api/v1/mediciones` | front | serie, con `?desde=&hasta=&resolucion=` |
| `GET` | `/api/v1/estado` | front | última lectura, placa online, episodio abierto |
| `POST` | `/api/v1/etiquetas` | front | abrir episodio |
| `PATCH` | `/api/v1/etiquetas/{id}` | front | cerrar o corregir |
| `POST` | `/api/v1/eventos` | front | riego, luz, peso, foto, nota |
| `GET` | `/api/v1/dataset.csv` | notebook | las 20 columnas, joineadas |
| `GET` | `/api/v1/modelo` | front | versión activa y métricas |
| `POST` | `/api/v1/auth/login` | front | contraseña compartida → JWT |

Dos autenticaciones distintas, a propósito: la placa usa `X-Device-Token` (fijo,
sin sesión); las personas usan un JWT corto. Un token filtrado en el firmware no
puede reescribir etiquetas.

### `?resolucion=` — por qué está en la API y no en el gráfico

Tres semanas a 5 minutos son ~6000 puntos por serie. Es demasiado para un
gráfico SVG y es innecesario para mirar tendencias. El backend agrega por
ventana (`5m`, `1h`, `6h`) y devuelve lo que el gráfico puede dibujar. Resolver
esto en el servidor deja al front simple y evita tener que cambiar de librería
de gráficos cuando el dataset crezca.

---

## 7. Dónde corre el modelo

**La predicción viaja en la respuesta del mismo POST que ingesta la muestra.**

```
ESP32 ──POST medición──► backend ─► guarda ─► features(últimas 24 h) ─► modelo
       ◄──{"prediccion":"estresada","proba":0.81}──────────────────────────┘
       └─► prende el LED
```

Las alternativas y por qué no:

| Opción | Problema |
|---|---|
| Umbrales del árbol como `if` en el firmware | las features son medias móviles de 1 h / 6 h / 24 h: habría que guardar 288 muestras y mantener ventanas en la placa. Y cada reentrenamiento obliga a reflashear. |
| `GET /prediccion` aparte | un request de más cada 5 minutos, para un dato que el backend ya calculó en el request anterior. |
| Predecir en el front | el semáforo físico quedaría dependiendo de que alguien tenga la pantalla abierta. |

Con la respuesta del POST: cero requests extra, cero features en la placa, y el
modelo se actualiza redesplegando el backend sin tocar el hardware.

El campo ya está reservado en `MedicionResponse` (`prediccion`, `proba`), en
`null` hasta que haya modelo entrenado.

---

## 8. Pipeline de ML

**Features** — el instante no discrimina; la dinámica sí:

- `suelo_mv` y deltas a 1 h / 6 h / 24 h, y pendiente de la ventana.
- `horas_desde_riego` (de `eventos`, con `merge_asof`).
- **VPD** (déficit de presión de vapor) a partir de `temperatura_c` y
  `humedad_ambiente_pct`. Advertencia honesta: el DHT11 tiene ±5 % en humedad y
  1 °C de resolución, así que el VPD va a ser ruidoso. Sirve como tendencia, no
  como medida.
- `luz_nivel` categórico a partir de los cortes de `docs/CALIBRACION.md`, no
  `luz_pct` — el ADC satura y la respuesta del LDR es logarítmica.
- Hora del día y ciclo día/noche.

**Modelo** — árbol de decisión o Random Forest chico. La justificación es
interpretabilidad (los umbrales se muestran en el informe) y el tamaño del
dataset, no la performance.

**Evaluación — el punto que define si el trabajo es serio:**

- Split por **bloques temporales**, agrupando por `episodio_id` (`GroupKFold`).
  Un split aleatorio da ~98 % de accuracy que es puro leakage: muestras
  contiguas del mismo episodio comparten etiqueta por construcción.
- **El N efectivo son los episodios, no las filas.** En 3 semanas van a ser
  ~6000 filas y tal vez 15–20 episodios. Con 15 grupos, el test queda en 3–4
  episodios y la barra de error de la accuracy es enorme. **Eso es irreducible**
  y no se arregla muestreando más rápido.
- Conclusión metodológica para el informe: reportar
  `accuracy ± desvío, con N efectivo = k episodios, evaluado por GroupKFold`.
  Un 72 % ± 15 % bien medido vale más que un 98 % con leakage, y demuestra que
  se entendió el problema.
- Baseline obligatorio: clase mayoritaria. Si el modelo no le gana con claridad,
  eso también es un resultado y hay que decirlo.

---

## 9. Stack del frontend

**React 18 + TypeScript + Vite.**

| Pieza | Elección | Por qué |
|---|---|---|
| Build | **Vite** | dev server instantáneo, build estático, cero config |
| Lenguaje | **TypeScript** | los tipos del CSV y de las etiquetas son el corazón del proyecto; errarle a un nombre de campo tiene que fallar al compilar |
| Estado del servidor | **TanStack Query v5** | `refetchInterval` para el panel en vivo, cache, mutaciones optimistas al anotar. Reemplaza casi todo el estado global |
| Ruteo | **React Router v6** | cuatro pantallas, no hace falta más |
| Gráficos | **Recharts** | declarativo, buena DX. Alcanza porque el backend manda la serie ya agregada (`?resolucion=`). Si algún día hace falta dibujar 30 k puntos crudos, se cambia por **uPlot** sin tocar el resto |
| Estilos | **Tailwind CSS v4 + shadcn/ui** | componentes accesibles (Radix abajo) sin diseñar desde cero |
| Formularios | **React Hook Form + Zod** | la pantalla de anotación es puro formulario, y Zod comparte el esquema con la validación |
| Fechas | **date-fns** | liviano y explícito con zonas horarias |
| Paquetes | **npm** | viene con Node, un componente menos en la imagen. Todavía no hay lockfile: commitear el `package-lock.json` que queda después del primer `docker compose up` |

### Alternativas descartadas

| Opción | Por qué no |
|---|---|
| Next.js | SSR y rutas de servidor que no se usan; el backend ya es FastAPI. Complejidad sin beneficio |
| Streamlit | rapidísimo para explorar, pero no sirve como producto ni para anotar desde el celular |
| Jinja + Chart.js en FastAPI | la opción más barata y es defendible, pero deja el front sin estructura propia y sin tipos justo donde más hacen falta |
| SvelteKit | buena opción técnica; pierde contra React por ecosistema y porque es lo que el equipo ya conoce |

### La pantalla que más importa

No son los gráficos: es **`Anotar.tsx`**, y tiene que ser **mobile first**,
porque se usa parado al lado de la maceta con el celular en la mano.

- abrir / cerrar / corregir un episodio de etiqueta en dos toques;
- registrar riego, escena de luz, peso y foto con el timestamp del momento;
- ver el episodio abierto y desde cuándo, para no duplicarlo.

El botón físico solo puede expresar 4 estados y no puede corregir nada. Esta
pantalla es la que realmente genera la verdad de campo del dataset.

> **Fotos:** el disco de un contenedor de Railway es efímero — lo que se sube se
> pierde en el próximo deploy. Arrancar guardando solo `foto_url` (Drive o el
> celular) y, si después hacen falta uploads de verdad, montar un Railway Volume
> o un bucket externo. No subir archivos al filesystem del contenedor.

---

## 10. Orden de trabajo

Los pasos 1 y 2 eran los urgentes: **todo lo que se recolecte sin ellos es dato
degradado y no se recupera después.**

1. ~~Resolver las contradicciones; CLAUDE.md como fuente única~~ ✅
2. ~~`ts_dispositivo`, `condicion` persistida, `errores` reales, canales crudos completos~~ ✅
3. ~~Contenedores por servicio, Postgres local y migraciones automáticas con Alembic~~ ✅
4. `railway run alembic stamp 0001` y redeploy con el builder Dockerfile
5. Migración `0003`: episodios, eventos y predicciones + `/dataset.csv` + endpoint de lote
6. Calibrar suelo y luz con el sustrato real ([docs/CALIBRACION.md](CALIBRACION.md))
7. Buffer LittleFS con reenvío por lote
8. **Arrancar la recolección en serio** + `Anotar.tsx` en paralelo —
   la pantalla de anotación se necesita desde el día 1, no después
9. `01_eda.ipynb` con lo que haya
10. `features.py` compartido → modelo → cerrar el loop por la respuesta del POST
