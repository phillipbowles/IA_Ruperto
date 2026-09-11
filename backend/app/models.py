from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base


class Medicion(Base):
    """Hecho inmutable: lo que la placa midió en un instante.

    Nunca se edita ni se borra. Las anotaciones humanas (episodios de etiqueta,
    riegos, pesos, fotos) viven en tablas aparte porque tienen otro ciclo de
    vida — se corrigen a posteriori. Ver docs/ARQUITECTURA.md.
    """

    __tablename__ = "mediciones"

    id                   = Column(Integer, primary_key=True, index=True)
    dispositivo          = Column(String(50), nullable=False, index=True)
    numero_muestra       = Column(Integer, nullable=False)
    boot_id              = Column(Integer, nullable=True)
    firmware_version     = Column(String(20), nullable=True)

    # Hora de la placa (NTP, UTC). Es la que permite cruzar con el timelapse del
    # celular; ts_servidor incluye el retardo de red y de los reintentos.
    ts_dispositivo       = Column(DateTime(timezone=True), nullable=True, index=True)

    temperatura_c        = Column(Float, nullable=True)
    humedad_ambiente_pct = Column(Float, nullable=True)

    # Cada canal analógico guarda crudo + convertido (CLAUDE.md).
    luz_raw              = Column(Integer, nullable=True)
    luz_mv               = Column(Float, nullable=True)
    luz_pct              = Column(Float, nullable=True)
    suelo_raw            = Column(Integer, nullable=True)
    suelo_mv             = Column(Float, nullable=True)
    suelo_pct            = Column(Float, nullable=True)
    termistor_raw        = Column(Integer, nullable=True)
    termistor_mv         = Column(Float, nullable=True)
    temp_ntc_c           = Column(Float, nullable=True)

    # Etiqueta tal como la reportó la placa. `etiqueta_origen` distingue la
    # muestra donde hubo observación humana (manual) de las que heredaron la
    # etiqueta hasta la próxima pulsación (propagada).
    condicion_codigo     = Column(Integer, nullable=True)
    condicion_etiqueta   = Column(String(30), nullable=True)
    etiqueta_origen      = Column(String(20), nullable=True)

    wifi_rssi            = Column(Integer, nullable=True)
    errores              = Column(JSON, nullable=True)
    ts_servidor          = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("dispositivo", "numero_muestra", name="uq_dispositivo_muestra"),
    )
