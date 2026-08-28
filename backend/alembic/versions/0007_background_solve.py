"""Arka plan üretimi için çalıştırma sayaçları.

Program üretimi artık arka planda sürüyor ve tam yerleşim sağlanana kadar
deneme yapıyor; çalıştırma kaydı bu ilerlemeyi taşır.

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

# (ad, tür, sunucu varsayılanı, boş bırakılabilir mi)
YENI_SUTUNLAR = (
    ("updated_at", sa.DateTime(), None, True),
    ("attempts", sa.Integer(), "0", False),
    ("best_placed", sa.Integer(), "0", False),
    ("required", sa.Integer(), "0", False),
    ("proven_infeasible", sa.Boolean(), "0", False),
    ("stop_requested", sa.Boolean(), "0", False),
)


def upgrade() -> None:
    mevcut = {c["name"] for c in inspect(op.get_bind()).get_columns("solve_runs")}
    for ad, tur, varsayilan, bos_olabilir in YENI_SUTUNLAR:
        if ad in mevcut:
            continue
        op.add_column("solve_runs", sa.Column(
            ad, tur, nullable=bos_olabilir, server_default=varsayilan,
        ))
    # Durum listesine DURDURULDU eklendi.
    if op.get_bind().dialect.name != "sqlite":
        op.alter_column(
            "solve_runs", "status",
            existing_type=sa.Enum("BEKLIYOR", "CALISIYOR", "BASARILI", "COZUMSUZ",
                                  "HATA", name="solvestatus"),
            type_=sa.Enum("BEKLIYOR", "CALISIYOR", "BASARILI", "COZUMSUZ",
                          "DURDURULDU", "HATA", name="solvestatus"),
            existing_nullable=False,
        )


def downgrade() -> None:
    for ad, *_ in YENI_SUTUNLAR:
        op.drop_column("solve_runs", ad)
