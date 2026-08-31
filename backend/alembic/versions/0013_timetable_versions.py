"""Ders programı sürüm geçmişi.

Programda yapılan her değişiklik yeni bir sürüm yazar; sürümler eklenir, hiç
silinmez. Geri/ileri alma artık ayrı bir adım yığınında değil, bu geçmişin
üzerinde yürür — tek geçmiş olsun diye `edit_undo`/`edit_redo` kaldırıldı.

Mevcut programlara o anki hâlleri "Başlangıç" sürümü olarak yazılır, yoksa
sürümleme öncesinden kalan bir programda ilk düzenleme geri alınamazdı.

Revision ID: 0013
Revises: 0012
"""
import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

SURUM_TURU = sa.Enum("ILK", "URETIM", "ELLE", name="versionkind")


def upgrade() -> None:
    baglanti = op.get_bind()
    denetci = inspect(baglanti)

    if "timetable_versions" not in denetci.get_table_names():
        op.create_table(
            "timetable_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("timetable_id", sa.Integer(), nullable=False),
            sa.Column("number", sa.Integer(), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("kind", SURUM_TURU, nullable=False),
            sa.Column("label", sa.String(length=200), nullable=False),
            sa.Column("placements", sa.JSON(), nullable=False),
            sa.Column("placed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False,
                      server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["timetable_id"], ["timetables.id"],
                                    ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["parent_id"], ["timetable_versions.id"],
                                    ondelete="SET NULL"),
            sa.UniqueConstraint("timetable_id", "number", name="uq_version_number"),
        )

    sutunlar = {c["name"] for c in denetci.get_columns("timetables")}
    if "current_version_id" not in sutunlar:
        op.add_column("timetables",
                      sa.Column("current_version_id", sa.Integer(), nullable=True))
        # Döngüsel bağ (timetables ↔ timetable_versions): kısıt tablolar
        # kurulduktan sonra eklenir. SQLite ALTER ile kısıt eklemeyi
        # desteklemez; orada mantıksal bağ yeterli.
        if baglanti.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_timetables_current_version", "timetables", "timetable_versions",
                ["current_version_id"], ["id"], ondelete="SET NULL",
            )

    _baslangic_surumleri(baglanti)

    for sutun in ("edit_undo", "edit_redo"):
        if sutun in sutunlar:
            op.drop_column("timetables", sutun)


def _baslangic_surumleri(baglanti) -> None:
    """Her programa o anki yerleşimini "Başlangıç" sürümü olarak yazar."""
    programlar = baglanti.execute(sa.text("SELECT id FROM timetables")).fetchall()
    for (timetable_id,) in programlar:
        var_mi = baglanti.execute(
            sa.text("SELECT id FROM timetable_versions WHERE timetable_id = :t LIMIT 1"),
            {"t": timetable_id},
        ).first()
        if var_mi:
            continue

        satirlar = baglanti.execute(
            sa.text(
                "SELECT curriculum_entry_id, period_id, is_locked FROM assignments "
                "WHERE timetable_id = :t ORDER BY period_id, curriculum_entry_id"
            ),
            {"t": timetable_id},
        ).fetchall()
        yerlesimler = [[e, p, bool(k)] for e, p, k in satirlar]

        baglanti.execute(
            sa.text(
                "INSERT INTO timetable_versions "
                "(timetable_id, number, parent_id, kind, label, placements, placed) "
                "VALUES (:t, 1, NULL, 'ILK', :l, :y, :n)"
            ),
            {"t": timetable_id, "l": "Başlangıç",
             "y": json.dumps(yerlesimler), "n": len(yerlesimler)},
        )
        yeni = baglanti.execute(
            sa.text("SELECT id FROM timetable_versions "
                    "WHERE timetable_id = :t AND number = 1"),
            {"t": timetable_id},
        ).scalar()
        baglanti.execute(
            sa.text("UPDATE timetables SET current_version_id = :v WHERE id = :t"),
            {"v": yeni, "t": timetable_id},
        )


def downgrade() -> None:
    baglanti = op.get_bind()
    for sutun in ("edit_undo", "edit_redo"):
        op.add_column("timetables", sa.Column(sutun, sa.JSON(), nullable=True))
    if baglanti.dialect.name != "sqlite":
        op.drop_constraint("fk_timetables_current_version", "timetables",
                           type_="foreignkey")
    op.drop_column("timetables", "current_version_id")
    op.drop_table("timetable_versions")
    SURUM_TURU.drop(baglanti, checkfirst=True)
