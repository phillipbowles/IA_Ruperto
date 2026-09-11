import os
import csv
import io
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from ..database import get_db
from ..models import Medicion
from ..schemas import MedicionIn, MedicionOut, MedicionResponse

router = APIRouter(prefix="/api/v1", tags=["mediciones"])

# Orden de columnas del CSV exportado. Mientras exista una sola tabla este es el
# volcado crudo; el dataset con etiquetas y eventos unidos sale de /dataset.csv
# una vez migrado el esquema (ver docs/ARQUITECTURA.md).
COLUMNAS_CSV = [
    "id", "dispositivo", "numero_muestra", "boot_id", "firmware_version",
    "ts_dispositivo", "ts_servidor",
    "temperatura_c", "humedad_ambiente_pct",
    "luz_raw", "luz_mv", "luz_pct",
    "suelo_raw", "suelo_mv", "suelo_pct",
    "termistor_raw", "termistor_mv", "temp_ntc_c",
    "condicion_codigo", "condicion_etiqueta", "etiqueta_origen",
    "wifi_rssi", "errores",
]


def verificar_token(x_device_token: Optional[str] = Header(None)):
    token = os.getenv("DEVICE_TOKEN", "")
    if not token or x_device_token != token:
        raise HTTPException(status_code=401, detail="Token inválido o ausente")


def _a_modelo(data: MedicionIn) -> Medicion:
    """Convierte el payload de la placa en fila. El unix epoch UTC se guarda
    como timestamp con zona; null si la placa todavía no sincronizó NTP."""
    campos = data.model_dump(exclude={"ts_dispositivo_unix"})
    ts = data.ts_dispositivo_unix
    campos["ts_dispositivo"] = (
        datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
    )
    return Medicion(**campos)


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

    m = _a_modelo(data)
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
    writer.writerow(COLUMNAS_CSV)
    for m in mediciones:
        fila = []
        for col in COLUMNAS_CSV:
            v = getattr(m, col)
            # La lista de errores va como texto separado por "|": el repr de
            # Python obligaría al notebook a hacer eval para leerla.
            if col == "errores":
                v = "|".join(v) if v else ""
            fila.append(v)
        writer.writerow(fila)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mediciones.csv"},
    )
