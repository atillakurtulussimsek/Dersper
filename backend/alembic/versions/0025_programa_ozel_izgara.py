"""Programa özel zaman ızgarası.

Revision ID: 0025
Revises: 0024
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    baglanti = op.get_bind()
    insp = inspect(baglanti)
    if "own_grid" not in {c["name"] for c in insp.get_columns("timetables")}:
        op.add_column("timetables", sa.Column(
            "own_grid", sa.Boolean(), nullable=False, server_default="0"))
    if "timetable_id" not in {c["name"] for c in insp.get_columns("days")}:
        op.add_column("days", sa.Column("timetable_id", sa.Integer(), nullable=True))
        # SQLite ALTER ile yabancı anahtar eklemeyi desteklemez (bkz. 0014).
        if baglanti.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_days_timetable", "days", "timetables", ["timetable_id"], ["id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    op.drop_constraint("fk_days_timetable", "days", type_="foreignkey")
    op.drop_column("days", "timetable_id")
    op.drop_column("timetables", "own_grid")
