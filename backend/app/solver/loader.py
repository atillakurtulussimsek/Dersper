"""Veritabanındaki tanımları çözücünün anladığı yapıya çevirir."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Availability, CurriculumEntry, Day, Period, TeacherAvailability,
)
from app.solver.engine import Lesson, Slot


def slotlari_yukle(db: Session) -> list[Slot]:
    """Aktif günlerdeki, teneffüs olmayan ders saatleri."""
    gunler = db.scalars(
        select(Day)
        .options(selectinload(Day.periods))
        .where(Day.is_active.is_(True))
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


def dersleri_yukle(db: Session) -> list[Lesson]:
    kapali: dict[int, set[int]] = defaultdict(set)
    for row in db.scalars(
        select(TeacherAvailability).where(
            TeacherAvailability.state == Availability.UYGUN_DEGIL
        )
    ):
        kapali[row.teacher_id].add(row.period_id)

    entries = db.scalars(
        select(CurriculumEntry).options(
            selectinload(CurriculumEntry.section),
            selectinload(CurriculumEntry.subject),
            selectinload(CurriculumEntry.teacher),
        )
    )
    dersler: list[Lesson] = []
    for e in entries:
        if not e.section.is_active or not e.subject.is_active or not e.teacher.is_active:
            continue
        dersler.append(Lesson(
            entry_id=e.id,
            section_id=e.section_id,
            section_name=e.section.name,
            teacher_id=e.teacher_id,
            teacher_name=e.teacher.full_name,
            subject_name=e.subject.name,
            weekly_hours=e.weekly_hours,
            block_size=e.block_size,
            max_per_day=e.max_per_day,
            blocked_period_ids=frozenset(kapali.get(e.teacher_id, set())),
        ))
    return dersler
