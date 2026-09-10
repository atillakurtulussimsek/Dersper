"""Şube birleştirme kuralları.

"9-A ile 9-B, Cumartesi, tam 4 saat": hangi dersin ortak okutulacağını
çözücü seçer (bkz. models.SectionMergeRule ve solver.loader.birlesme_kurallari).
Bu uç yalnızca kuralı ve eşleşebilecek ders çiftlerini yönetir.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import aktif_donem, current_user
from app.models import (
    CurriculumEntry, Day, Section, SectionMergeRule, Term,
)
from app.schemas import MergePairOut, MergePreviewOut, MergeRuleIn, MergeRuleOut

router = APIRouter(prefix="/merge-rules", tags=["şube birleştirme"],
                   dependencies=[Depends(current_user)])


def _sube(db: Session, section_id: int, donem: Term) -> Section:
    s = db.get(Section, section_id)
    if s is None or s.deleted_at is not None or s.term_id != donem.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Şube bulunamadı.")
    return s


def eslesen_ciftler(db: Session, a_id: int, b_id: int) -> list[MergePairOut]:
    """İki şubede aynı öğretmenin verdiği aynı dersler. Elle birleştirilmiş
    (birden fazla şubeli) satırlar dışarıda: onlar zaten ortak."""
    satirlar = db.scalars(
        select(CurriculumEntry)
        .options(selectinload(CurriculumEntry.subject),
                 selectinload(CurriculumEntry.teacher))
        .where(CurriculumEntry.section_id.in_([a_id, b_id]),
               CurriculumEntry.deleted_at.is_(None))
    ).all()
    a = {(e.teacher_id, e.subject_id): e for e in satirlar
         if e.section_id == a_id and not e.extra_sections}
    b = {(e.teacher_id, e.subject_id): e for e in satirlar
         if e.section_id == b_id and not e.extra_sections}
    ciftler = []
    for anahtar in sorted(set(a) & set(b), key=lambda k: a[k].subject.name):
        ea, eb = a[anahtar], b[anahtar]
        ciftler.append(MergePairOut(
            subject_name=ea.subject.name, teacher_name=ea.teacher.full_name,
            hours_a=ea.weekly_hours, hours_b=eb.weekly_hours,
            max_hours=min(ea.weekly_hours, eb.weekly_hours),
        ))
    return ciftler


def _gun_adlari(db: Session, donem: Term) -> dict[int, str]:
    return {d.index: d.name for d in db.scalars(
        select(Day).where(Day.term_id == donem.id, Day.is_active.is_(True))
    )}


def _cikti(db: Session, k: SectionMergeRule, donem: Term) -> MergeRuleOut:
    ciftler = eslesen_ciftler(db, k.section_a_id, k.section_b_id)
    gunler = _gun_adlari(db, donem)
    return MergeRuleOut(
        id=k.id, section_a_id=k.section_a_id, section_b_id=k.section_b_id,
        section_a_name=k.section_a.name, section_b_name=k.section_b.name,
        hours=k.hours, day_indexes=list(k.day_indexes or []),
        day_names=[gunler[i] for i in k.day_indexes if i in gunler],
        pairs=ciftler, max_hours=sum(c.max_hours for c in ciftler),
    )


def _dogrula(db: Session, payload: MergeRuleIn, donem: Term) -> tuple[int, int]:
    a, b = sorted((payload.section_a_id, payload.section_b_id))
    _sube(db, a, donem)
    _sube(db, b, donem)
    gunler = _gun_adlari(db, donem)
    bilinmeyen = [i for i in payload.day_indexes if i not in gunler]
    if bilinmeyen:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Seçilen günlerden bazıları ızgarada yok ya da kapalı.")
    ciftler = eslesen_ciftler(db, a, b)
    en_fazla = sum(c.max_hours for c in ciftler)
    if not ciftler:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Bu iki şubede aynı öğretmenin verdiği ortak bir ders yok; "
            "birleştirilecek ders bulunamıyor.",
        )
    if payload.hours > en_fazla:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Bu iki şubede en çok {en_fazla} saat ortak okutulabilir "
            f"({', '.join(f'{c.subject_name} {c.max_hours}' for c in ciftler)}).",
        )
    return a, b


@router.get("", response_model=list[MergeRuleOut])
def kurallar(db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)):
    return [_cikti(db, k, donem) for k in db.scalars(
        select(SectionMergeRule)
        .options(selectinload(SectionMergeRule.section_a),
                 selectinload(SectionMergeRule.section_b))
        .where(SectionMergeRule.term_id == donem.id)
        .order_by(SectionMergeRule.id)
    )]


@router.get("/preview", response_model=MergePreviewOut)
def on_izleme(
    section_a_id: int, section_b_id: int,
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem),
):
    """Kural yazılmadan önce: bu iki şubede hangi dersler eşleşir, en çok kaç saat?"""
    _sube(db, section_a_id, donem)
    _sube(db, section_b_id, donem)
    ciftler = eslesen_ciftler(db, section_a_id, section_b_id)
    return MergePreviewOut(pairs=ciftler, max_hours=sum(c.max_hours for c in ciftler))


@router.post("", response_model=MergeRuleOut, status_code=status.HTTP_201_CREATED)
def kural_ekle(
    payload: MergeRuleIn,
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem),
):
    a, b = _dogrula(db, payload, donem)
    if db.scalar(select(SectionMergeRule).where(
        SectionMergeRule.term_id == donem.id,
        SectionMergeRule.section_a_id == a, SectionMergeRule.section_b_id == b,
    )):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Bu iki şube için zaten bir birleştirme kuralı var.")
    k = SectionMergeRule(term_id=donem.id, section_a_id=a, section_b_id=b,
                         hours=payload.hours, day_indexes=payload.day_indexes)
    db.add(k)
    db.commit()
    db.refresh(k)
    return _cikti(db, k, donem)


@router.put("/{rule_id}", response_model=MergeRuleOut)
def kural_guncelle(
    rule_id: int, payload: MergeRuleIn,
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem),
):
    k = db.get(SectionMergeRule, rule_id)
    if k is None or k.term_id != donem.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kural bulunamadı.")
    a, b = _dogrula(db, payload, donem)
    cakisan = db.scalar(select(SectionMergeRule).where(
        SectionMergeRule.term_id == donem.id, SectionMergeRule.id != k.id,
        SectionMergeRule.section_a_id == a, SectionMergeRule.section_b_id == b,
    ))
    if cakisan:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Bu iki şube için zaten bir birleştirme kuralı var.")
    k.section_a_id, k.section_b_id = a, b
    k.hours, k.day_indexes = payload.hours, payload.day_indexes
    db.commit()
    db.refresh(k)
    return _cikti(db, k, donem)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def kural_sil(
    rule_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem),
):
    k = db.get(SectionMergeRule, rule_id)
    if k is None or k.term_id != donem.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kural bulunamadı.")
    db.delete(k)
    db.commit()
