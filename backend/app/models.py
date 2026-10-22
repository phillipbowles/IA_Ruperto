from sqlalchemy import (JSON, BigInteger, Column, DateTime, Float, ForeignKey, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Medicion(Base):
    """Hecho inmutable: lo que la placa midió en un instante.

    Nunca se edita ni se borra. Las anotaciones humanas (episodios de etiqueta,
    riegos, pesos, fotos) viven en tablas aparte porque tienen otro ciclo de
    vida — se corrigen a posteriori. Ver docs/ARQUITECTURA.md.
    """

    __tablename__ = "mediciones"

    id = Column(Integer, primary_key=True, index=True)
    dispositivo = Column(String(50), nullable=False, index=True)
    numero_muestra = Column(Integer, nullable=False)
    boot_id = Column(Integer, nullable=True)
    firmware_version = Column(String(20), nullable=True)

    # Hora de la placa (NTP, UTC). Es la que permite cruzar con el timelapse del
    # celular; ts_servidor incluye el retardo de red y de los reintentos.
    ts_dispositivo = Column(DateTime(timezone=True), nullable=True, index=True)

    temperatura_c = Column(Float, nullable=True)
    humedad_ambiente_pct = Column(Float, nullable=True)

    # Cada canal analógico guarda crudo + convertido (CLAUDE.md).
    luz_raw = Column(Integer, nullable=True)
    luz_mv = Column(Float, nullable=True)
    luz_pct = Column(Float, nullable=True)
    suelo_raw = Column(Integer, nullable=True)
    suelo_mv = Column(Float, nullable=True)
    suelo_pct = Column(Float, nullable=True)
    termistor_raw = Column(Integer, nullable=True)
    termistor_mv = Column(Float, nullable=True)
    temp_ntc_c = Column(Float, nullable=True)

    # Etiqueta tal como la reportó la placa. `etiqueta_origen` distingue la
    # muestra donde hubo observación humana (manual) de las que heredaron la
    # etiqueta hasta la próxima pulsación (propagada).
    condicion_codigo = Column(Integer, nullable=True)
    condicion_etiqueta = Column(String(30), nullable=True)
    etiqueta_origen = Column(String(20), nullable=True)

    wifi_rssi = Column(Integer, nullable=True)
    errores = Column(JSON, nullable=True)
    ts_servidor = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("dispositivo", "numero_muestra", name="uq_dispositivo_muestra"),
    )

    # selectin: una sola query extra con IN para toda la lista, en vez de una
    # por fila al serializar /mediciones.
    predicciones = relationship(
        "Prediccion", lazy="selectin", order_by="Prediccion.id", passive_deletes=True
    )

    # Lo que expone la API: la predicción más reciente de esta muestra. La placa
    # manda una sola por muestra; la tabla admite más (una por modelo_version).
    @property
    def _ultima_prediccion(self):
        return self.predicciones[-1] if self.predicciones else None

    @property
    def prediccion_etiqueta(self):
        p = self._ultima_prediccion
        return p.clase if p else None

    @property
    def prediccion_proba(self):
        p = self._ultima_prediccion
        return p.proba if p else None

    @property
    def modelo_version(self):
        p = self._ultima_prediccion
        return p.modelo_version if p else None


class Prediccion(Base):
    """Salida del modelo que corre en la placa (docs/ARQUITECTURA.md §3.4).

    **Nunca** en la misma columna que la etiqueta humana: si se mezclan, nadie
    puede decir después cuál dato fue observación y cuál el modelo
    prediciéndose a sí mismo.
    """

    __tablename__ = "predicciones"

    id = Column(Integer, primary_key=True)
    medicion_id = Column(
        Integer, ForeignKey("mediciones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    modelo_version = Column(String(40), nullable=False)
    clase = Column(String(30), nullable=False)
    proba = Column(Float, nullable=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("medicion_id", "modelo_version", name="uq_prediccion_medicion_modelo"),
    )


class Foto(Base):
    """Metadatos de una foto; el JPEG vive en un Bucket compatible con S3."""

    __tablename__ = "fotos"

    id = Column(Integer, primary_key=True, index=True)
    dispositivo = Column(String(64), nullable=False, index=True)
    numero_foto = Column(BigInteger, nullable=False)
    object_key = Column(String(512), nullable=False, unique=True)
    content_type = Column(String(64), nullable=False, default="image/jpeg")
    bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    wifi_rssi = Column(Integer, nullable=True)
    recibido_en = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (UniqueConstraint("dispositivo", "numero_foto", name="uq_dispositivo_foto"),)


class CalibracionFoto(Base):
    """Foto de la planta con lo que una persona observó, para medir y mejorar
    el análisis de fotos (docs/VISION_CLASICA.md §5).

    La etiqueta humana es la verdad de esta tabla; lo que dijeron la visión
    clásica y la IA al guardarla queda al lado para comparar, junto con la
    versión que lo calculó. La re-evaluación corre la versión actual sobre las
    fotos guardadas, sin pisar estos valores.
    """

    __tablename__ = "calibraciones_foto"

    id = Column(Integer, primary_key=True)
    creada_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    object_key = Column(String(512), nullable=False, unique=True)
    content_type = Column(String(64), nullable=False)
    bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)

    etiqueta = Column(String(30), nullable=False)          # saludable | estresada | marchita
    puntaje_humano = Column(Integer, nullable=True)        # 0-100, opcional
    nota = Column(String(500), nullable=True)
    autor = Column(String(64), nullable=True)

    vision_version = Column(String(40), nullable=True)
    vision_puntaje = Column(Integer, nullable=True)
    vision_metricas = Column(JSON, nullable=True)
    ia_modelo = Column(String(64), nullable=True)
    ia_puntaje = Column(Integer, nullable=True)
