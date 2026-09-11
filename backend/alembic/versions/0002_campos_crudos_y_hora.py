"""Hora del dispositivo, canales crudos completos y origen de etiqueta

Qué agrega y por qué:

- ts_dispositivo: la hora NTP de la placa (UTC). Sin esto el único tiempo era
  ts_servidor, que incluye el retardo de red y de los reintentos, y no permite
  cruzar la serie con el timelapse del celular.
- luz_mv / suelo_mv / termistor_mv: el convertido a milivolts de cada canal.
  CLAUDE.md pide guardar siempre el crudo ADEMÁS del convertido.
- temp_ntc_c: el firmware calculaba la temperatura del termistor y la tiraba;
  solo viajaba el raw.
- etiqueta_origen: distingue la muestra donde hubo observación humana (manual)
  de las que heredan la etiqueta hasta la próxima pulsación (propagada).
- firmware_version: permite separar en el análisis los datos tomados antes y
  después de un cambio de calibración o de lógica.

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mediciones", sa.Column("firmware_version", sa.String(length=20), nullable=True))
    op.add_column("mediciones", sa.Column("ts_dispositivo", sa.DateTime(timezone=True), nullable=True))
    op.add_column("mediciones", sa.Column("luz_mv", sa.Float(), nullable=True))
    op.add_column("mediciones", sa.Column("suelo_mv", sa.Float(), nullable=True))
    op.add_column("mediciones", sa.Column("termistor_mv", sa.Float(), nullable=True))
    op.add_column("mediciones", sa.Column("temp_ntc_c", sa.Float(), nullable=True))
    op.add_column("mediciones", sa.Column("etiqueta_origen", sa.String(length=20), nullable=True))

    # El análisis ordena y filtra por la hora de la placa, no por la del servidor.
    op.create_index("ix_mediciones_ts_dispositivo", "mediciones", ["ts_dispositivo"])

    # Las filas anteriores a esta migración no tienen origen de etiqueta. Se marcan
    # explícitamente para poder excluirlas del entrenamiento sin tener que adivinar.
    op.execute(
        "UPDATE mediciones SET etiqueta_origen = 'desconocido' WHERE etiqueta_origen IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_mediciones_ts_dispositivo", table_name="mediciones")
    for col in (
        "etiqueta_origen", "temp_ntc_c", "termistor_mv",
        "suelo_mv", "luz_mv", "ts_dispositivo", "firmware_version",
    ):
        op.drop_column("mediciones", col)
