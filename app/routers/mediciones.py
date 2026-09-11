import os
import csv
import io
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..models import Medicion
from ..schemas import MedicionIn, MedicionOut, MedicionResponse

router = APIRouter(prefix="/api/v1", tags=["mediciones"])


def verificar_token(x_device_token: Optional[str] = Header(None)):
    token = os.getenv("DEVICE_TOKEN", "")
    if not token or x_device_token != token:
        raise HTTPException(status_code=401, detail="Token inválido o ausente")


@router.post("/mediciones", response_model=MedicionResponse, status_code=201)
def crear_medicion(
    data: MedicionIn,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(verificar_token),
):
    existing = db.query(Medicion).filter(
        and_(
            Medicion.dispositivo    == data.dispositivo,
            Medicion.numero_muestra == data.numero_muestra,
        )
    ).first()

    if existing:
        response.status_code = 200
        return MedicionResponse(
            duplicado=True, id=existing.id, ts_servidor=existing.ts_servidor
        )

    m = Medicion(**data.model_dump())
    db.add(m)
    try:
        db.commit()
        db.refresh(m)
    except IntegrityError:
        db.rollback()
        existing = db.query(Medicion).filter(
            and_(
                Medicion.dispositivo    == data.dispositivo,
                Medicion.numero_muestra == data.numero_muestra,
            )
        ).first()
        response.status_code = 200
        return MedicionResponse(
            duplicado=True, id=existing.id, ts_servidor=existing.ts_servidor
        )

    response.status_code = 201
    return MedicionResponse(duplicado=False, id=m.id, ts_servidor=m.ts_servidor)


@router.get("/mediciones/ultima", response_model=MedicionOut)
def ultima_medicion(db: Session = Depends(get_db)):
    m = db.query(Medicion).order_by(Medicion.id.desc()).first()
    if not m:
        raise HTTPException(status_code=404, detail="No hay mediciones")
    return m


@router.get("/mediciones", response_model=List[MedicionOut])
def listar_mediciones(db: Session = Depends(get_db), limit: int = 100):
    return db.query(Medicion).order_by(Medicion.id.desc()).limit(limit).all()


@router.get("/mediciones.csv")
def descargar_csv(db: Session = Depends(get_db)):
    mediciones = db.query(Medicion).order_by(Medicion.id).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "dispositivo", "numero_muestra", "boot_id",
        "temperatura_c", "humedad_ambiente_pct",
        "luz_raw", "luz_pct", "suelo_raw", "suelo_pct",
        "termistor_raw", "condicion_codigo", "condicion_etiqueta",
        "wifi_rssi", "errores", "ts_servidor",
    ])
    for m in mediciones:
        writer.writerow([
            m.id, m.dispositivo, m.numero_muestra, m.boot_id,
            m.temperatura_c, m.humedad_ambiente_pct,
            m.luz_raw, m.luz_pct, m.suelo_raw, m.suelo_pct,
            m.termistor_raw, m.condicion_codigo, m.condicion_etiqueta,
            m.wifi_rssi, m.errores, m.ts_servidor,
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mediciones.csv"},
    )
