"""Programa dahil şubeler.

Bazı dönemlerde yalnızca belirli şubeler için program yapılır. Seçim programın
kendisinde tutulur; NULL, dönemin tüm şubeleri demektir (eski kayıtlar böyle
kalır).

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    mevcut = {c["name"] for c in inspect(op.get_bind()).get_columns("timetables")}
    if "section_ids" not in mevcut:
        op.add_column("timetables", sa.Column("section_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("timetables", "section_ids")
