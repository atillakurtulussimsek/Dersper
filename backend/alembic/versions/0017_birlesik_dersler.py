"""Birleşik dersler: bir müfredat satırı birden fazla şubeye ait olabilir.

Beden eğitimi, din kültürü ve seçmeliler sık sık birkaç şubeye birlikte
okutulur: tek öğretmen, tek saat, birkaç şube. Satırın asıl şubesi yerinde
kalır; ek şubeler bu tabloya yazılır.

Revision ID: 0017
Revises: 0016
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    baglanti = op.get_bind()
    if "curriculum_entry_sections" in inspect(baglanti).get_table_names():
        return
    op.create_table(
        "curriculum_entry_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["curriculum_entries.id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("entry_id", "section_id", name="uq_entry_section"),
    )


def downgrade() -> None:
    op.drop_table("curriculum_entry_sections")
