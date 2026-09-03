"""Dönemin tamamını yeni bir döneme kopyalar.

Yeni öğretim yılı çoğu zaman bir öncekinin küçük farklarla tekrarıdır: aynı
zaman ızgarası, aynı binalar, büyük ölçüde aynı kadro ve dersler. Tanım
ekranlarındaki "geçmiş dönemden aktar" bunları tek tek taşır; burası hepsini
bir kerede, bağımlılık sırasıyla ve kimlikleri yeniden eşleyerek taşır.

Kopyalanan:  zaman ızgarası, binalar, öğretmenler (müsaitlik dahil), dersler,
             şubeler (bina, müsaitlik, elle sıra dahil), ders atamaları
             (birleşik dersler dahil), dönem ayarları.
Kopyalanmayan: ders programları ve sürümleri. Onlar dönemin sonucudur; yeni
             dönemde yeniden üretilir. Silinmiş kayıtlar da taşınmaz.

Her şey tek işlemde yazılır: yarıda kalırsa yeni dönem hiç oluşmaz.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Building, CurriculumEntry, CurriculumEntrySection, Day, Period, Section,
    SectionAvailability, Subject, Teacher, TeacherAvailability, Term,
)


def _canlilar(db: Session, model, donem: Term):
    """Dönemin silinmemiş kayıtları, kimlik sırasıyla (deterministik kopya)."""
    return db.scalars(
        select(model)
        .where(model.term_id == donem.id, model.deleted_at.is_(None))
        .order_by(model.id)
    )


def donemi_kopyala(
    db: Session,
    kaynak: Term,
    ad: str,
    starts_on: date | None = None,
    ends_on: date | None = None,
) -> tuple[Term, dict[str, int]]:
    """Kaynağın kopyası olan yeni dönemi döner; işlemi çağıran taraf onaylar.

    İkinci değer neyin kaç tane kopyalandığıdır — kullanıcıya özet için.
    """
    yeni = Term(
        institution_id=kaynak.institution_id,
        name=ad,
        starts_on=starts_on,
        ends_on=ends_on,
        block_building_switch=kaynak.block_building_switch,
        conflict_basis=kaynak.conflict_basis,
        section_order=kaynak.section_order,
    )
    db.add(yeni)
    db.flush()
    sayim: dict[str, int] = {}

    # Zaman ızgarası. Müsaitlik satırları ders saatine bağlı; eşleme şart.
    saat_esi: dict[int, int] = {}
    gunler = db.scalars(
        select(Day).options(selectinload(Day.periods))
        .where(Day.term_id == kaynak.id).order_by(Day.index)
    ).all()
    for g in gunler:
        gun = Day(term_id=yeni.id, index=g.index, name=g.name, is_active=g.is_active)
        db.add(gun)
        db.flush()
        for p in sorted(g.periods, key=lambda x: x.index):
            saat = Period(day_id=gun.id, index=p.index, name=p.name,
                          start_time=p.start_time, end_time=p.end_time,
                          is_break=p.is_break, is_lunch=p.is_lunch)
            db.add(saat)
            db.flush()
            saat_esi[p.id] = saat.id
    sayim["gun"] = len(gunler)
    sayim["ders_saati"] = len(saat_esi)

    bina_esi: dict[int, int] = {}
    for b in _canlilar(db, Building, kaynak):
        kopya = Building(term_id=yeni.id, name=b.name, short_code=b.short_code,
                         notes=b.notes, is_active=b.is_active)
        db.add(kopya)
        db.flush()
        bina_esi[b.id] = kopya.id
    sayim["bina"] = len(bina_esi)

    ogretmen_esi: dict[int, int] = {}
    for t in _canlilar(db, Teacher, kaynak):
        kopya = Teacher(term_id=yeni.id, full_name=t.full_name, short_code=t.short_code,
                        branch=t.branch, max_daily_hours=t.max_daily_hours,
                        max_half_days=t.max_half_days, notes=t.notes, color=t.color,
                        is_active=t.is_active)
        db.add(kopya)
        db.flush()
        ogretmen_esi[t.id] = kopya.id
    sayim["ogretmen"] = len(ogretmen_esi)
    if ogretmen_esi:
        for m in db.scalars(select(TeacherAvailability)
                            .where(TeacherAvailability.teacher_id.in_(ogretmen_esi))):
            if m.period_id in saat_esi:
                db.add(TeacherAvailability(teacher_id=ogretmen_esi[m.teacher_id],
                                           period_id=saat_esi[m.period_id], state=m.state))

    ders_esi: dict[int, int] = {}
    for d in _canlilar(db, Subject, kaynak):
        kopya = Subject(term_id=yeni.id, name=d.name, short_code=d.short_code,
                        color=d.color, is_active=d.is_active)
        db.add(kopya)
        db.flush()
        ders_esi[d.id] = kopya.id
    sayim["ders"] = len(ders_esi)

    sube_esi: dict[int, int] = {}
    for s in _canlilar(db, Section, kaynak):
        kopya = Section(term_id=yeni.id, name=s.name, grade_level=s.grade_level,
                        student_count=s.student_count, is_active=s.is_active,
                        sort_order=s.sort_order,
                        building_id=bina_esi.get(s.building_id) if s.building_id else None)
        db.add(kopya)
        db.flush()
        sube_esi[s.id] = kopya.id
    sayim["sube"] = len(sube_esi)
    if sube_esi:
        for m in db.scalars(select(SectionAvailability)
                            .where(SectionAvailability.section_id.in_(sube_esi))):
            if m.period_id in saat_esi:
                db.add(SectionAvailability(section_id=sube_esi[m.section_id],
                                           period_id=saat_esi[m.period_id], state=m.state))

    # Ders atamaları: öğretmeni ya da dersi silinmiş satır kopyalanmaz — yeni
    # dönemde karşılığı olmayan bir kayda bağlanamaz.
    atama_sayisi = 0
    if sube_esi:
        for e in db.scalars(
            select(CurriculumEntry)
            .options(selectinload(CurriculumEntry.extra_sections))
            .where(CurriculumEntry.section_id.in_(sube_esi),
                   CurriculumEntry.deleted_at.is_(None))
            .order_by(CurriculumEntry.id)
        ):
            if e.subject_id not in ders_esi or e.teacher_id not in ogretmen_esi:
                continue
            kopya = CurriculumEntry(
                section_id=sube_esi[e.section_id], subject_id=ders_esi[e.subject_id],
                teacher_id=ogretmen_esi[e.teacher_id], weekly_hours=e.weekly_hours,
                block_pattern=e.block_pattern, max_per_day=e.max_per_day,
            )
            kopya.extra_sections = [
                CurriculumEntrySection(section_id=sube_esi[x.section_id])
                for x in e.extra_sections if x.section_id in sube_esi
            ]
            db.add(kopya)
            atama_sayisi += 1
    sayim["mufredat"] = atama_sayisi

    db.flush()
    return yeni, sayim
