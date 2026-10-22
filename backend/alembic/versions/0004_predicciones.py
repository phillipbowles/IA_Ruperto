"""Predicciones del modelo de la placa, separadas de la etiqueta humana

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "predicciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("medicion_id", sa.Integer(), nullable=False),
        sa.Column("modelo_version", sa.String(length=40), nullable=False),
        sa.Column("clase", sa.String(length=30), nullable=False),
        sa.Column("proba", sa.Float(), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["medicion_id"], ["mediciones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("medicion_id", "modelo_version", name="uq_prediccion_medicion_modelo"),
    )
    op.create_index("ix_predicciones_medicion_id", "predicciones", ["medicion_id"])


def downgrade() -> None:
    op.drop_index("ix_predicciones_medicion_id", table_name="predicciones")
    op.drop_table("predicciones")
