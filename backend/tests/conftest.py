"""Fixtures de los tests del bot: sin red ni Postgres.

La base es SQLite en memoria con las tablas creadas por `create_all` (sólo en
los tests: en la app el esquema es de Alembic). Gemini es un falso con la misma
interfaz que `app.bot.gemini.ClienteGemini`.
"""
from __future__ import annotations

import itertools
import os

# app.database exige DATABASE_URL al importarse; no se conecta hasta usarla.
os.environ.setdefault("DATABASE_URL", "sqlite://")

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.bot.dominio import Clasificacion
from app.bot.gemini import SinCupo
from app.database import Base
from app.models import Medicion, Prediccion

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
PASO = timedelta(minutes=5)
_numero = itertools.count(1)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()
    engine.dispose()


def cargar(db, suelos, t0=T0, paso=PASO, boot_id=1, dispositivo="maceta-01", pred=None, **extra):
    """Inserta una serie: un valor de `suelos` por muestra (None = faltante).
    `pred` = (clase, proba, version) para la última muestra."""
    filas = []
    for i, s in enumerate(suelos):
        m = Medicion(dispositivo=dispositivo, numero_muestra=next(_numero),
                     boot_id=boot_id, ts_dispositivo=t0 + i * paso, suelo_mv=s,
                     suelo_raw=None if s is None else int(s * 4095 / 3300),
                     luz_mv=extra.get("luz_mv", 800.0), temperatura_c=extra.get("temp", 22.0),
                     humedad_ambiente_pct=extra.get("hum", 55.0), firmware_version="2.0.0")
        filas.append(m)
    if pred:
        filas[-1].predicciones.append(Prediccion(clase=pred[0], proba=pred[1], modelo_version=pred[2]))
    db.add_all(filas)
    db.commit()
    return filas


class GeminiFalso:
    """Clasifica con una función y genera un texto fijo, anotando cada llamada."""

    modelo = "gemini-falso"

    def __init__(self, en_dominio=True, intencion="estado", respuesta="Soy Ruperto [1].",
                 error_generar=None, error_clasificar=None):
        self.en_dominio, self.intencion, self.respuesta = en_dominio, intencion, respuesta
        self.error_generar, self.error_clasificar = error_generar, error_clasificar
        self.prompts_clasificar: list[str] = []
        self.llamadas_generar: list[tuple[str, list[dict]]] = []

    async def clasificar(self, prompt, esquema):
        self.prompts_clasificar.append(prompt)
        if self.error_clasificar:
            raise self.error_clasificar
        return Clasificacion(en_dominio=self.en_dominio, intencion=self.intencion)

    async def generar(self, system, contenidos):
        self.llamadas_generar.append((system, contenidos))
        if self.error_generar:
            raise self.error_generar
        return self.respuesta


@pytest.fixture
def gemini():
    return GeminiFalso()


__all__ = ["PASO", "T0", "GeminiFalso", "SinCupo", "cargar"]
