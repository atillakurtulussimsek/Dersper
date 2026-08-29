"""Veritabanındaki tanımları çözücünün anladığı yapıya çevirir."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import bloklar
from app.models import (
    Availability, CurriculumEntry, Day, Section, SectionAvailability, Teacher,
    TeacherAvailability, Term,
)
from app.solver.engine import Lesson, Slot


def sabah_mi(saatler: list, ders_saati) -> bool:
    """Bir ders saati öğle arasından önce mi?

    Günde öğle arası tanımlıysa sınır odur. Tanımlı değilse gün ders saati
    sayısına göre ortadan ikiye bölünür ve tek sayıda saat varsa fazlalık
    sabaha yazılır — okul günü tipik olarak sabah ağırlıklıdır. Bölme noktası
    o durumda bir varsayımdır; arayüz bunu kullanıcıya söyler.

    `saatler` günün TÜM saatleridir (teneffüsler dahil); öğle arasının yerini
    ancak böyle bilebiliriz.
    """
    ogle = next((p for p in saatler if p.is_lunch), None)
    if ogle is not None:
        return ders_saati.index < ogle.index

    dersler = [p for p in saatler if not p.is_break]
    if not dersler:
        return True
    sinir = -(-len(dersler) // 2)        # yukarı yuvarlama
    sirasi = [p.id for p in dersler].index(ders_saati.id)
    return sirasi < sinir


def slotlari_yukle(db: Session, donem: Term) -> list[Slot]:
    """Dönemin aktif günlerindeki, teneffüs olmayan ders saatleri."""
    gunler = db.scalars(
        select(Day)
        .options(selectinload(Day.periods))
        .where(Day.term_id == donem.id, Day.is_active.is_(True))
        .order_by(Day.index)
    )
    slots: list[Slot] = []
    for gun in gunler:
        saatler = sorted(gun.periods, key=lambda x: x.index)
        for p in saatler:
            if p.is_break:
                continue
            slots.append(Slot(
                period_id=p.id,
                day_index=gun.index,
                period_index=p.index,
                day_name=gun.name,
                period_name=p.name,
                sabah=sabah_mi(saatler, p),
            ))
    return slots


def gun_sinirlarini_yukle(db: Session, donem: Term) -> dict[int, int]:
    """teacher_id -> haftalık yarım gün sınırı. Sınırsız öğretmenler listede yok."""
    return {
        t.id: t.max_half_days
        for t in db.scalars(
            select(Teacher).where(
                Teacher.term_id == donem.id,
                Teacher.deleted_at.is_(None),
                Teacher.is_active.is_(True),
                Teacher.max_half_days.is_not(None),
            )
        )
    }


def dersleri_yukle(
    db: Session, donem: Term, section_ids: list[int] | None = None
) -> list[Lesson]:
    """Dönemin dersleri. `section_ids` verilirse yalnızca o şubelerinkiler."""
    ogretmen_kapali: dict[int, set[int]] = defaultdict(set)
    for row in db.scalars(
        select(TeacherAvailability).where(
            TeacherAvailability.state == Availability.UYGUN_DEGIL
        )
    ):
        ogretmen_kapali[row.teacher_id].add(row.period_id)

    sube_kapali: dict[int, set[int]] = defaultdict(set)
    for row in db.scalars(
        select(SectionAvailability).where(
            SectionAvailability.state == Availability.UYGUN_DEGIL
        )
    ):
        sube_kapali[row.section_id].add(row.period_id)

    sorgu = (
        select(CurriculumEntry)
        .join(Section, Section.id == CurriculumEntry.section_id)
        .where(Section.term_id == donem.id, CurriculumEntry.deleted_at.is_(None))
    )
    if section_ids is not None:
        sorgu = sorgu.where(CurriculumEntry.section_id.in_(section_ids))
    entries = db.scalars(
        sorgu.options(
            selectinload(CurriculumEntry.section),
            selectinload(CurriculumEntry.subject),
            selectinload(CurriculumEntry.teacher),
        )
    )
    dersler: list[Lesson] = []
    for e in entries:
        if not e.section.is_active or not e.subject.is_active or not e.teacher.is_active:
            continue
        if e.section.is_deleted or e.subject.is_deleted or e.teacher.is_deleted:
            continue
        dersler.append(Lesson(
            entry_id=e.id,
            section_id=e.section_id,
            section_name=e.section.name,
            teacher_id=e.teacher_id,
            teacher_name=e.teacher.full_name,
            subject_name=e.subject.name,
            weekly_hours=e.weekly_hours,
            blocks=tuple(bloklar.coz(e.block_pattern, e.weekly_hours)),
            max_per_day=e.max_per_day,
            blocked_period_ids=frozenset(ogretmen_kapali.get(e.teacher_id, set())),
            section_blocked_period_ids=frozenset(sube_kapali.get(e.section_id, set())),
        ))
    return dersler
