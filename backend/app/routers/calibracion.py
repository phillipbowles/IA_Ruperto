"""Calibración del análisis de fotos (docs/VISION_CLASICA.md §5).

Se sube una foto con lo que una persona observó (estado y, si quiere, un
puntaje de 0 a 100). La foto va al Railway Bucket, bajo `calibracion/`, y la
fila guarda la etiqueta humana junto a lo que dijeron la visión clásica y,
opcionalmente, la IA. `GET /evaluacion` corre la visión clásica ACTUAL sobre
todas las fotos guardadas: es el lazo para iterar sobre sus errores.

Todo pide `X-Calibracion-Token`: las fotos son de una casa y pueden mostrar
personas (reflejos), así que ni se suben ni se leen sin la clave.
"""

import hashlib
import hmac
import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .. import vision
from ..database import get_db
from ..models import CalibracionFoto
from ..photo_storage import photo_storage
from ..schemas import CalibracionOut, EvaluacionFila, EvaluacionOut
from .analisis import analizar_con_ia, analizar_con_vision, leer_imagen

router = APIRouter(prefix="/api/v1/calibracion", tags=["calibracion"])
log = logging.getLogger("uvicorn.error")

CLASES = ("saludable", "estresada", "marchita")
EXTENSIONES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}


def verificar_token_calibracion(x_calibracion_token: str | None = Header(None)) -> None:
    esperado = os.getenv("CALIBRACION_TOKEN", "")
    if not esperado:
        raise HTTPException(status_code=503, detail="La calibración no está configurada (falta CALIBRACION_TOKEN)")
    if not x_calibracion_token or not hmac.compare_digest(x_calibracion_token, esperado):
        raise HTTPException(status_code=401, detail="Clave de calibración incorrecta")


def _salida(c: CalibracionFoto) -> CalibracionOut:
    return CalibracionOut(
        id=c.id,
        creada_en=c.creada_en,
        etiqueta=c.etiqueta,
        puntaje_humano=c.puntaje_humano,
        nota=c.nota,
        autor=c.autor,
        vision_version=c.vision_version,
        vision_puntaje=c.vision_puntaje,
        vision_metricas=c.vision_metricas,
        ia_modelo=c.ia_modelo,
        ia_puntaje=c.ia_puntaje,
        imagen_url=f"/api/v1/calibracion/{c.id}/imagen",
    )


@router.post("", response_model=CalibracionOut, status_code=201,
             dependencies=[Depends(verificar_token_calibracion)])
async def guardar(
    request: Request,
    etiqueta: Literal["saludable", "estresada", "marchita"] = Query(),
    puntaje_humano: int | None = Query(default=None, ge=0, le=100),
    nota: str | None = Query(default=None, max_length=500),
    autor: str | None = Query(default=None, max_length=64),
    con_ia: bool = Query(default=False, description="También correr la IA (gasta cuota)"),
    db: Session = Depends(get_db),
):
    datos, content_type = await leer_imagen(request)
    v = analizar_con_vision(datos)

    ia_modelo = ia_puntaje = None
    if con_ia:
        # Si la IA falla (cuota, saturación) la foto se guarda igual: la
        # etiqueta humana es lo valioso.
        try:
            ia = await analizar_con_ia(datos, content_type)
            ia_modelo, ia_puntaje = ia.modelo, ia.puntaje
        except HTTPException as e:
            log.warning("calibracion: IA no disponible al guardar (%s): %s", e.status_code, e.detail)

    ahora = datetime.now(UTC)
    key = f"calibracion/{ahora:%Y/%m/%d}/{uuid.uuid4().hex}.{EXTENSIONES[content_type]}"
    await run_in_threadpool(photo_storage.put, key, datos, content_type)

    c = CalibracionFoto(
        object_key=key,
        content_type=content_type,
        bytes=len(datos),
        sha256=hashlib.sha256(datos).hexdigest(),
        etiqueta=etiqueta,
        puntaje_humano=puntaje_humano,
        nota=nota or None,
        autor=autor or None,
        vision_version=vision.VERSION,
        vision_puntaje=v.puntaje,
        vision_metricas=v.metricas,
        ia_modelo=ia_modelo,
        ia_puntaje=ia_puntaje,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _salida(c)


@router.get("", response_model=list[CalibracionOut],
            dependencies=[Depends(verificar_token_calibracion)])
def listar(db: Session = Depends(get_db)):
    return [_salida(c) for c in db.query(CalibracionFoto).order_by(CalibracionFoto.id.desc()).all()]


@router.get("/evaluacion", response_model=EvaluacionOut,
            dependencies=[Depends(verificar_token_calibracion)])
def evaluar(db: Session = Depends(get_db)):
    filas: list[EvaluacionFila] = []
    matriz = {h: {p: 0 for p in CLASES} for h in CLASES}
    errores: list[int] = []
    for c in db.query(CalibracionFoto).order_by(CalibracionFoto.id).all():
        try:
            datos, _ = photo_storage.get(c.object_key)
            r = analizar_con_vision(datos.getvalue())
        except Exception as e:  # una foto ilegible no tiene que tirar la evaluación entera
            log.warning("calibracion: no se pudo re-evaluar %s: %s", c.id, e)
            continue
        if r.estado:
            matriz[c.etiqueta][r.estado] += 1
        if c.puntaje_humano is not None and r.puntaje is not None:
            errores.append(abs(c.puntaje_humano - r.puntaje))
        filas.append(EvaluacionFila(
            id=c.id, etiqueta=c.etiqueta, puntaje_humano=c.puntaje_humano,
            puntaje=r.puntaje, estado=r.estado, acierto=r.estado == c.etiqueta, metricas=r.metricas,
        ))
    aciertos = sum(f.acierto for f in filas)
    return EvaluacionOut(
        version=vision.VERSION,
        n=len(filas),
        aciertos=aciertos,
        exactitud=round(aciertos / len(filas), 3) if filas else None,
        error_medio=round(sum(errores) / len(errores), 1) if errores else None,
        matriz=matriz,
        filas=filas,
    )


@router.get("/{calibracion_id}/imagen", dependencies=[Depends(verificar_token_calibracion)])
def imagen(calibracion_id: int, db: Session = Depends(get_db)):
    c = db.get(CalibracionFoto, calibracion_id)
    if c is None:
        raise HTTPException(status_code=404, detail="No existe esa foto de calibración")
    datos, _ = photo_storage.get(c.object_key)
    return Response(content=datos.getvalue(), media_type=c.content_type,
                    headers={"Cache-Control": "private, max-age=3600"})


@router.delete("/{calibracion_id}", status_code=204,
               dependencies=[Depends(verificar_token_calibracion)])
def borrar(calibracion_id: int, db: Session = Depends(get_db)):
    c = db.get(CalibracionFoto, calibracion_id)
    if c is None:
        raise HTTPException(status_code=404, detail="No existe esa foto de calibración")
    photo_storage.delete(c.object_key)
    db.delete(c)
    db.commit()
    return Response(status_code=204)
