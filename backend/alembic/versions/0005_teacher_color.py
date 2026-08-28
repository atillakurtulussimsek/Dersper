"""Öğretmenlere renk alanı.

Öğretmenler de derslerdeki gibi bir renkle işaretlenir; listelerde ve
seçim ekranlarında ayırt etmeyi kolaylaştırır.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

VARSAYILAN = "#94a3b8"


def upgrade() -> None:
    sutunlar = {c["name"] for c in inspect(op.get_bind()).get_columns("teachers")}
    if "color" not in sutunlar:
        op.add_column(
            "teachers",
            sa.Column("color", sa.String(7), nullable=False, server_default=VARSAYILAN),
        )


def downgrade() -> None:
    op.drop_column("teachers", "color")
