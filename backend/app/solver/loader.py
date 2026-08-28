"""Veritabanındaki tanımları çözücünün anladığı yapıya çevirir."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import bloklar
from app.models import (
    Availability, CurriculumEntry, Day, Section, SectionAvailability,
    TeacherAvailability, Term,
)
from app.solver.engine import Lesson, Slot


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
        for p in sorted(gun.periods, key=lambda x: x.index):
            if p.is_break:
                continue
            slots.append(Slot(
                period_id=p.id,
                day_index=gun.index,
                period_index=p.index,
                day_name=gun.name,
                period_name=p.name,
            ))
    return slots


def dersleri_yukle(db: Session, donem: Term) -> list[Lesson]:
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

    entries = db.scalars(
        select(CurriculumEntry)
        .join(Section, Section.id == CurriculumEntry.section_id)
        .where(Section.term_id == donem.id, CurriculumEntry.deleted_at.is_(None))
        .options(
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
