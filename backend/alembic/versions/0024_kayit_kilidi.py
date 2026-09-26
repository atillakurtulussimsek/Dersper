"""Programda şube / öğretmen kilidi.

Revision ID: 0024
Revises: 0023
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    mevcut = {c["name"] for c in insp.get_columns("timetables")}
    if "locked_section_ids" not in mevcut:
        op.add_column("timetables", sa.Column("locked_section_ids", sa.JSON(), nullable=True))
    if "locked_teacher_ids" not in mevcut:
        op.add_column("timetables", sa.Column("locked_teacher_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("timetables", "locked_teacher_ids")
    op.drop_column("timetables", "locked_section_ids")
