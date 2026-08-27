"""Başlangıç şeması.

Tablolar model tanımlarından üretilir, ancak yalnızca aşağıda adı geçenler.
Liste sabittir: sonradan eklenen tablolar kendi revizyonlarında oluşturulur,
aksi halde bu revizyon ileride eklenen tabloları da yaratıp çakışma çıkarır.

Revision ID: 0001
Revises:
"""
from alembic import op

from app.db import Base
import app.models  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLOLAR = (
    "institutions", "users", "days", "periods", "teachers", "teacher_availability",
    "subjects", "sections", "curriculum_entries", "timetables", "assignments",
    "solve_runs", "ai_settings",
)


def _tablolar():
    return [Base.metadata.tables[ad] for ad in TABLOLAR]


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=_tablolar())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=_tablolar())
