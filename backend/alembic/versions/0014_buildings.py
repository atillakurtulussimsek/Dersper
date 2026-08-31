"""Binalar.

Bazı kurumlar birden fazla binada ders yapıyor; şube kendi dersliğiyle bir
binada duruyor, öğretmen ise binalar arasında geziyor. Binalar birbirinden
uzaksa gün içinde geçiş yapmak zor olduğundan dönem ayarıyla engellenebiliyor:
bir öğretmenin bir günkü dersleri tek binada toplanır.

Revision ID: 0014
Revises: 0013
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    baglanti = op.get_bind()
    denetci = inspect(baglanti)

    if "buildings" not in denetci.get_table_names():
        op.create_table(
            "buildings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("term_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("short_code", sa.String(length=20), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False,
                      server_default=sa.true()),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["term_id"], ["terms.id"], ondelete="CASCADE"),
        )

    sube_sutunlari = {c["name"] for c in denetci.get_columns("sections")}
    if "building_id" not in sube_sutunlari:
        op.add_column("sections", sa.Column("building_id", sa.Integer(), nullable=True))
        # SQLite ALTER ile yabancı anahtar eklemeyi desteklemez; orada
        # mantıksal bağ yeterli (uygulama katmanı zaten denetliyor).
        if baglanti.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_sections_building", "sections", "buildings",
                ["building_id"], ["id"], ondelete="SET NULL",
            )

    donem_sutunlari = {c["name"] for c in denetci.get_columns("terms")}
    if "block_building_switch" not in donem_sutunlari:
        op.add_column("terms", sa.Column(
            "block_building_switch", sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ))


def downgrade() -> None:
    baglanti = op.get_bind()
    op.drop_column("terms", "block_building_switch")
    if baglanti.dialect.name != "sqlite":
        op.drop_constraint("fk_sections_building", "sections", type_="foreignkey")
    op.drop_column("sections", "building_id")
    op.drop_table("buildings")
