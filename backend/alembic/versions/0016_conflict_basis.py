"""Dönemin çakışma ölçütü: ızgaranın satırı mı, gerçek saat aralığı mı?

Bir şube ya da öğretmen aynı anda iki yerde olamaz; "aynı an"ın ölçütünü kurum
seçer. Tek ve düzenli bir ızgarası olan okulda satır zaten saatin kendisidir;
saatleri üst üste binebilen ızgaralarda (vardiya, bölüme göre değişen ders
süresi) gerçek aralığa bakmak gerekir.

Varsayılan `DERS_SAATI`: mevcut dönemlerin programı değişmez.

Revision ID: 0016
Revises: 0015
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

OLCUT = sa.Enum("DERS_SAATI", "SAAT", name="conflictbasis")


def upgrade() -> None:
    baglanti = op.get_bind()
    mevcut = {c["name"] for c in inspect(baglanti).get_columns("terms")}
    if "conflict_basis" not in mevcut:
        OLCUT.create(baglanti, checkfirst=True)
        op.add_column("terms", sa.Column(
            "conflict_basis", OLCUT, nullable=False, server_default="DERS_SAATI",
        ))


def downgrade() -> None:
    op.drop_column("terms", "conflict_basis")
    OLCUT.drop(op.get_bind(), checkfirst=True)
