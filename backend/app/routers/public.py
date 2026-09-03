"""Girişsiz, salt-okunur program görünümü. Yayınlanmış programlar için.

Çok kurumlu kurulumda hangi kurumun programına bakıldığı yayın jetonundan
çıkarılır; girişsiz uçlar hiçbir zaman "ilk kurum" varsayımı yapmaz.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app import siralama
from app.models import Day, Institution, Term, Timetable, TimetableStatus
from app.routers.timetables import izgara_hucreleri
from app.schemas import DayOut, TimetableGrid, TimetableOut

router = APIRouter(prefix="/public", tags=["herkese açık"])


def _yayin(db: Session, token: str) -> Timetable:
    t = db.scalar(select(Timetable).where(Timetable.public_token == token))
    if t is None or t.is_deleted or t.status is not TimetableStatus.YAYINDA:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Böyle bir yayın bulunamadı.")
    return t


@router.get("/timetables/{token}", response_model=TimetableGrid)
def yayindaki_program(token: str, db: Session = Depends(get_db)) -> TimetableGrid:
    t = _yayin(db, token)
    return TimetableGrid(
        timetable=TimetableOut.model_validate(t),
        cells=izgara_hucreleri(db, t.id),
        section_names=[s.name for s in siralama.sirali_subeler(db, t.term)],
    )


@router.get("/timetables/{token}/timegrid", response_model=list[DayOut])
def yayindaki_izgara(token: str, db: Session = Depends(get_db)) -> list[Day]:
    """Yayınlanan programın dönemine ait zaman ızgarası — gün adları ve teneffüsler."""
    t = _yayin(db, token)
    return list(db.scalars(
        select(Day)
        .options(selectinload(Day.periods))
        .where(Day.term_id == t.term_id)
        .order_by(Day.index)
    ))


@router.get("/timetables/{token}/institution")
def yayindaki_kurum(token: str, db: Session = Depends(get_db)) -> dict:
    t = _yayin(db, token)
    donem = db.get(Term, t.term_id)
    inst = db.get(Institution, donem.institution_id) if donem else None
    return {"name": inst.name if inst else None, "term": donem.name if donem else None}
