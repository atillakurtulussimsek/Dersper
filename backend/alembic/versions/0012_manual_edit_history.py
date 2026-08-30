"""Elle düzenlemede geri/ileri alma.

Program üzerinde yapılan her elle müdahale, dokunduğu ders saatlerinin o anki
içeriğini bir yığına yazar; geri alma o içeriği geri koyar. Yığın programın
kendisinde durur — kullanıcı sayfayı kapatıp dönse de geçmiş kaybolmaz.

Revision ID: 0012
Revises: 0011
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    mevcut = {c["name"] for c in inspect(op.get_bind()).get_columns("timetables")}
    for sutun in ("edit_undo", "edit_redo"):
        if sutun not in mevcut:
            op.add_column("timetables", sa.Column(sutun, sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("timetables", "edit_redo")
    op.drop_column("timetables", "edit_undo")
