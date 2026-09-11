"""Configuración de Alembic.

La URL de la base sale siempre del entorno (DATABASE_URL), nunca de alembic.ini:
así el mismo archivo funciona en el compose local y en Railway.
"""
from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import DATABASE_URL, Base
import app.models  # noqa: F401 — registra las tablas en Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# La URL normalizada por app.database (Railway entrega "postgres://" legacy).
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))

target_metadata = Base.metadata

# Identificador arbitrario pero FIJO del advisory lock de migraciones: todo
# proceso que migre esta base pide el mismo número, así solo uno migra a la vez.
ID_LOCK_MIGRACIONES = 8274531


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse — útil para revisar qué se va a aplicar."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # En producción esto puede correr dos veces casi en simultáneo: el
        # preDeployCommand de Railway y el entrypoint del contenedor nuevo,
        # mientras el contenedor viejo todavía sirve tráfico. El advisory lock
        # hace que el segundo espere en vez de intentar aplicar la misma
        # revisión. Es a nivel de sesión, así que sobrevive a los commits de
        # cada migración y se suelta al cerrar la conexión.
        usa_lock = connection.dialect.name == "postgresql"
        if usa_lock:
            connection.execute(
                sa.text("SELECT pg_advisory_lock(:id)"), {"id": ID_LOCK_MIGRACIONES}
            )
            connection.commit()   # cierra la transacción implícita; el lock queda

        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            if usa_lock:
                connection.execute(
                    sa.text("SELECT pg_advisory_unlock(:id)"), {"id": ID_LOCK_MIGRACIONES}
                )
                connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
