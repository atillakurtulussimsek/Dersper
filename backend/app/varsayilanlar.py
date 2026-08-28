"""Yeni bir dönem açılırken kurulan varsayılanlar.

Dönem boş açılır, ama zaman ızgarası hariç: gün ve ders saati tanımlı olmadan
öğretmen müsaitliği işaretlenemez, ders yerleştirilemez. Bu yüzden her dönem
düzenlenebilir bir haftalık iskeletle başlar.
"""
from sqlalchemy.orm import Session

from app.models import Day, Period, Term

GUN_ADLARI = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
VARSAYILAN_DERS_SAATI = 8


def varsayilan_izgara(db: Session, donem: Term) -> None:
    """Pazartesi–Cuma açık, günde 8 ders saati. Kullanıcı sonra düzenler."""
    for i, ad in enumerate(GUN_ADLARI):
        gun = Day(term_id=donem.id, index=i, name=ad, is_active=i < 5)
        db.add(gun)
        db.flush()
        if not gun.is_active:
            continue
        for p in range(VARSAYILAN_DERS_SAATI):
            db.add(Period(day_id=gun.id, index=p, name=f"{p + 1}. ders"))
