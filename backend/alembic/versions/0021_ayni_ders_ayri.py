"""Aynı ders farklı öğretmenlerde de arka arkaya gelmesin (dönem ayarı).

Revision ID: 0021
Revises: 0020
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if "same_subject_apart" not in {c["name"] for c in insp.get_columns("terms")}:
        op.add_column("terms", sa.Column(
            "same_subject_apart", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("terms", "same_subject_apart")
