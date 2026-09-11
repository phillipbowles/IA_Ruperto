"""Esquema inicial — tabla mediciones tal como la creó create_all()

Esta revisión reproduce exactamente el esquema que ya existe en la base de
Railway, creado por Base.metadata.create_all() antes de que hubiera migraciones.

Para una base nueva (el compose local) se aplica normalmente.
Para la base de Railway, que YA tiene esta tabla, hay que marcarla como aplicada
una sola vez sin ejecutarla:

    alembic stamp 0001

y recién después correr `alembic upgrade head`. Si no, 0001 falla al intentar
crear una tabla que ya existe.

Revision ID: 0001
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mediciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dispositivo", sa.String(length=50), nullable=False),
        sa.Column("numero_muestra", sa.Integer(), nullable=False),
        sa.Column("boot_id", sa.Integer(), nullable=True),
        sa.Column("temperatura_c", sa.Float(), nullable=True),
        sa.Column("humedad_ambiente_pct", sa.Float(), nullable=True),
        sa.Column("luz_raw", sa.Integer(), nullable=True),
        sa.Column("luz_pct", sa.Float(), nullable=True),
        sa.Column("suelo_raw", sa.Integer(), nullable=True),
        sa.Column("suelo_pct", sa.Float(), nullable=True),
        sa.Column("termistor_raw", sa.Integer(), nullable=True),
        sa.Column("condicion_codigo", sa.Integer(), nullable=True),
        sa.Column("condicion_etiqueta", sa.String(length=30), nullable=True),
        sa.Column("wifi_rssi", sa.Integer(), nullable=True),
        sa.Column("errores", sa.JSON(), nullable=True),
        sa.Column(
            "ts_servidor",
            sa.DateTime(timezone=True),
            # func.now() y no text("now()"): SQLAlchemy lo compila según el
            # dialecto (now() en Postgres, CURRENT_TIMESTAMP en SQLite), así los
            # tests pueden correr sin levantar una base de verdad.
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        # Idempotencia de la ingesta: un reintento de la placa no duplica la fila.
        sa.UniqueConstraint("dispositivo", "numero_muestra", name="uq_dispositivo_muestra"),
    )
    op.create_index("ix_mediciones_id", "mediciones", ["id"])
    op.create_index("ix_mediciones_dispositivo", "mediciones", ["dispositivo"])


def downgrade() -> None:
    op.drop_index("ix_mediciones_dispositivo", table_name="mediciones")
    op.drop_index("ix_mediciones_id", table_name="mediciones")
    op.drop_table("mediciones")
