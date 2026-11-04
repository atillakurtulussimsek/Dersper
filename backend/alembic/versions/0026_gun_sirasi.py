"""Günlerin gösterim sırası.

Revision ID: 0026
Revises: 0025
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "sira" not in {c["name"] for c in inspect(op.get_bind()).get_columns("days")}:
        op.add_column("days", sa.Column("sira", sa.Integer(), nullable=False,
                                        server_default="0"))
        # Var olan ızgaralar bugünkü sırasını korur: Pazartesi'den Pazar'a.
        op.execute("UPDATE days SET sira = `index`" if op.get_bind().dialect.name == "mysql"
                   else 'UPDATE days SET sira = "index"')


def downgrade() -> None:
    op.drop_column("days", "sira")
