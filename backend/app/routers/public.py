"""Girişsiz, salt-okunur program görünümü. Yayınlanmış programlar için."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Institution, Timetable, TimetableStatus
from app.routers.timetables import izgara_hucreleri
from app.schemas import TimetableGrid, TimetableOut

router = APIRouter(prefix="/public", tags=["herkese açık"])


@router.get("/timetables/{token}", response_model=TimetableGrid)
def yayindaki_program(token: str, db: Session = Depends(get_db)) -> TimetableGrid:
    t = db.scalar(select(Timetable).where(Timetable.public_token == token))
    if t is None or t.is_deleted or t.status is not TimetableStatus.YAYINDA:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Böyle bir yayın bulunamadı.")
    return TimetableGrid(timetable=TimetableOut.model_validate(t),
                         cells=izgara_hucreleri(db, t.id))


@router.get("/institution")
def kurum_adi(db: Session = Depends(get_db)) -> dict:
    inst = db.scalar(select(Institution).limit(1))
    return {"name": inst.name if inst else None}
