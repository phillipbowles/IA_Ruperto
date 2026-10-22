"""Fotos de calibración del análisis de fotos, con la etiqueta humana

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "calibraciones_foto",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("etiqueta", sa.String(length=30), nullable=False),
        sa.Column("puntaje_humano", sa.Integer(), nullable=True),
        sa.Column("nota", sa.String(length=500), nullable=True),
        sa.Column("autor", sa.String(length=64), nullable=True),
        sa.Column("vision_version", sa.String(length=40), nullable=True),
        sa.Column("vision_puntaje", sa.Integer(), nullable=True),
        sa.Column("vision_metricas", sa.JSON(), nullable=True),
        sa.Column("ia_modelo", sa.String(length=64), nullable=True),
        sa.Column("ia_puntaje", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_calibraciones_foto_sha256", "calibraciones_foto", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_calibraciones_foto_sha256", table_name="calibraciones_foto")
    op.drop_table("calibraciones_foto")
