"""Şube sırası: dönem ayarı (ada göre / elle) ve şubede elle sıra numarası.

Revision ID: 0018
Revises: 0017
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

SIRA = sa.Enum("AD", "ELLE", name="sectionorder")


def upgrade() -> None:
    baglanti = op.get_bind()
    insp = inspect(baglanti)
    if "section_order" not in {c["name"] for c in insp.get_columns("terms")}:
        SIRA.create(baglanti, checkfirst=True)
        op.add_column("terms", sa.Column(
            "section_order", SIRA, nullable=False, server_default="AD",
        ))
    if "sort_order" not in {c["name"] for c in insp.get_columns("sections")}:
        op.add_column("sections", sa.Column("sort_order", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("sections", "sort_order")
    op.drop_column("terms", "section_order")
    SIRA.drop(op.get_bind(), checkfirst=True)
