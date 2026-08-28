"""Programa özel gizlenen uyarılar.

Günlük ders tekrar sınırı gerektiğinde esnetilebiliyor; oluşan uyarıları
kullanıcı isterse düzeltir, isterse "görmezden gel" der. Gizlenen uyarı
anahtarları programın kendisinde tutulur.

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    mevcut = {c["name"] for c in inspect(op.get_bind()).get_columns("timetables")}
    if "ignored_warnings" not in mevcut:
        op.add_column("timetables", sa.Column("ignored_warnings", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("timetables", "ignored_warnings")
