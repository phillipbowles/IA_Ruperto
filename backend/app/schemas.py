from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MedicionIn(BaseModel):
    """Lo que manda la placa. Todo opcional salvo la identidad de la muestra:
    si un sensor falla el campo viaja en null, nunca en 0."""

    dispositivo:          str
    numero_muestra:       int
    boot_id:              Optional[int] = None
    firmware_version:     Optional[str] = None

    # Unix epoch UTC del reloj NTP de la placa. Null si todavía no sincronizó.
    ts_dispositivo_unix:  Optional[int] = None

    temperatura_c:        Optional[float] = None
    humedad_ambiente_pct: Optional[float] = None

    luz_raw:              Optional[int]   = None
    luz_mv:               Optional[float] = None
    luz_pct:              Optional[float] = None
    suelo_raw:            Optional[int]   = None
    suelo_mv:             Optional[float] = None
    suelo_pct:            Optional[float] = None
    termistor_raw:        Optional[int]   = None
    termistor_mv:         Optional[float] = None
    temp_ntc_c:           Optional[float] = None

    condicion_codigo:     Optional[int] = None
    condicion_etiqueta:   Optional[str] = None
    etiqueta_origen:      Optional[str] = Field(
        default=None, description="manual | propagada | corregida"
    )

    wifi_rssi:            Optional[int] = None
    errores:              Optional[List[str]] = None


class MedicionOut(BaseModel):
    id:                   int
    dispositivo:          str
    numero_muestra:       int
    boot_id:              Optional[int]
    firmware_version:     Optional[str]
    ts_dispositivo:       Optional[datetime]
    temperatura_c:        Optional[float]
    humedad_ambiente_pct: Optional[float]
    luz_raw:              Optional[int]
    luz_mv:               Optional[float]
    luz_pct:              Optional[float]
    suelo_raw:            Optional[int]
    suelo_mv:             Optional[float]
    suelo_pct:            Optional[float]
    termistor_raw:        Optional[int]
    termistor_mv:         Optional[float]
    temp_ntc_c:           Optional[float]
    condicion_codigo:     Optional[int]
    condicion_etiqueta:   Optional[str]
    etiqueta_origen:      Optional[str]
    wifi_rssi:            Optional[int]
    errores:              Optional[List[str]]
    ts_servidor:          datetime

    model_config = {"from_attributes": True}


class MedicionResponse(BaseModel):
    duplicado:   bool
    id:          int
    ts_servidor: datetime
    # Reservado para cuando el modelo esté entrenado: el mismo POST que ingesta
    # la muestra devuelve la predicción y la placa prende el semáforo con eso,
    # sin request extra ni features calculadas en la placa. Ver ARQUITECTURA.md.
    prediccion:  Optional[str]   = None
    proba:       Optional[float] = None
