import hashlib
import hmac
import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Foto
from ..photo_storage import photo_storage
from ..schemas import FotoGuardadaResponse, FotoOut
from .mediciones import verificar_token

router = APIRouter(prefix="/api/v1/fotos", tags=["fotos"])


def verificar_token_lectura(x_read_token: str | None = Header(None)) -> None:
    esperado = os.getenv("PHOTO_READ_TOKEN", "")
    if not esperado or not x_read_token or not hmac.compare_digest(x_read_token, esperado):
        raise HTTPException(status_code=401, detail="Token de lectura invalido o ausente")


def _salida(foto: Foto) -> FotoOut:
    return FotoOut(
        id=foto.id,
        dispositivo=foto.dispositivo,
        numero_foto=foto.numero_foto,
        content_type=foto.content_type,
        bytes=foto.bytes,
        sha256=foto.sha256,
        wifi_rssi=foto.wifi_rssi,
        recibido_en=foto.recibido_en,
        imagen_url=f"/api/v1/fotos/{foto.id}/imagen",
    )


@router.post("", response_model=FotoGuardadaResponse, status_code=status.HTTP_201_CREATED)
async def subir_foto(
    request: Request,
    response: Response,
    dispositivo: str = Query(min_length=1, max_length=64),
    numero_foto: int = Query(ge=0),
    wifi_rssi: int | None = Query(default=None, ge=-120, le=0),
    db: Session = Depends(get_db),
    _: None = Depends(verificar_token),
):
    existente = (
        db.query(Foto)
        .filter(and_(Foto.dispositivo == dispositivo, Foto.numero_foto == numero_foto))
        .first()
    )
    if existente:
        response.status_code = status.HTTP_200_OK
        return FotoGuardadaResponse(
            duplicado=True,
            id=existente.id,
            bytes=existente.bytes,
            sha256=existente.sha256,
            recibido_en=existente.recibido_en,
            imagen_url=f"/api/v1/fotos/{existente.id}/imagen",
        )

    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type != "image/jpeg":
        raise HTTPException(status_code=415, detail="Se requiere Content-Type image/jpeg")

    max_bytes = int(os.getenv("MAX_PHOTO_BYTES", "2097152"))
    contenido = bytearray()
    async for chunk in request.stream():
        contenido.extend(chunk)
        if len(contenido) > max_bytes:
            raise HTTPException(status_code=413, detail="La imagen supera el tamano permitido")
    data = bytes(contenido)

    if not data:
        raise HTTPException(status_code=400, detail="La imagen esta vacia")
    if len(data) < 4 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        raise HTTPException(status_code=422, detail="El archivo no parece un JPEG valido")

    recibido_en = datetime.now(UTC)
    digest = hashlib.sha256(data).hexdigest()
    dispositivo_seguro = "".join(c if c.isalnum() or c in "-_" else "_" for c in dispositivo)
    object_key = (
        f"{dispositivo_seguro}/{recibido_en:%Y/%m/%d}/"
        f"{numero_foto:012d}-{uuid.uuid4().hex[:12]}.jpg"
    )

    try:
        photo_storage.put(object_key, data, content_type)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="No se pudo almacenar la imagen") from exc

    foto = Foto(
        dispositivo=dispositivo,
        numero_foto=numero_foto,
        object_key=object_key,
        content_type=content_type,
        bytes=len(data),
        sha256=digest,
        wifi_rssi=wifi_rssi,
        recibido_en=recibido_en,
    )
    db.add(foto)
    try:
        db.commit()
        db.refresh(foto)
    except IntegrityError:
        db.rollback()
        photo_storage.delete(object_key)
        existente = (
            db.query(Foto)
            .filter(and_(Foto.dispositivo == dispositivo, Foto.numero_foto == numero_foto))
            .first()
        )
        if existente is None:
            raise
        response.status_code = status.HTTP_200_OK
        return FotoGuardadaResponse(
            duplicado=True,
            id=existente.id,
            bytes=existente.bytes,
            sha256=existente.sha256,
            recibido_en=existente.recibido_en,
            imagen_url=f"/api/v1/fotos/{existente.id}/imagen",
        )
    except Exception:
        db.rollback()
        photo_storage.delete(object_key)
        raise

    return FotoGuardadaResponse(
        id=foto.id,
        bytes=foto.bytes,
        sha256=foto.sha256,
        recibido_en=foto.recibido_en,
        imagen_url=f"/api/v1/fotos/{foto.id}/imagen",
    )


@router.get("", response_model=list[FotoOut], dependencies=[Depends(verificar_token_lectura)])
def listar_fotos(
    limite: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    fotos = db.query(Foto).order_by(Foto.recibido_en.desc()).limit(limite).all()
    return [_salida(foto) for foto in fotos]


@router.get("/ultima", response_model=FotoOut, dependencies=[Depends(verificar_token_lectura)])
def ultima_foto(db: Session = Depends(get_db)):
    foto = db.query(Foto).order_by(Foto.recibido_en.desc()).first()
    if foto is None:
        raise HTTPException(status_code=404, detail="Todavia no hay fotos")
    return _salida(foto)


@router.get("/{foto_id}/imagen", dependencies=[Depends(verificar_token_lectura)])
def obtener_imagen(foto_id: int, db: Session = Depends(get_db)):
    foto = db.get(Foto, foto_id)
    if foto is None:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    try:
        stream, content_type = photo_storage.get(foto.object_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Archivo de imagen no encontrado") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="No se pudo recuperar la imagen") from exc
    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )
