"""Metadatos de fotos capturadas por la ESP32-CAM

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fotos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dispositivo", sa.String(length=64), nullable=False),
        sa.Column("numero_foto", sa.BigInteger(), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("wifi_rssi", sa.Integer(), nullable=True),
        sa.Column(
            "recibido_en",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dispositivo", "numero_foto", name="uq_dispositivo_foto"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_fotos_id", "fotos", ["id"])
    op.create_index("ix_fotos_dispositivo", "fotos", ["dispositivo"])
    op.create_index("ix_fotos_sha256", "fotos", ["sha256"])
    op.create_index("ix_fotos_recibido_en", "fotos", ["recibido_en"])


def downgrade() -> None:
    op.drop_index("ix_fotos_recibido_en", table_name="fotos")
    op.drop_index("ix_fotos_sha256", table_name="fotos")
    op.drop_index("ix_fotos_dispositivo", table_name="fotos")
    op.drop_index("ix_fotos_id", table_name="fotos")
    op.drop_table("fotos")
