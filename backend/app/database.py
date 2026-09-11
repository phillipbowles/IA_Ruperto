import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Sin valor por defecto a propósito: una URL implícita a SQLite hacía que la
# app levantara contra una base vacía en vez de fallar cuando faltaba la
# variable, y el problema aparecía recién al no encontrar los datos.
DATABASE_URL = os.environ["DATABASE_URL"]
# Railway entrega "postgres://" (legacy) — SQLAlchemy requiere "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# El esquema lo crea y lo versiona Alembic (backend/alembic/), no create_all().
# Dos mecanismos creando tablas es la forma más rápida de que el esquema de
# local y el de producción se separen sin que nadie se entere.
