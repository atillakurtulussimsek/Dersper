"""Şube müsaitlik matrisi.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

DURUMLAR = ("UYGUN", "UYGUN_DEGIL", "TERCIH")


def upgrade() -> None:
    op.create_table(
        "section_availability",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.Enum(*DURUMLAR, name="availability"), nullable=False),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["period_id"], ["periods.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("section_id", "period_id", name="uq_section_availability"),
    )


def downgrade() -> None:
    op.drop_table("section_availability")
