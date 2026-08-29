"""Çok kurumluluk.

Kullanıcılar, dönemler ve yapay zeka ayarları bir kuruma bağlanır. Var olan
kurulumda tek kurum vardır; mevcut kullanıcılar, dönemler ve ayarlar ona
aktarılır, böylece çalışan kurulumlarda veri kaybı olmaz.

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

TABLOLAR = ("users", "terms", "ai_settings")


def _sqlite(baglanti) -> bool:
    """SQLite yabancı anahtar ekleyemez; oradaki şema testlerde model
    tanımlarından kurulur, bu adımlar atlanabilir."""
    return baglanti.dialect.name == "sqlite"


def upgrade() -> None:
    baglanti = op.get_bind()
    sqlite = _sqlite(baglanti)

    kurum_id = baglanti.execute(
        sa.text("SELECT id FROM institutions ORDER BY id LIMIT 1")
    ).scalar()

    for tablo in TABLOLAR:
        op.add_column(tablo, sa.Column("institution_id", sa.Integer(), nullable=True))
        if kurum_id is not None:
            baglanti.execute(
                sa.text(f"UPDATE {tablo} SET institution_id = :k"), {"k": kurum_id}
            )

    # Kurumu olmayan artık kayıt kalmasın (kurum silinmişse öksüz satır olabilir).
    for tablo in TABLOLAR:
        baglanti.execute(sa.text(f"DELETE FROM {tablo} WHERE institution_id IS NULL"))

    if sqlite:
        return

    for tablo in TABLOLAR:
        op.alter_column(tablo, "institution_id", existing_type=sa.Integer(),
                        nullable=False)
        op.create_foreign_key(
            f"fk_{tablo}_institution", tablo, "institutions",
            ["institution_id"], ["id"], ondelete="CASCADE",
        )
    # Kurum başına tek yapay zeka ayarı.
    op.create_unique_constraint(
        "uq_ai_settings_institution", "ai_settings", ["institution_id"]
    )


def downgrade() -> None:
    sqlite = _sqlite(op.get_bind())
    # MySQL benzersiz kısıtı yabancı anahtarın indeksi olarak kullanıyor;
    # önce yabancı anahtarlar, sonra kısıt düşürülmeli.
    if not sqlite:
        for tablo in TABLOLAR:
            op.drop_constraint(f"fk_{tablo}_institution", tablo, type_="foreignkey")
        op.drop_constraint("uq_ai_settings_institution", "ai_settings", type_="unique")
    for tablo in TABLOLAR:
        op.drop_column(tablo, "institution_id")
