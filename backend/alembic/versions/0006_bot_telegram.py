"""Chats suscriptos y log de conversaciones del bot Ruperto (docs/ENTREGA3.md §5.5)

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chats_telegram",
        sa.Column("chat_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("usuario", sa.String(length=64), nullable=True),
        sa.Column("suscripto", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ultimo_aviso_riego", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("chat_id"),
    )
    op.create_table(
        "conversaciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("pregunta", sa.Text(), nullable=False),
        sa.Column("en_dominio", sa.Boolean(), nullable=True),
        sa.Column("intencion", sa.String(length=20), nullable=True),
        sa.Column("fragmentos", sa.JSON(), nullable=True),
        sa.Column("respuesta", sa.Text(), nullable=False),
        sa.Column("modelo", sa.String(length=64), nullable=True),
        sa.Column("latencia_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversaciones_chat_id", "conversaciones", ["chat_id"])
    op.create_index("ix_conversaciones_ts", "conversaciones", ["ts"])


def downgrade() -> None:
    op.drop_index("ix_conversaciones_ts", table_name="conversaciones")
    op.drop_index("ix_conversaciones_chat_id", table_name="conversaciones")
    op.drop_table("conversaciones")
    op.drop_table("chats_telegram")
