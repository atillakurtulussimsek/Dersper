"""Ders grupları: benzer dersler bir şubede arka arkaya gelmesin.

Revision ID: 0022
Revises: 0021
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tablolar = inspect(op.get_bind()).get_table_names()
    if "subject_groups" not in tablolar:
        op.create_table(
            "subject_groups",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("term_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["term_id"], ["terms.id"], ondelete="CASCADE"),
        )
    if "subject_group_members" not in tablolar:
        op.create_table(
            "subject_group_members",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("group_id", sa.Integer(), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["group_id"], ["subject_groups.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("subject_id", name="uq_subject_group_member"),
        )


def downgrade() -> None:
    op.drop_table("subject_group_members")
    op.drop_table("subject_groups")
