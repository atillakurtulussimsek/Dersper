"""Öğretmen boşluğu politikası.

Okullar programın "havasını" seçebilmeli: kimi öğretmenin günü sıkışık olsun
ister, kimi dersler arasında boşluk kalmasını yeğler. Üç seçenek programın
kendisinde tutulur — aynı dönemde iki taslak farklı politikayla üretilip
karşılaştırılabilsin diye.

Varsayılan `ideal`: boşluğa hiç bakılmaz, yani mevcut davranış korunur.

Revision ID: 0015
Revises: 0014
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

POLITIKA = sa.Enum("BOSLUKLU", "IDEAL", "SIKI", name="gappolicy")


def upgrade() -> None:
    baglanti = op.get_bind()
    mevcut = {c["name"] for c in inspect(baglanti).get_columns("timetables")}
    if "gap_policy" not in mevcut:
        POLITIKA.create(baglanti, checkfirst=True)
        op.add_column("timetables", sa.Column(
            "gap_policy", POLITIKA, nullable=False, server_default="IDEAL",
        ))


def downgrade() -> None:
    op.drop_column("timetables", "gap_policy")
    POLITIKA.drop(op.get_bind(), checkfirst=True)
