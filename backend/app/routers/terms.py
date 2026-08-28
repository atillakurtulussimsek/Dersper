"""Dönemler.

Her dönem kendi zaman ızgarası, öğretmenleri, dersleri, şubeleri, müfredatı ve
programlarıyla bağımsızdır. Yeni dönem boş açılır; geçmiş dönemden kayıt
aktarmak tanım ekranlarındaki "geçmiş dönemden aktar" ile yapılır.

Silme yumuşaktır: dönem `deleted_at` ile işaretlenir, verisi durur.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import current_user, kurum
from app.models import (
    CurriculumEntry, Day, Institution, Section, Subject, Teacher, Term, Timetable,
)
from app.schemas import TermIn, TermOut

router = APIRouter(prefix="/terms", tags=["dönem"], dependencies=[Depends(current_user)])

SAYILACAKLAR = {
    "ogretmen": Teacher,
    "ders": Subject,
    "sube": Section,
    "program": Timetable,
}


def _getir(db: Session, term_id: int) -> Term:
    donem = db.get(Term, term_id)
    if donem is None or donem.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dönem bulunamadı.")
    return donem


def _cikti(db: Session, donem: Term, inst: Institution) -> TermOut:
    sayilar = {
        ad: db.scalar(
            select(func.count())
            .select_from(model)
            .where(model.term_id == donem.id, model.deleted_at.is_(None))
        )
        or 0
        for ad, model in SAYILACAKLAR.items()
    }
    sayilar["ders_saati"] = (
        db.scalar(select(func.count()).select_from(Day).where(Day.term_id == donem.id))
        or 0
    )
    # Müfredat döneme şube üzerinden bağlıdır.
    sayilar["mufredat"] = (
        db.scalar(
            select(func.count())
            .select_from(CurriculumEntry)
            .join(Section, Section.id == CurriculumEntry.section_id)
            .where(Section.term_id == donem.id, CurriculumEntry.deleted_at.is_(None))
        )
        or 0
    )
    veri = TermOut.model_validate(donem)
    veri.is_active = inst.active_term_id == donem.id
    veri.counts = sayilar
    return veri


@router.get("", response_model=list[TermOut])
def donemler(db: Session = Depends(get_db)) -> list[TermOut]:
    inst = kurum(db)
    kayitlar = db.scalars(
        select(Term).where(Term.deleted_at.is_(None)).order_by(Term.id.desc())
    )
    return [_cikti(db, d, inst) for d in kayitlar]


@router.post("", response_model=TermOut, status_code=status.HTTP_201_CREATED)
def donem_olustur(payload: TermIn, db: Session = Depends(get_db)) -> TermOut:
    """Yeni dönem boş açılır ve hemen aktif dönem olur."""
    inst = kurum(db)
    donem = Term(**payload.model_dump())
    db.add(donem)
    db.flush()
    inst.active_term_id = donem.id
    db.commit()
    db.refresh(donem)
    return _cikti(db, donem, inst)


@router.put("/{term_id}", response_model=TermOut)
def donem_guncelle(
    term_id: int, payload: TermIn, db: Session = Depends(get_db)
) -> TermOut:
    donem = _getir(db, term_id)
    for alan, deger in payload.model_dump().items():
        setattr(donem, alan, deger)
    db.commit()
    db.refresh(donem)
    return _cikti(db, donem, kurum(db))


@router.post("/{term_id}/activate", response_model=TermOut)
def donemi_sec(term_id: int, db: Session = Depends(get_db)) -> TermOut:
    donem = _getir(db, term_id)
    inst = kurum(db)
    inst.active_term_id = donem.id
    db.commit()
    return _cikti(db, donem, inst)


@router.delete("/{term_id}", response_model=list[TermOut])
def donem_sil(term_id: int, db: Session = Depends(get_db)) -> list[TermOut]:
    """Dönemi gizler. Veri silinmez; başka bir dönem varsa ona geçilir."""
    donem = _getir(db, term_id)
    kalan = db.scalar(
        select(func.count())
        .select_from(Term)
        .where(Term.deleted_at.is_(None), Term.id != donem.id)
    )
    if not kalan:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Son dönem silinemez. Önce yeni bir dönem oluşturun.",
        )

    donem.deleted_at = datetime.now(timezone.utc)
    inst = kurum(db)
    if inst.active_term_id == donem.id:
        inst.active_term_id = db.scalar(
            select(Term.id)
            .where(Term.deleted_at.is_(None), Term.id != donem.id)
            .order_by(Term.id.desc())
            .limit(1)
        )
    db.commit()
    return donemler(db)


@router.post("/{term_id}/restore", response_model=TermOut)
def donemi_geri_al(term_id: int, db: Session = Depends(get_db)) -> TermOut:
    """Silinmiş dönemi geri getirir. Hiçbir veri kalıcı olarak silinmediği için
    dönemin tüm tanımları olduğu gibi geri gelir."""
    donem = db.get(Term, term_id)
    if donem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dönem bulunamadı.")
    donem.deleted_at = None
    db.commit()
    db.refresh(donem)
    return _cikti(db, donem, kurum(db))


@router.get("/deleted", response_model=list[TermOut])
def silinmis_donemler(db: Session = Depends(get_db)) -> list[TermOut]:
    inst = kurum(db)
    kayitlar = db.scalars(
        select(Term).where(Term.deleted_at.is_not(None)).order_by(Term.id.desc())
    )
    return [_cikti(db, d, inst) for d in kayitlar]

