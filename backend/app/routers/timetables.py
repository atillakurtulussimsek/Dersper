"""Ders programı: üretim, ızgara görünümü, elle düzenleme, yayınlama."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import aktif_donem, current_user
from app.models import (
    Assignment, CurriculumEntry, Day, Period, SolveRun, SolveStatus, Term, Timetable,
    TimetableStatus,
)
from app.schemas import (
    AssignmentMove, GridCell, SolveRunOut, TimetableGrid, TimetableIn, TimetableOut,
    WarningIgnoreIn, WarningOut,
)
from app.uyarilar import uyarilari_hesapla
from app.solver import arkaplan

router = APIRouter(prefix="/timetables", tags=["ders programı"],
                   dependencies=[Depends(current_user)])


def _programi_getir(db: Session, timetable_id: int, donem: Term) -> Timetable:
    t = db.get(Timetable, timetable_id)
    if t is None or t.is_deleted or t.term_id != donem.id:
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
            subject_short=a.entry.subject.short_code,
            subject_color=a.entry.subject.color,
            teacher_id=a.entry.teacher_id,
            teacher_name=a.entry.teacher.full_name,
            teacher_short=a.entry.teacher.short_code,
            is_locked=a.is_locked,
        ))
    return hucreler


@router.get("", response_model=list[TimetableOut])
def programlar(
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Timetable]:
    return list(db.scalars(
        select(Timetable)
        .where(Timetable.term_id == donem.id, Timetable.deleted_at.is_(None))
        .order_by(Timetable.created_at.desc())
    ))


@router.post("", response_model=TimetableOut, status_code=status.HTTP_201_CREATED)
def program_olustur(
    payload: TimetableIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Timetable:
    t = Timetable(term_id=donem.id, name=payload.name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{timetable_id}", status_code=status.HTTP_204_NO_CONTENT)
def program_sil(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
):
    """Yumuşak silme: program gizlenir, yerleşimleri saklı kalır."""
    t = _programi_getir(db, timetable_id, donem)
    t.deleted_at = datetime.now(timezone.utc)
    t.public_token = None
    db.commit()


@router.get("/{timetable_id}/grid", response_model=TimetableGrid)
def izgara(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> TimetableGrid:
    t = _programi_getir(db, timetable_id, donem)
    return TimetableGrid(timetable=TimetableOut.model_validate(t),
                         cells=izgara_hucreleri(db, timetable_id))


@router.post("/{timetable_id}/solve", response_model=SolveRunOut,
             status_code=status.HTTP_202_ACCEPTED)
def uret(
    timetable_id: int,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> SolveRun:
    """Program üretimini arka planda başlatır ve hemen döner.

    Üretim, tam yerleşim sağlanana ya da durdurulana kadar arka planda deneme
    yapmayı sürdürür; ilerleme `/runs/active` ucundan izlenir.
    """
    t = _programi_getir(db, timetable_id, donem)

    calisan = db.scalar(
        select(SolveRun)
        .where(SolveRun.timetable_id == t.id,
               SolveRun.status.in_([SolveStatus.BEKLIYOR, SolveStatus.CALISIYOR]))
        .limit(1)
    )
    if calisan is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bu program için zaten bir üretim çalışıyor. Önce onu durdurun.",
        )

    run = SolveRun(timetable_id=t.id, status=SolveStatus.BEKLIYOR)
    db.add(run)
    db.commit()
    db.refresh(run)

    arkaplan.baslat(run.id, donem.id)
    return run


@router.get("/{timetable_id}/runs/active", response_model=SolveRunOut | None)
def calisan_uretim(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> SolveRun | None:
    """Sürmekte olan üretim; yoksa null. Arayüz bunu düzenli aralıklarla sorar."""
    _programi_getir(db, timetable_id, donem)
    db.expire_all()
    return db.scalar(
        select(SolveRun)
        .where(SolveRun.timetable_id == timetable_id,
               SolveRun.status.in_([SolveStatus.BEKLIYOR, SolveStatus.CALISIYOR]))
        .order_by(SolveRun.id.desc())
        .limit(1)
    )


@router.post("/{timetable_id}/runs/{run_id}/stop", response_model=SolveRunOut)
def uretimi_durdur(
    timetable_id: int,
    run_id: int,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> SolveRun:
    """Çalışan üretimi durdurur; o ana kadarki en iyi yerleşim kaydedilir."""
    _programi_getir(db, timetable_id, donem)
    run = db.get(SolveRun, run_id)
    if run is None or run.timetable_id != timetable_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Çalıştırma bulunamadı.")

    run.stop_requested = True
    db.commit()
    if not arkaplan.durdur(run.id) and run.status in (
        SolveStatus.BEKLIYOR, SolveStatus.CALISIYOR
    ):
        # İş parçacığı yok (örneğin uygulama yeniden başlamış): kaydı kapat.
        run.status = SolveStatus.DURDURULDU
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
    db.refresh(run)
    return run


@router.get("/{timetable_id}/runs", response_model=list[SolveRunOut])
def denemeler(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[SolveRun]:
    _programi_getir(db, timetable_id, donem)
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
    donem: Term = Depends(aktif_donem),
) -> TimetableGrid:
    """Elle sürükle-bırak. Çakışma oluşturacak taşımalar reddedilir."""
    t = _programi_getir(db, timetable_id, donem)
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
    timetable_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> TimetableGrid:
    t = _programi_getir(db, timetable_id, donem)
    a = db.get(Assignment, assignment_id)
    if a is None or a.timetable_id != t.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yerleşim bulunamadı.")
    a.is_locked = not a.is_locked
    db.commit()
    return TimetableGrid(timetable=TimetableOut.model_validate(t),
                         cells=izgara_hucreleri(db, t.id))


@router.get("/{timetable_id}/warnings", response_model=list[WarningOut])
def uyarilar(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[dict]:
    """Yerleşimdeki uyarılar. Her istekte o anki programdan hesaplanır."""
    t = _programi_getir(db, timetable_id, donem)
    return uyarilari_hesapla(db, t)


@router.post("/{timetable_id}/warnings/ignore", response_model=list[WarningOut])
def uyariyi_gizle(
    timetable_id: int,
    payload: WarningIgnoreIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> list[dict]:
    """Uyarıyı bu program için kalıcı olarak gizler."""
    t = _programi_getir(db, timetable_id, donem)
    gizlenen = list(t.ignored_warnings or [])
    if payload.key not in gizlenen:
        gizlenen.append(payload.key)
        t.ignored_warnings = gizlenen
        db.commit()
    return uyarilari_hesapla(db, t)


@router.delete("/{timetable_id}/warnings/ignore/{key}", response_model=list[WarningOut])
def uyariyi_geri_getir(
    timetable_id: int,
    key: str,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> list[dict]:
    t = _programi_getir(db, timetable_id, donem)
    gizlenen = [k for k in (t.ignored_warnings or []) if k != key]
    t.ignored_warnings = gizlenen
    db.commit()
    return uyarilari_hesapla(db, t)


@router.post("/{timetable_id}/publish", response_model=TimetableOut)
def yayinla(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> Timetable:
    """Herkese açık, girişsiz görüntülenebilen bir bağlantı üretir."""
    t = _programi_getir(db, timetable_id, donem)
    t.public_token = t.public_token or secrets.token_urlsafe(16)
    t.status = TimetableStatus.YAYINDA
    db.commit()
    db.refresh(t)
    return t


@router.post("/{timetable_id}/unpublish", response_model=TimetableOut)
def yayindan_kaldir(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> Timetable:
    t = _programi_getir(db, timetable_id, donem)
    t.public_token = None
    t.status = TimetableStatus.URETILDI
    db.commit()
    db.refresh(t)
    return t
