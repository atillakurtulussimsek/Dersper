"""Sonsuz mod ve deneme günlüğü.

Revision ID: 0019
Revises: 0018
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if "endless_mode" not in {c["name"] for c in insp.get_columns("timetables")}:
        op.add_column("timetables", sa.Column(
            "endless_mode", sa.Boolean(), nullable=False, server_default="0"))
    if "log" not in {c["name"] for c in insp.get_columns("solve_runs")}:
        op.add_column("solve_runs", sa.Column("log", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("solve_runs", "log")
    op.drop_column("timetables", "endless_mode")
