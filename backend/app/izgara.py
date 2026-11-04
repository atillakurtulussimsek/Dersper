"""Bir programın hangi zaman ızgarasını kullandığı.

Dönemin genel ızgarası `Day.timetable_id IS NULL` olan günlerdir; bütün
programlar onu paylaşır. Oluşturulurken kendi ızgarası seçilen program
(`Timetable.own_grid`) yalnızca kendi günlerini görür. Ders saati kimlikleri
ayrı olduğu için o saatlere yazılan müsaitlik işaretleri de programa özeldir.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Day, Period, SectionAvailability, TeacherAvailability, Term, Timetable,
)


def gun_kosulu(donem: Term, program: Timetable | None = None):
    """Programın (ya da program yoksa genel ızgaranın) günlerini seçen koşul."""
    if program is not None and program.own_grid:
        return Day.timetable_id == program.id
    return (Day.term_id == donem.id) & Day.timetable_id.is_(None)


def gunleri_getir(
    db: Session, donem: Term, program: Timetable | None = None,
    yalniz_aktif: bool = False,
) -> list[Day]:
    sorgu = (
        select(Day).options(selectinload(Day.periods))
        .where(gun_kosulu(donem, program)).order_by(Day.sira, Day.index)
    )
    if yalniz_aktif:
        sorgu = sorgu.where(Day.is_active.is_(True))
    return list(db.scalars(sorgu))


def saat_kimlikleri(db: Session, donem: Term, program: Timetable | None = None) -> set[int]:
    return set(db.scalars(
        select(Period.id).join(Day, Day.id == Period.day_id)
        .where(gun_kosulu(donem, program))
    ))


def genel_izgarayi_kopyala(db: Session, donem: Term, program: Timetable) -> None:
    """Genel ızgarayı ve ona yazılmış müsaitlik işaretlerini programa kopyalar.

    Kopya bağımsızdır: sonradan genel ızgarada ya da genel müsaitlikte yapılan
    değişiklik programa yansımaz, programdaki değişiklik de genele.
    """
    saat_esi: dict[int, int] = {}
    for g in gunleri_getir(db, donem):
        gun = Day(term_id=donem.id, timetable_id=program.id, index=g.index,
                  sira=g.sira, name=g.name, is_active=g.is_active)
        db.add(gun)
        db.flush()
        for p in sorted(g.periods, key=lambda x: x.index):
            saat = Period(day_id=gun.id, index=p.index, name=p.name,
                          start_time=p.start_time, end_time=p.end_time,
                          is_break=p.is_break, is_lunch=p.is_lunch)
            db.add(saat)
            db.flush()
            saat_esi[p.id] = saat.id
    if not saat_esi:
        return
    for model, alan in ((TeacherAvailability, "teacher_id"),
                        (SectionAvailability, "section_id")):
        for r in db.scalars(select(model).where(model.period_id.in_(list(saat_esi)))):
            db.add(model(**{alan: getattr(r, alan)},
                         period_id=saat_esi[r.period_id], state=r.state))
    db.flush()


def bos_izgara_kur(db: Session, donem: Term, program: Timetable) -> None:
    """Ders saati olmayan gün iskeleti: düzenleyicinin ekleyecek yeri olsun."""
    from app.varsayilanlar import GUN_ADLARI

    for i, ad in enumerate(GUN_ADLARI):
        db.add(Day(term_id=donem.id, timetable_id=program.id, index=i, sira=i,
                   name=ad, is_active=i < 5))
    db.flush()
