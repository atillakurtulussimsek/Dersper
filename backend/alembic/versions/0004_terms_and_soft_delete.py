"""Dönemler ve yumuşak silme.

Tüm tanımlar bir döneme bağlanır. Var olan kayıtlar için "Mevcut Dönem" adında
bir dönem açılır ve hepsi ona aktarılır; böylece çalışan kurulumlarda veri
kaybı olmaz.

Yumuşak silme için `deleted_at` eklenir. Ad/indeks eşsizliği artık uygulama
katmanında denetlendiğinden ilgili benzersiz kısıtlar kaldırılır.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

DONEME_BAGLI = ("days", "teachers", "subjects", "sections", "timetables")
YUMUSAK_SILME = (
    "terms", "teachers", "subjects", "sections", "curriculum_entries", "timetables",
)


def _sqlite(baglanti) -> bool:
    """SQLite kısıt ve yabancı anahtar değiştiremez; oradaki şema testlerde
    model tanımlarından kurulduğu için bu adımlar atlanabilir."""
    return baglanti.dialect.name == "sqlite"


def upgrade() -> None:
    op.create_table(
        "terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    for tablo in YUMUSAK_SILME:
        if tablo != "terms":
            op.add_column(tablo, sa.Column("deleted_at", sa.DateTime(), nullable=True))

    baglanti = op.get_bind()
    sqlite = _sqlite(baglanti)

    op.add_column("institutions", sa.Column("active_term_id", sa.Integer(), nullable=True))
    if not sqlite:
        op.create_foreign_key(
            "fk_institutions_active_term", "institutions", "terms",
            ["active_term_id"], ["id"], ondelete="SET NULL",
        )

        # Eşsizlik denetimi uygulamaya taşındı; yumuşak silmeyle bağdaşmıyor.
        _kisiti_dusur("sections", "uq_sections_name")
        _kisiti_dusur("days", "uq_days_index")
        # MySQL bu benzersiz anahtarı section_id yabancı anahtarının indeksi
        # olarak kullanıyor; önce yerine düz bir indeks koymak gerekiyor.
        op.create_index("ix_curriculum_section", "curriculum_entries", ["section_id"])
        _kisiti_dusur("curriculum_entries", "uq_curriculum_section_subject")

    veri_var = any(
        baglanti.execute(sa.text(f"SELECT 1 FROM {t} LIMIT 1")).first() is not None
        for t in DONEME_BAGLI
    )
    donem_id = None
    if veri_var or baglanti.execute(
        sa.text("SELECT 1 FROM institutions LIMIT 1")
    ).first() is not None:
        baglanti.execute(
            sa.text("INSERT INTO terms (name) VALUES ('Mevcut Dönem')")
        )
        donem_id = baglanti.execute(
            sa.text("SELECT id FROM terms ORDER BY id DESC LIMIT 1")
        ).scalar()

    for tablo in DONEME_BAGLI:
        op.add_column(tablo, sa.Column("term_id", sa.Integer(), nullable=True))
        if donem_id is not None:
            baglanti.execute(
                sa.text(f"UPDATE {tablo} SET term_id = :d"), {"d": donem_id}
            )

    if donem_id is not None:
        baglanti.execute(
            sa.text("UPDATE institutions SET active_term_id = :d"), {"d": donem_id}
        )

    if sqlite:
        return
    for tablo in DONEME_BAGLI:
        op.alter_column(tablo, "term_id", existing_type=sa.Integer(), nullable=False)
        op.create_foreign_key(
            f"fk_{tablo}_term", tablo, "terms", ["term_id"], ["id"], ondelete="CASCADE",
        )


def _kisiti_dusur(tablo: str, kisit: str) -> None:
    """Kısıt sürüme göre benzersiz kısıt ya da indeks olarak durabilir."""
    try:
        op.drop_constraint(kisit, tablo, type_="unique")
        return
    except Exception:
        pass
    op.drop_index(kisit, table_name=tablo)


def downgrade() -> None:
    sqlite = _sqlite(op.get_bind())
    for tablo in DONEME_BAGLI:
        if not sqlite:
            op.drop_constraint(f"fk_{tablo}_term", tablo, type_="foreignkey")
        op.drop_column(tablo, "term_id")
    if not sqlite:
        op.drop_constraint("fk_institutions_active_term", "institutions",
                           type_="foreignkey")
    op.drop_column("institutions", "active_term_id")
    for tablo in YUMUSAK_SILME:
        if tablo != "terms":
            op.drop_column(tablo, "deleted_at")
    op.drop_table("terms")
    if sqlite:
        return
    op.create_unique_constraint("uq_sections_name", "sections", ["name"])
    op.create_unique_constraint("uq_days_index", "days", ["index"])
    op.create_unique_constraint(
        "uq_curriculum_section_subject", "curriculum_entries", ["section_id", "subject_id"]
    )
    op.drop_index("ix_curriculum_section", table_name="curriculum_entries")
