from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MedicionIn(BaseModel):
    dispositivo:          str
    numero_muestra:       int
    boot_id:              Optional[int]   = None
    temperatura_c:        Optional[float] = None
    humedad_ambiente_pct: Optional[float] = None
    luz_raw:              Optional[int]   = None
    luz_pct:              Optional[float] = None
    suelo_raw:            Optional[int]   = None
    suelo_pct:            Optional[float] = None
    termistor_raw:        Optional[int]   = None
    condicion_codigo:     Optional[int]   = None
    condicion_etiqueta:   Optional[str]   = None
    wifi_rssi:            Optional[int]   = None
    errores:              Optional[List[str]] = None


class MedicionOut(BaseModel):
    id:                   int
    dispositivo:          str
    numero_muestra:       int
    boot_id:              Optional[int]
    temperatura_c:        Optional[float]
    humedad_ambiente_pct: Optional[float]
    luz_raw:              Optional[int]
    luz_pct:              Optional[float]
    suelo_raw:            Optional[int]
    suelo_pct:            Optional[float]
    termistor_raw:        Optional[int]
    condicion_codigo:     Optional[int]
    condicion_etiqueta:   Optional[str]
    wifi_rssi:            Optional[int]
    errores:              Optional[List[str]]
    ts_servidor:          datetime

    model_config = {"from_attributes": True}


class MedicionResponse(BaseModel):
    duplicado:   bool
    id:          int
    ts_servidor: datetime
