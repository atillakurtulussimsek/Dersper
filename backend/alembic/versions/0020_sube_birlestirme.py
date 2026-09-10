"""Şube birleştirme kuralları ve ortak okutulan saatler.

Revision ID: 0020
Revises: 0019
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if "section_merge_rules" not in insp.get_table_names():
        op.create_table(
            "section_merge_rules",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("term_id", sa.Integer(), nullable=False),
            sa.Column("section_a_id", sa.Integer(), nullable=False),
            sa.Column("section_b_id", sa.Integer(), nullable=False),
            sa.Column("hours", sa.Integer(), nullable=False),
            sa.Column("day_indexes", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["term_id"], ["terms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["section_a_id"], ["sections.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["section_b_id"], ["sections.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("term_id", "section_a_id", "section_b_id",
                                name="uq_merge_rule_pair"),
        )
    if "merged_entry_id" not in {c["name"] for c in insp.get_columns("assignments")}:
        # Toplu kip: SQLite yabancı anahtarı ALTER ile ekleyemez, tabloyu
        # kopyalayarak kurar; MySQL'de doğrudan ALTER çalışır.
        with op.batch_alter_table("assignments") as toplu:
            toplu.add_column(sa.Column("merged_entry_id", sa.Integer(), nullable=True))
            toplu.create_foreign_key(
                "fk_assignment_merged_entry", "curriculum_entries",
                ["merged_entry_id"], ["id"], ondelete="SET NULL",
            )


def downgrade() -> None:
    with op.batch_alter_table("assignments") as toplu:
        toplu.drop_constraint("fk_assignment_merged_entry", type_="foreignkey")
        toplu.drop_column("merged_entry_id")
    op.drop_table("section_merge_rules")
