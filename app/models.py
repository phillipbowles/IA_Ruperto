from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base


class Medicion(Base):
    __tablename__ = "mediciones"

    id                   = Column(Integer, primary_key=True, index=True)
    dispositivo          = Column(String(50), nullable=False, index=True)
    numero_muestra       = Column(Integer, nullable=False)
    boot_id              = Column(Integer, nullable=True)
    temperatura_c        = Column(Float, nullable=True)
    humedad_ambiente_pct = Column(Float, nullable=True)
    luz_raw              = Column(Integer, nullable=True)
    luz_pct              = Column(Float, nullable=True)
    suelo_raw            = Column(Integer, nullable=True)
    suelo_pct            = Column(Float, nullable=True)
    termistor_raw        = Column(Integer, nullable=True)
    condicion_codigo     = Column(Integer, nullable=True)
    condicion_etiqueta   = Column(String(30), nullable=True)
    wifi_rssi            = Column(Integer, nullable=True)
    errores              = Column(JSON, nullable=True)
    ts_servidor          = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("dispositivo", "numero_muestra", name="uq_dispositivo_muestra"),
    )
