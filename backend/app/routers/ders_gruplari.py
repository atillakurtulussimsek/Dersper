"""Ders grupları: benzer derslerin (Temel Matematik, İleri Matematik,
Geometri) bir şubede arka arkaya gelmemesi için öbekler."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import aktif_donem, current_user
from app.models import Subject, SubjectGroup, SubjectGroupMember, Term
from app.schemas import SubjectGroupIn, SubjectGroupOut

router = APIRouter(prefix="/subject-groups", tags=["ders grupları"],
                   dependencies=[Depends(current_user)])


def _cikti(g: SubjectGroup) -> SubjectGroupOut:
    uyeler = sorted(g.members, key=lambda m: m.subject.name)
    return SubjectGroupOut(
        id=g.id, name=g.name,
        subject_ids=[m.subject_id for m in uyeler],
        subject_names=[m.subject.name for m in uyeler],
    )


def _grup(db: Session, group_id: int, donem: Term) -> SubjectGroup:
    g = db.get(SubjectGroup, group_id)
    if g is None or g.term_id != donem.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ders grubu bulunamadı.")
    return g


def _dogrula(db: Session, payload: SubjectGroupIn, donem: Term, haric: int | None) -> None:
    dersler = {
        s.id: s for s in db.scalars(select(Subject).where(
            Subject.id.in_(payload.subject_ids), Subject.term_id == donem.id,
            Subject.deleted_at.is_(None),
        ))
    }
    if len(dersler) != len(payload.subject_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Seçilen derslerden bazıları bu dönemde yok.")
    # Bir ders yalnız bir grupta olabilir.
    for m in db.scalars(
        select(SubjectGroupMember)
        .join(SubjectGroup, SubjectGroup.id == SubjectGroupMember.group_id)
        .where(SubjectGroupMember.subject_id.in_(payload.subject_ids),
               SubjectGroup.term_id == donem.id)
    ):
        if m.group_id != haric:
            grup = db.get(SubjectGroup, m.group_id)
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{dersler[m.subject_id].name} zaten \"{grup.name}\" grubunda; "
                f"bir ders tek grupta olabilir.",
            )


@router.get("", response_model=list[SubjectGroupOut])
def gruplar(db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)):
    return [_cikti(g) for g in db.scalars(
        select(SubjectGroup).where(SubjectGroup.term_id == donem.id)
        .order_by(SubjectGroup.name)
    )]


@router.post("", response_model=SubjectGroupOut, status_code=status.HTTP_201_CREATED)
def grup_ekle(
    payload: SubjectGroupIn,
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem),
):
    _dogrula(db, payload, donem, None)
    g = SubjectGroup(term_id=donem.id, name=payload.name)
    g.members = [SubjectGroupMember(subject_id=sid) for sid in payload.subject_ids]
    db.add(g)
    db.commit()
    db.refresh(g)
    return _cikti(g)


@router.put("/{group_id}", response_model=SubjectGroupOut)
def grup_guncelle(
    group_id: int, payload: SubjectGroupIn,
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem),
):
    g = _grup(db, group_id, donem)
    _dogrula(db, payload, donem, g.id)
    g.name = payload.name
    g.members = [SubjectGroupMember(subject_id=sid) for sid in payload.subject_ids]
    db.commit()
    db.refresh(g)
    return _cikti(g)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def grup_sil(
    group_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem),
):
    g = _grup(db, group_id, donem)
    db.delete(g)
    db.commit()
