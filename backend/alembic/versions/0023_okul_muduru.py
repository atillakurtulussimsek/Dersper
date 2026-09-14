"""Kurum ayarlarına okul müdürü adı (tebligat imzası).

Revision ID: 0023
Revises: 0022
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if "principal_name" not in {c["name"] for c in insp.get_columns("institutions")}:
        op.add_column("institutions", sa.Column("principal_name", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("institutions", "principal_name")
