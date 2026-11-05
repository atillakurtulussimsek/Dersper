"""Zorunlu kalınca bloğun bölünebilmesi.

Revision ID: 0027
Revises: 0026
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sutunlar = {c["name"] for c in inspect(op.get_bind()).get_columns("curriculum_entries")}
    if "allow_split" not in sutunlar:
        op.add_column("curriculum_entries", sa.Column(
            "allow_split", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("curriculum_entries", "allow_split")
