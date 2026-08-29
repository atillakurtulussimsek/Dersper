"""Öğle arası ve öğretmen gün sınırı.

Özel kurumlarda öğretmenle "haftada 4,5 gün" gibi bir anlaşma yapılabiliyor.
Sabit bir günü kapatmak programı gereksiz kısıtladığı için sınır gün sayısı
olarak tutulur ve hangi günlerin kullanılacağına çözücü karar verir.

Kesirli gün yalnızca yarım olabildiğinden sınır YARIM GÜN biriminde saklanır
(9 = 4,5 gün): tam sayı, kayıpsız ve karşılaştırması kesin.

Yarım günün nerede bittiğini belirlemek için ızgaraya öğle arası eklenir —
teneffüsün, günü ikiye bölen özel hâli.

Revision ID: 0011
Revises: 0010
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    denetci = inspect(op.get_bind())

    saat_sutunlari = {c["name"] for c in denetci.get_columns("periods")}
    if "is_lunch" not in saat_sutunlari:
        op.add_column("periods", sa.Column(
            "is_lunch", sa.Boolean(), nullable=False, server_default=sa.false()
        ))

    ogretmen_sutunlari = {c["name"] for c in denetci.get_columns("teachers")}
    if "max_half_days" not in ogretmen_sutunlari:
        op.add_column("teachers", sa.Column("max_half_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("teachers", "max_half_days")
    op.drop_column("periods", "is_lunch")
