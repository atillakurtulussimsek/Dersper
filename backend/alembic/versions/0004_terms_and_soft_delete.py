"""Dönemler ve yumuşak silme.

Tüm tanımlar bir döneme bağlanır. Var olan kayıtlar için "Mevcut Dönem" adında
bir dönem açılır ve hepsi ona aktarılır; böylece çalışan kurulumlarda veri
kaybı olmaz.

Yumuşak silme için `deleted_at` eklenir. Ad/indeks eşsizliği artık uygulama
katmanında denetlendiğinden ilgili benzersiz kısıtlar kaldırılır.

Bu revizyon **yeniden çalıştırılabilir** yazılmıştır: her adım önce yapılıp
yapılmadığına bakar. MySQL'de DDL geri alınamadığı için, yarıda kalan bir
yükseltme aynı komutla kaldığı yerden tamamlanabilir. Kısıtlar ada göre değil
sütunlarına göre bulunur; eski kurulumlarda adlar farklıdır.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

DONEME_BAGLI = ("days", "teachers", "subjects", "sections", "timetables")
YUMUSAK_SILME = (
    "terms", "teachers", "subjects", "sections", "curriculum_entries", "timetables",
)
# (tablo, kısıtın kapsadığı sütunlar)
KALDIRILACAK_KISITLAR = (
    ("sections", ["name"]),
    ("days", ["index"]),
    ("curriculum_entries", ["section_id", "subject_id"]),
)


def _mufettis():
    return inspect(op.get_bind())


def _sutunlar(mufettis, tablo: str) -> set[str]:
    return {c["name"] for c in mufettis.get_columns(tablo)}


def _kisiti_dusur(mufettis, tablo: str, sutunlar: list[str]) -> None:
    """Verilen sütunları kapsayan benzersiz kısıtı adı ne olursa olsun düşürür."""
    for kisit in mufettis.get_unique_constraints(tablo):
        if list(kisit["column_names"]) == sutunlar:
            op.drop_constraint(kisit["name"], tablo, type_="unique")
            return
    for indeks in mufettis.get_indexes(tablo):
        if indeks.get("unique") and list(indeks["column_names"]) == sutunlar:
            op.drop_index(indeks["name"], table_name=tablo)
            return


def upgrade() -> None:
    baglanti = op.get_bind()
    sqlite = baglanti.dialect.name == "sqlite"
    m = _mufettis()

    if "terms" not in m.get_table_names():
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
        m = _mufettis()

    for tablo in YUMUSAK_SILME:
        if "deleted_at" not in _sutunlar(m, tablo):
            op.add_column(tablo, sa.Column("deleted_at", sa.DateTime(), nullable=True))

    m = _mufettis()
    if "active_term_id" not in _sutunlar(m, "institutions"):
        op.add_column(
            "institutions", sa.Column("active_term_id", sa.Integer(), nullable=True)
        )
        if not sqlite:
            op.create_foreign_key(
                "fk_institutions_active_term", "institutions", "terms",
                ["active_term_id"], ["id"], ondelete="SET NULL",
            )

    if not sqlite:
        # Eşsizlik denetimi uygulamaya taşındı; yumuşak silmeyle bağdaşmıyor.
        m = _mufettis()
        # MySQL, şube–ders benzersiz anahtarını section_id yabancı anahtarının
        # indeksi olarak kullanır; önce yerine düz bir indeks konmalı.
        if "ix_curriculum_section" not in {
            i["name"] for i in m.get_indexes("curriculum_entries")
        }:
            op.create_index("ix_curriculum_section", "curriculum_entries", ["section_id"])
            m = _mufettis()
        for tablo, sutunlar in KALDIRILACAK_KISITLAR:
            _kisiti_dusur(m, tablo, sutunlar)

    # --- Var olan veriyi bir döneme bağla ---
    donem_id = baglanti.execute(
        sa.text("SELECT id FROM terms ORDER BY id LIMIT 1")
    ).scalar()
    if donem_id is None and baglanti.execute(
        sa.text("SELECT 1 FROM institutions LIMIT 1")
    ).first() is not None:
        baglanti.execute(sa.text("INSERT INTO terms (name) VALUES ('Mevcut Dönem')"))
        donem_id = baglanti.execute(
            sa.text("SELECT id FROM terms ORDER BY id DESC LIMIT 1")
        ).scalar()

    m = _mufettis()
    for tablo in DONEME_BAGLI:
        if "term_id" not in _sutunlar(m, tablo):
            op.add_column(tablo, sa.Column("term_id", sa.Integer(), nullable=True))
        if donem_id is not None:
            baglanti.execute(
                sa.text(f"UPDATE {tablo} SET term_id = :d WHERE term_id IS NULL"),
                {"d": donem_id},
            )

    if donem_id is not None:
        baglanti.execute(
            sa.text("UPDATE institutions SET active_term_id = :d "
                    "WHERE active_term_id IS NULL"),
            {"d": donem_id},
        )

    if sqlite:
        return

    m = _mufettis()
    for tablo in DONEME_BAGLI:
        op.alter_column(tablo, "term_id", existing_type=sa.Integer(), nullable=False)
        varolan = {fk["name"] for fk in m.get_foreign_keys(tablo)}
        if f"fk_{tablo}_term" not in varolan:
            op.create_foreign_key(
                f"fk_{tablo}_term", tablo, "terms", ["term_id"], ["id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    sqlite = op.get_bind().dialect.name == "sqlite"
    m = _mufettis()
    for tablo in DONEME_BAGLI:
        if not sqlite and f"fk_{tablo}_term" in {
            fk["name"] for fk in m.get_foreign_keys(tablo)
        }:
            op.drop_constraint(f"fk_{tablo}_term", tablo, type_="foreignkey")
        if "term_id" in _sutunlar(m, tablo):
            op.drop_column(tablo, "term_id")

    m = _mufettis()
    if not sqlite and "fk_institutions_active_term" in {
        fk["name"] for fk in m.get_foreign_keys("institutions")
    }:
        op.drop_constraint("fk_institutions_active_term", "institutions",
                           type_="foreignkey")
    if "active_term_id" in _sutunlar(m, "institutions"):
        op.drop_column("institutions", "active_term_id")

    m = _mufettis()
    for tablo in YUMUSAK_SILME:
        if tablo != "terms" and "deleted_at" in _sutunlar(m, tablo):
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
