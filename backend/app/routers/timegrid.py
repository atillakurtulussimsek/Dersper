"""Zaman ızgarası: günler ve ders saatleri. Ders saati sayısı güne göre değişir."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import current_user
from app.models import Assignment, Day, Period
from app.schemas import DayIn, DayOut, PeriodIn

router = APIRouter(prefix="/timegrid", tags=["zaman ızgarası"],
                   dependencies=[Depends(current_user)])


def _gunleri_getir(db: Session) -> list[Day]:
    return list(
        db.scalars(
            select(Day).options(selectinload(Day.periods)).order_by(Day.index)
        )
    )


@router.get("", response_model=list[DayOut])
def izgarayi_getir(db: Session = Depends(get_db)) -> list[Day]:
    return _gunleri_getir(db)


@router.put("", response_model=list[DayOut])
def izgarayi_kaydet(payload: list[DayIn], db: Session = Depends(get_db)) -> list[Day]:
    """Izgarayı bütünüyle değiştirir. Yerleşmiş program varsa reddedilir."""
    if db.scalar(select(Assignment.id).limit(1)) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Yerleşmiş bir ders programı varken zaman ızgarası değiştirilemez. "
            "Önce programı silin.",
        )

    mevcut = {d.index: d for d in _gunleri_getir(db)}
    gelen_indexler = {d.index for d in payload}

    for gun in mevcut.values():
        if gun.index not in gelen_indexler:
            db.delete(gun)

    for gelen in payload:
        gun = mevcut.get(gelen.index)
        if gun is None:
            gun = Day(index=gelen.index, name=gelen.name, is_active=gelen.is_active)
            db.add(gun)
            db.flush()
        else:
            gun.name, gun.is_active = gelen.name, gelen.is_active
            for p in list(gun.periods):
                db.delete(p)
            db.flush()
        for p in gelen.periods:
            db.add(Period(day_id=gun.id, **p.model_dump()))

    db.commit()
    return _gunleri_getir(db)


@router.post("/days/{day_id}/periods", response_model=DayOut,
             status_code=status.HTTP_201_CREATED)
def ders_saati_ekle(
    day_id: int, payload: PeriodIn, db: Session = Depends(get_db)
) -> Day:
    gun = db.get(Day, day_id)
    if gun is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gün bulunamadı.")
    db.add(Period(day_id=day_id, **payload.model_dump()))
    db.commit()
    db.refresh(gun)
    return gun
