"""Dönem ayarı: zorunlu kalınca bloklu derslerin otomatik bölünmesi.

Revision ID: 0028
Revises: 0027
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sutunlar = {c["name"] for c in inspect(op.get_bind()).get_columns("terms")}
    if "auto_split" not in sutunlar:
        op.add_column("terms", sa.Column(
            "auto_split", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("terms", "auto_split")
