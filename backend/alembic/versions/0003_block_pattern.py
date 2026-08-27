"""Sabit blok boyu yerine serbest blok deseni.

`block_size` (tek sayı) kaldırılır; yerine "2+2+1" gibi bir desen tutan
`block_pattern` gelir. Mevcut satırlar eski davranışa denk desenle doldurulur.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLO = "curriculum_entries"


def _desene_cevir(haftalik: int, boy: int) -> str:
    """Eski davranış: haftalık saati `boy` uzunluğunda bloklara böl, kalanı sona ekle."""
    boy = max(1, min(boy or 1, haftalik))
    tam, kalan = divmod(haftalik, boy)
    parcalar = [boy] * tam + ([kalan] if kalan else [])
    return "+".join(str(p) for p in parcalar)


def upgrade() -> None:
    op.add_column(
        TABLO,
        sa.Column("block_pattern", sa.String(60), nullable=False, server_default=""),
    )
    baglanti = op.get_bind()
    satirlar = baglanti.execute(
        sa.text(f"SELECT id, weekly_hours, block_size FROM {TABLO}")
    ).fetchall()
    for satir_id, haftalik, boy in satirlar:
        baglanti.execute(
            sa.text(f"UPDATE {TABLO} SET block_pattern = :d WHERE id = :i"),
            {"d": _desene_cevir(haftalik, boy), "i": satir_id},
        )
    op.drop_column(TABLO, "block_size")


def downgrade() -> None:
    op.add_column(
        TABLO, sa.Column("block_size", sa.Integer(), nullable=False, server_default="1")
    )
    baglanti = op.get_bind()
    satirlar = baglanti.execute(
        sa.text(f"SELECT id, block_pattern FROM {TABLO}")
    ).fetchall()
    for satir_id, desen in satirlar:
        parcalar = [int(p) for p in (desen or "").split("+") if p.strip().isdigit()]
        baglanti.execute(
            sa.text(f"UPDATE {TABLO} SET block_size = :b WHERE id = :i"),
            {"b": max(parcalar) if parcalar else 1, "i": satir_id},
        )
    op.drop_column(TABLO, "block_pattern")
