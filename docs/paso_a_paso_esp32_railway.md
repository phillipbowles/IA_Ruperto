# Paso a paso para integrar la ESP32 con Railway

## Objetivo

Dejar funcionando el siguiente flujo:

```text
Sensores -> ESP32 -> Wi-Fi -> HTTPS -> Backend en Railway -> PostgreSQL
                                                       |
                                                       +-> API y archivo CSV
```

Al finalizar, la ESP32 debe poder funcionar conectada solamente a un cargador USB, tomar las mediciones, mostrarlas localmente y enviarlas a Railway sin depender de una computadora encendida.

## Resultado que debe entregar el compañero

- Repositorio GitHub privado con el proyecto.
- Backend desplegado en Railway.
- PostgreSQL conectado al backend.
- URL pública de la API.
- Prueba de una medición guardada.
- Archivo `secrets.h` configurado únicamente en la computadora que carga la ESP32.
- Captura o registro de diez envíos consecutivos correctos.
- Confirmación de que una medición duplicada no crea otra fila.
- Confirmación de que el CSV se puede descargar.

## 1. Revisar el hardware

No es necesario cambiar los pines para utilizar Wi-Fi o Railway.

> **El mapa de pines está en [CLAUDE.md](../CLAUDE.md#mapa-de-pines-fijo-no-cambiar).**
> La tabla que estaba acá contradecía al firmware en tres filas (suelo,
> termistor y botón) y omitía el GPIO33 que alimenta la sonda. Se eliminó a
> propósito: un solo lugar define el cableado.

Comprobar antes de continuar:

- Todos los módulos comparten GND.
- Los sensores analógicos reciben 3,3 V.
- Cada LED tiene una resistencia de 220 a 330 ohmios.
- El botón está entre GPIO13 y GND, no entre GPIO13 y 3,3 V.
- La sonda de suelo recibe VCC desde GPIO33, no desde el riel de 3V3.
- La fuente USB es estable y el cable está en buenas condiciones.
- El lugar dispone de Wi-Fi de 2,4 GHz sin portal cautivo.

### Precaución con el LCD

Si el adaptador I2C del LCD se alimenta con 5 V, verificar que SDA y SCL no queden elevados a 5 V. La ESP32 trabaja con lógica de 3,3 V. Utilizar un conversor bidireccional de nivel I2C o alimentar el adaptador a 3,3 V si el módulo funciona correctamente así.

## 2. Obtener el proyecto

El repositorio contiene:

```text
backend/    API FastAPI, migraciones y despliegue Railway
firmware/   proyecto PlatformIO de la ESP32
frontend/   dashboard y pantalla de anotación
docs/       documentación y decisiones del proyecto
notebooks/  análisis de datos y entrenamiento
outputs/    informes
```

Una vez publicado en GitHub, clonar el repositorio:

```bash
git clone URL_DEL_REPOSITORIO
cd maceta-inteligente
```

Nunca agregar contraseñas, tokens, archivos `.env` ni `secrets.h` a Git.

## 3. Levantar el entorno local

No hace falta instalar Python, Postgres ni Node en la máquina: cada servicio
corre en su propio contenedor. Solo se necesita **Docker Desktop** andando.

Crear la configuración local:

```bash
cp .env.example .env
```

Editar `.env` y reemplazar `DEVICE_TOKEN` por uno largo y aleatorio
(`openssl rand -hex 32`). No reutilizar una contraseña personal.

Levantar todo:

```bash
docker compose up --build
```

La primera vez tarda: baja las imágenes y compila. Queda andando:

| Servicio | URL | Qué es |
|---|---|---|
| backend | http://localhost:8000/docs | la API con su Swagger |
| frontend | http://localhost:5173 | el dashboard |
| db | `localhost:5432` | Postgres 16 |

Las migraciones se aplican solas al arrancar. En los logs del backend tiene que
aparecer, antes de que levante el servidor:

```text
→ aplicando migraciones (alembic upgrade head)
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, Esquema inicial
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, Hora del dispositivo
→ migraciones al día
→ arrancando servidor
```

Si el backend se cae ahí, es una migración que falló: **no** hay que reiniciar
el contenedor hasta entender por qué. Está cortando a propósito para no servir
contra una base a medio migrar.

Para parar: `docker compose down`. Para parar y **borrar los datos**:
`docker compose down -v`.

## 4. Probar una medición local

Abrir http://localhost:8000/docs.

Probar `GET /health`. La respuesta esperada es:

```json
{"status":"ok"}
```

Después, desde `/docs`, abrir `POST /api/v1/mediciones`, pulsar **Try it out** y utilizar este ejemplo:

```json
{
  "dispositivo": "maceta-01",
  "numero_muestra": 1,
  "boot_id": 3,
  "firmware_version": "1.1.0",
  "ts_dispositivo_unix": 1757600000,
  "temperatura_c": 24.3,
  "humedad_ambiente_pct": 61,
  "luz_raw": 2870,
  "luz_mv": 2310,
  "luz_pct": 70,
  "suelo_raw": 1940,
  "suelo_mv": 1560,
  "suelo_pct": 54,
  "termistor_raw": 1820,
  "termistor_mv": 1470,
  "temp_ntc_c": 23.8,
  "condicion_codigo": 1,
  "condicion_etiqueta": "saludable",
  "etiqueta_origen": "manual",
  "wifi_rssi": -58,
  "errores": []
}
```

Agregar el encabezado:

```text
X-Device-Token: EL_TOKEN_CONFIGURADO
```

Resultados esperados:

- Sin token: `401 Unauthorized`.
- Con token correcto: `201 Created`.
- Repetir el mismo dispositivo y número de muestra: `200 OK` con `duplicado: true`.

Comprobar también:

```text
GET /api/v1/mediciones/ultima
GET /api/v1/mediciones
GET /api/v1/mediciones.csv
```

## 5. Crear el proyecto en Railway

1. Iniciar sesión en Railway.
2. Crear un proyecto nuevo.
3. Elegir **Deploy from GitHub repo**.
4. Autorizar el repositorio privado cuando Railway lo solicite.
5. Seleccionar el repositorio `maceta-inteligente`.
6. Esperar el primer build.

Railway construye con el **Dockerfile** del backend, según `backend/railway.json`.
En **Settings → Root Directory** hay que poner `backend`, o no lo encuentra.

El arranque lo define el `ENTRYPOINT` de la imagen: aplica las migraciones
pendientes y después levanta uvicorn en el `$PORT` que inyecta Railway.

> La primera vez hay que correr `railway run alembic stamp 0001`, porque la
> base ya tiene la tabla `mediciones` creada por el código viejo. Ver
> [backend/README.md](../backend/README.md).

El healthcheck configurado es:

```text
/health
```

## 6. Agregar PostgreSQL

Dentro del mismo proyecto Railway:

1. Pulsar **New**.
2. Seleccionar **Database**.
3. Seleccionar **PostgreSQL**.
4. Esperar a que el servicio quede disponible.
5. Abrir el servicio del backend.
6. Entrar en **Variables**.
7. Agregar una referencia a la variable `DATABASE_URL` del servicio PostgreSQL.

No copiar manualmente la contraseña de PostgreSQL dentro del código.

Cuando `DATABASE_URL` quede disponible, volver a desplegar el backend. La aplicación creará inicialmente la tabla `mediciones`.

## 7. Configurar las variables de Railway

En el servicio del backend, configurar:

```text
ENVIRONMENT=production
DEVICE_TOKEN=UN_TOKEN_LARGO_Y_ALEATORIO
DATABASE_URL=referencia al servicio PostgreSQL
```

Marcar `DEVICE_TOKEN` como variable sellada cuando la interfaz lo permita.

El mismo valor de `DEVICE_TOKEN` deberá colocarse después en `firmware/include/secrets.h`. No publicarlo en capturas, mensajes grupales o commits.

## 8. Generar la URL pública

1. Abrir el servicio del backend.
2. Entrar en **Settings**.
3. Buscar **Networking / Public Networking**.
4. Pulsar **Generate Domain**.

Railway entregará una dirección parecida a:

```text
https://maceta-inteligente-production.up.railway.app
```

Comprobar en el navegador:

```text
https://DOMINIO_RAILWAY/health
https://DOMINIO_RAILWAY/docs
```

No continuar con la ESP32 hasta que `/health` devuelva `{"status":"ok"}`.

## 9. Probar Railway antes de modificar la ESP32

En `/docs`, repetir la medición ficticia del paso 4 utilizando el token configurado en Railway.

Verificar:

- El backend devuelve `201 Created`.
- `GET /api/v1/mediciones/ultima` devuelve la misma lectura.
- `GET /api/v1/mediciones.csv` descarga un CSV con la lectura.
- Repetir el número de muestra no duplica la fila.

Si esta prueba falla, corregir primero Railway o PostgreSQL. No modificar sensores para intentar resolver un error del backend.

## 10. Preparar los secretos de la ESP32

Dentro de `firmware/include/`, copiar:

```text
secrets.example.h -> secrets.h
```

Completar solamente en la computadora local:

```cpp
#pragma once

#define WIFI_SSID "NOMBRE_WIFI"
#define WIFI_PASSWORD "CLAVE_WIFI"
#define API_URL "https://DOMINIO_RAILWAY/api/v1/mediciones"
#define DEVICE_TOKEN "EL_MISMO_TOKEN_DE_RAILWAY"
```

Antes de cualquier commit, ejecutar:

```bash
git status
```

Confirmar que `secrets.h` no aparece entre los archivos a subir.

## 11. Adaptar el firmware

Mantener el código de sensores que ya fue probado y agregar estas responsabilidades:

1. Conectar y reconectar el Wi-Fi.
2. Leer sensores cada 2 segundos.
3. Actualizar LCD y semáforo sin bloquear el programa.
4. Promediar varias lecturas analógicas.
5. Crear un número de muestra creciente.
6. Formar el JSON con todos los sensores.
7. Enviar por HTTPS cada 5 o 10 minutos.
8. Incluir `X-Device-Token` en la solicitud.
9. Mostrar el resultado en Serial y LCD.
10. Reintentar si falla la conexión.

No utilizar `delay()` largos para controlar el intervalo de envío. Utilizar `millis()` para que el botón, la pantalla y la reconexión continúen funcionando.

### Frecuencias recomendadas

| Acción | Intervalo |
|---|---:|
| Leer DHT11 | 2 segundos |
| Leer entradas analógicas | 2 segundos |
| Actualizar LCD | 2 segundos |
| Enviar durante pruebas | 30 segundos |
| Enviar durante recolección | 5 o 10 minutos |

## 12. Comportamiento del botón

Configurar GPIO13 así:

```cpp
pinMode(13, INPUT_PULLUP);
```

Comportamiento sugerido:

- Pulsación corta: cambiar la condición manual.
- Secuencia: `sin_etiquetar -> saludable -> estresada -> marchita`.
- Pulsación larga: forzar una medición y envío inmediato.

La condición manual debe representar una observación humana de la planta, no una categoría calculada automáticamente con el sensor de suelo.

## 13. Manejar errores y reintentos

La ESP32 debe interpretar:

| Resultado | Acción |
|---|---|
| `201` | Medición nueva guardada |
| `200` y `duplicado: true` | Medición ya guardada; no reenviar |
| `401` | Revisar el token |
| `422` | Revisar JSON o valores fuera de rango |
| `500` o `503` | Reintentar más tarde |
| Sin conexión o timeout | Reconectar y reintentar |

No incrementar definitivamente `numero_muestra` hasta guardar el identificador en memoria persistente. Si la placa se reinicia y vuelve a comenzar siempre desde cero, el backend podría considerar duplicadas las nuevas lecturas.

Para la primera prueba alcanza con reintentar en memoria. Después se recomienda guardar las mediciones fallidas en una cola limitada dentro de LittleFS o Preferences.

## 14. Prueba final sin computadora

1. Cargar el firmware definitivo mediante Arduino IDE.
2. Confirmar por Monitor Serie al menos dos envíos.
3. Desconectar la ESP32 de la computadora.
4. Conectarla a un cargador USB.
5. Esperar el intervalo de envío.
6. Abrir `/api/v1/mediciones/ultima` desde otro dispositivo.
7. Confirmar que la fecha y los valores cambiaron.
8. Apagar y encender el router o desconectar temporalmente la red.
9. Confirmar que la ESP32 sigue mostrando sensores localmente.
10. Restaurar Wi-Fi y comprobar que vuelve a enviar.

## 15. Lista de aceptación

Marcar cada punto antes de considerar terminada la tarea:

- [ ] El cableado coincide con la tabla.
- [ ] `/health` responde correctamente en Railway.
- [ ] PostgreSQL está conectado mediante `DATABASE_URL`.
- [ ] Un token incorrecto devuelve `401`.
- [ ] Una medición válida devuelve `201`.
- [ ] Un reintento no duplica la medición.
- [ ] La ESP32 se conecta sola después de reiniciarse.
- [ ] La ESP32 funciona con un cargador, sin computadora.
- [ ] El LCD muestra el estado de la nube.
- [ ] El botón devuelve una respuesta y registra la condición.
- [ ] Se observan diez envíos consecutivos.
- [ ] El CSV contiene timestamps, sensores y condición manual.
- [ ] `secrets.h` y `.env` no están en GitHub.
- [ ] El equipo conserva una copia del CSV fuera de Railway.

## 16. Información que debe comunicar al equipo

Al finalizar, enviar solamente:

- URL del repositorio.
- URL pública del backend.
- Estado de `/health`.
- Fecha y hora de la última medición.
- Cantidad de mediciones almacenadas.
- Captura del dashboard de Railway sin mostrar secretos.
- Problemas encontrados y decisiones tomadas.

No enviar contraseñas, `DATABASE_URL`, credenciales Wi-Fi ni `DEVICE_TOKEN` por el grupo.

## Referencias

- [Railway: despliegues desde GitHub](https://docs.railway.com/deployments/github-autodeploys)
- [Railway: PostgreSQL](https://docs.railway.com/databases/postgresql)
- [Railway: variables y secretos](https://docs.railway.com/variables)
- [Railway: dominios públicos y HTTPS](https://docs.railway.com/networking/public-networking)
- [Railway: healthchecks](https://docs.railway.com/deployments/healthchecks)
