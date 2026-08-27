"""Başlangıç şeması.

Taban şema doğrudan model tanımlarından üretilir. Sonraki değişiklikler için
`alembic revision --autogenerate` normal şekilde kullanılır.

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


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
