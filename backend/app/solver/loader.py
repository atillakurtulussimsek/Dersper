"""Veritabanındaki tanımları çözücünün anladığı yapıya çevirir."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import bloklar
from app import cakisma
from app.models import (
    Availability, CurriculumEntry, CurriculumEntrySection, Day, Section,
    SectionAvailability, Teacher,
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
                baslangic=cakisma.dakikaya(p.start_time),
                bitis=cakisma.dakikaya(p.end_time),
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
    entries = db.scalars(
        sorgu.options(
            selectinload(CurriculumEntry.section),
            selectinload(CurriculumEntry.subject),
            selectinload(CurriculumEntry.teacher),
            selectinload(CurriculumEntry.extra_sections)
            .selectinload(CurriculumEntrySection.section),
        )
    )
    kapsam = None if section_ids is None else set(section_ids)
    dersler: list[Lesson] = []
    for e in entries:
        subeler = [e.section] + [x.section for x in e.extra_sections]
        # Birleşik derste şubelerden biri kapsam dışıysa ders yine alınır:
        # dersin kaybolması, kapsamdaki şubenin saatinin eksik kalması demek
        # olurdu. Kapsam dışı şubenin kendi dersleri modelde olmadığı için
        # yanlış bir çakışma da doğmaz.
        if kapsam is not None and not any(sb.id in kapsam for sb in subeler):
            continue
        if not e.subject.is_active or not e.teacher.is_active:
            continue
        if e.subject.is_deleted or e.teacher.is_deleted:
            continue
        if any(not sb.is_active or sb.is_deleted for sb in subeler):
            continue

        # Birleşik ders tek bir yerde işlenir; şubeler farklı binalardaysa o
        # yer belirsizdir, bina kuralı bu derse uygulanmaz.
        binalar = {sb.building_id for sb in subeler}
        dersler.append(Lesson(
            entry_id=e.id,
            section_id=e.section_id,
            section_name=e.section.name,
            sections=tuple((sb.id, sb.name) for sb in subeler),
            teacher_id=e.teacher_id,
            teacher_name=e.teacher.full_name,
            subject_name=e.subject.name,
            weekly_hours=e.weekly_hours,
            blocks=tuple(bloklar.coz(e.block_pattern, e.weekly_hours)),
            max_per_day=e.max_per_day,
            building_id=binalar.pop() if len(binalar) == 1 else None,
            blocked_period_ids=frozenset(ogretmen_kapali.get(e.teacher_id, set())),
            # Şubelerden herhangi biri kapalıysa birleşik ders o saate konamaz.
            section_blocked_period_ids=frozenset().union(
                *(sube_kapali.get(sb.id, set()) for sb in subeler)
            ),
        ))
    return dersler
