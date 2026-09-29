# ESP32-CAM: fotos cada 5 minutos

La camara es una segunda placa independiente del logger de sensores. Publica
JPEG en `POST /api/v1/fotos`; el backend guarda el archivo en un Railway Bucket
privado y sus metadatos en Postgres.

## Railway

1. Crear un **Bucket** en la misma region del backend.
2. Desde el Bucket, inyectar sus credenciales S3 al servicio `Backend`.
3. Agregar al backend:
   - `PHOTO_STORAGE_REQUIRED=true`
   - `MAX_PHOTO_BYTES=2097152`
   - `PHOTO_READ_TOKEN=<token diferente de DEVICE_TOKEN>`
4. La camara usa el `DEVICE_TOKEN` que ya autentica las mediciones.

El backend acepta los nombres `AWS_*` de `railway bucket credentials` y tambien
los nombres nativos `BUCKET`, `ENDPOINT`, `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY` y
`REGION` que Railway ofrece como referencias.

## Endpoints

| Metodo | Ruta | Cabecera |
|---|---|---|
| POST | `/api/v1/fotos?dispositivo=esp32-cam-01&numero_foto=0` | `X-Device-Token` |
| GET | `/api/v1/fotos` | `X-Read-Token` |
| GET | `/api/v1/fotos/ultima` | `X-Read-Token` |
| GET | `/api/v1/fotos/{id}/imagen` | `X-Read-Token` |

Los reintentos son idempotentes por `(dispositivo, numero_foto)`.

## Volumen esperado

Una foto cada 5 minutos son 288 fotos por dia y 8.640 en 30 dias. Con JPEG de
100 a 300 KB, el crecimiento aproximado es de 0,9 a 2,6 GB por mes. Definir una
politica de retencion antes de dejarla funcionando por varios meses.

## Privacidad

Orientar la camara solo hacia la planta y evitar personas, pantallas, papeles o
espacios privados. Los objetos del Bucket son privados; no se exponen las
credenciales S3 a la placa.
