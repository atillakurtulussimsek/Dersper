"""Ders programı: üretim, ızgara görünümü, elle düzenleme, yayınlama."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ai import client as ai
from app.db import get_db
from app.deps import current_user
from app.models import (
    AiSettings, Assignment, CurriculumEntry, Day, Period, SolveRun, SolveStatus,
    Timetable, TimetableStatus,
)
from app.schemas import (
    AssignmentMove, GridCell, SolveRunOut, TimetableGrid, TimetableIn, TimetableOut,
)
from app.solver.diagnose import rapor_olustur
from app.solver.engine import SolveInput, solve
from app.solver.loader import dersleri_yukle, slotlari_yukle

router = APIRouter(prefix="/timetables", tags=["ders programı"],
                   dependencies=[Depends(current_user)])


def _programi_getir(db: Session, timetable_id: int) -> Timetable:
    t = db.get(Timetable, timetable_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ders programı bulunamadı.")
    return t


def izgara_hucreleri(db: Session, timetable_id: int) -> list[GridCell]:
    """Arayüzün doğrudan çizebileceği hücre listesi."""
    period_bilgi = {
        p.id: (d.index, p.index)
        for d in db.scalars(select(Day).options(selectinload(Day.periods)))
        for p in d.periods
    }
    atamalar = db.scalars(
        select(Assignment)
        .options(
            selectinload(Assignment.entry).selectinload(CurriculumEntry.section),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.subject),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.teacher),
        )
        .where(Assignment.timetable_id == timetable_id)
    )
    hucreler: list[GridCell] = []
    for a in atamalar:
        konum = period_bilgi.get(a.period_id)
        if konum is None:
            continue
        gun_index, ders_index = konum
        hucreler.append(GridCell(
            assignment_id=a.id,
            period_id=a.period_id,
            day_index=gun_index,
            period_index=ders_index,
            section_id=a.entry.section_id,
            section_name=a.entry.section.name,
            subject_name=a.entry.subject.name,
            subject_color=a.entry.subject.color,
            teacher_id=a.entry.teacher_id,
            teacher_name=a.entry.teacher.full_name,
            is_locked=a.is_locked,
        ))
    return hucreler


@router.get("", response_model=list[TimetableOut])
def programlar(db: Session = Depends(get_db)) -> list[Timetable]:
    return list(db.scalars(select(Timetable).order_by(Timetable.created_at.desc())))


@router.post("", response_model=TimetableOut, status_code=status.HTTP_201_CREATED)
def program_olustur(payload: TimetableIn, db: Session = Depends(get_db)) -> Timetable:
    t = Timetable(name=payload.name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{timetable_id}", status_code=status.HTTP_204_NO_CONTENT)
def program_sil(timetable_id: int, db: Session = Depends(get_db)):
    db.delete(_programi_getir(db, timetable_id))
    db.commit()


@router.get("/{timetable_id}/grid", response_model=TimetableGrid)
def izgara(timetable_id: int, db: Session = Depends(get_db)) -> TimetableGrid:
    t = _programi_getir(db, timetable_id)
    return TimetableGrid(timetable=TimetableOut.model_validate(t),
                         cells=izgara_hucreleri(db, timetable_id))


@router.post("/{timetable_id}/solve", response_model=SolveRunOut)
def uret(
    timetable_id: int,
    time_limit_seconds: float = 30.0,
    db: Session = Depends(get_db),
) -> SolveRun:
    """Programı üretir. Yerleşmeyen saat kalırsa tanı raporu ve yapay zeka
    açıklaması üretilir; yerleşenler yine de kaydedilir."""
    t = _programi_getir(db, timetable_id)
    slots = slotlari_yukle(db)
    lessons = dersleri_yukle(db)

    run = SolveRun(timetable_id=t.id, status=SolveStatus.CALISIYOR)
    db.add(run)
    db.commit()

    kilitli: dict[int, list[int]] = {}
    for a in db.scalars(
        select(Assignment).where(
            Assignment.timetable_id == t.id, Assignment.is_locked.is_(True)
        )
    ):
        kilitli.setdefault(a.curriculum_entry_id, []).append(a.period_id)

    sonuc = solve(SolveInput(
        slots=slots, lessons=lessons, locked=kilitli,
        time_limit_seconds=max(5.0, min(time_limit_seconds, 600.0)),
    ))

    for a in db.scalars(select(Assignment).where(Assignment.timetable_id == t.id)):
        db.delete(a)
    db.flush()
    for entry_id, period_id in sonuc.placements:
        db.add(Assignment(
            timetable_id=t.id, curriculum_entry_id=entry_id,
            period_id=period_id, is_locked=period_id in kilitli.get(entry_id, []),
        ))

    rapor = rapor_olustur(slots, lessons, sonuc.unplaced, sonuc.status_name,
                          sonuc.seconds)
    run.report = rapor
    run.seconds = sonuc.seconds
    run.finished_at = datetime.now(timezone.utc)

    if sonuc.ok and sonuc.placements:
        run.status = SolveStatus.BASARILI
        t.status = TimetableStatus.URETILDI
    elif sonuc.placements:
        run.status = SolveStatus.COZUMSUZ
        t.status = TimetableStatus.TASLAK
    else:
        run.status = SolveStatus.HATA if not slots or not lessons else SolveStatus.COZUMSUZ

    if run.status is not SolveStatus.BASARILI:
        ayar = db.scalar(select(AiSettings).limit(1))
        try:
            run.ai_explanation = ai.cozumsuzluk_acikla(ayar, rapor)
        except ai.AiKapali:
            run.ai_explanation = None
        except Exception as e:  # sağlayıcı hatası programı üretmeyi engellemesin
            run.ai_explanation = f"Yapay zeka açıklaması alınamadı: {e}"

    db.commit()
    db.refresh(run)
    return run


@router.get("/{timetable_id}/runs", response_model=list[SolveRunOut])
def denemeler(timetable_id: int, db: Session = Depends(get_db)) -> list[SolveRun]:
    _programi_getir(db, timetable_id)
    return list(db.scalars(
        select(SolveRun)
        .where(SolveRun.timetable_id == timetable_id)
        .order_by(SolveRun.started_at.desc())
    ))


@router.patch("/{timetable_id}/assignments/{assignment_id}", response_model=TimetableGrid)
def dersi_tasi(
    timetable_id: int,
    assignment_id: int,
    payload: AssignmentMove,
    db: Session = Depends(get_db),
) -> TimetableGrid:
    """Elle sürükle-bırak. Çakışma oluşturacak taşımalar reddedilir."""
    t = _programi_getir(db, timetable_id)
    a = db.get(Assignment, assignment_id)
    if a is None or a.timetable_id != t.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yerleşim bulunamadı.")
    hedef = db.get(Period, payload.period_id)
    if hedef is None or hedef.is_break:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Hedef ders saati geçersiz.")

    entry = db.get(CurriculumEntry, a.curriculum_entry_id)
    cakisan = db.scalars(
        select(Assignment)
        .options(selectinload(Assignment.entry))
        .where(Assignment.timetable_id == t.id,
               Assignment.period_id == payload.period_id,
               Assignment.id != a.id)
    )
    for diger in cakisan:
        if diger.entry.section_id == entry.section_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{entry.section.name} şubesinin o saatte zaten dersi var.",
            )
        if diger.entry.teacher_id == entry.teacher_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{entry.teacher.full_name} öğretmenin o saatte zaten dersi var.",
            )

    a.period_id = payload.period_id
    db.commit()
    return TimetableGrid(timetable=TimetableOut.model_validate(t),
                         cells=izgara_hucreleri(db, t.id))


@router.post("/{timetable_id}/assignments/{assignment_id}/lock",
             response_model=TimetableGrid)
def kilidi_degistir(
    timetable_id: int, assignment_id: int, db: Session = Depends(get_db)
) -> TimetableGrid:
    t = _programi_getir(db, timetable_id)
    a = db.get(Assignment, assignment_id)
    if a is None or a.timetable_id != t.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yerleşim bulunamadı.")
    a.is_locked = not a.is_locked
    db.commit()
    return TimetableGrid(timetable=TimetableOut.model_validate(t),
                         cells=izgara_hucreleri(db, t.id))


@router.post("/{timetable_id}/publish", response_model=TimetableOut)
def yayinla(timetable_id: int, db: Session = Depends(get_db)) -> Timetable:
    """Herkese açık, girişsiz görüntülenebilen bir bağlantı üretir."""
    t = _programi_getir(db, timetable_id)
    t.public_token = t.public_token or secrets.token_urlsafe(16)
    t.status = TimetableStatus.YAYINDA
    db.commit()
    db.refresh(t)
    return t


@router.post("/{timetable_id}/unpublish", response_model=TimetableOut)
def yayindan_kaldir(timetable_id: int, db: Session = Depends(get_db)) -> Timetable:
    t = _programi_getir(db, timetable_id)
    t.public_token = None
    t.status = TimetableStatus.URETILDI
    db.commit()
    db.refresh(t)
    return t
