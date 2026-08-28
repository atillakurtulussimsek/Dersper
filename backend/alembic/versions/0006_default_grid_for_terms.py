"""Izgarası olmayan dönemlere varsayılan zaman ızgarası.

Dönem özelliği ilk çıktığında yeni dönemler tamamen boş açılıyordu; zaman
ızgarası da olmadığı için o dönemlerde ders saati eklenemiyor, müsaitlik
işaretlenemiyor ve program üretilemiyordu. Bu revizyon, hiç günü olmayan
dönemlere Pazartesi–Cuma / günde 8 ders saatlik varsayılan iskeleti kurar.

Yalnızca günü olmayan dönemlere dokunur; var olan ızgaralar korunur.

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
DERS_SAATI = 8


def upgrade() -> None:
    baglanti = op.get_bind()
    bos_donemler = [
        r[0] for r in baglanti.execute(sa.text(
            "SELECT t.id FROM terms t "
            "LEFT JOIN days d ON d.term_id = t.id "
            "WHERE d.id IS NULL GROUP BY t.id"
        ))
    ]
    for donem_id in bos_donemler:
        for i, ad in enumerate(GUN_ADLARI):
            baglanti.execute(
                sa.text("INSERT INTO days (term_id, `index`, name, is_active) "
                        "VALUES (:t, :i, :ad, :aktif)"),
                {"t": donem_id, "i": i, "ad": ad, "aktif": i < 5},
            )
            if i >= 5:
                continue
            gun_id = baglanti.execute(
                sa.text("SELECT id FROM days WHERE term_id = :t AND `index` = :i"),
                {"t": donem_id, "i": i},
            ).scalar()
            for p in range(DERS_SAATI):
                baglanti.execute(
                    sa.text("INSERT INTO periods (day_id, `index`, name, is_break) "
                            "VALUES (:g, :i, :ad, :mola)"),
                    {"g": gun_id, "i": p, "ad": f"{p + 1}. ders", "mola": False},
                )


def downgrade() -> None:
    # Eklenen ızgaralar kullanıcı verisine karışmış olabilir; geri alınmaz.
    pass
