"""Öğretmen, ders, şube ve müfredat yönetimi."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import current_user
from app.models import (
    Availability, CurriculumEntry, Period, Section, SectionAvailability, Subject,
    Teacher, TeacherAvailability,
)
from app.schemas import (
    AvailabilityCell, AvailabilityCopyIn, AvailabilityCopyOut, AvailabilityUpdate,
    CurriculumCopyIn, CurriculumCopyOut, CurriculumIn, CurriculumOut, SectionIn,
    SectionOut, SubjectIn, SubjectOut, TeacherIn, TeacherOut,
)

router = APIRouter(tags=["tanımlar"], dependencies=[Depends(current_user)])


def _getir(db: Session, model, nesne_id: int, ad: str):
    nesne = db.get(model, nesne_id)
    if nesne is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{ad} bulunamadı.")
    return nesne


# --- Öğretmenler ---

@router.get("/teachers", response_model=list[TeacherOut])
def ogretmenler(db: Session = Depends(get_db)) -> list[Teacher]:
    return list(db.scalars(select(Teacher).order_by(Teacher.full_name)))


@router.post("/teachers", response_model=TeacherOut, status_code=status.HTTP_201_CREATED)
def ogretmen_ekle(payload: TeacherIn, db: Session = Depends(get_db)) -> Teacher:
    t = Teacher(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/teachers/{teacher_id}", response_model=TeacherOut)
def ogretmen_guncelle(
    teacher_id: int, payload: TeacherIn, db: Session = Depends(get_db)
) -> Teacher:
    t = _getir(db, Teacher, teacher_id, "Öğretmen")
    for alan, deger in payload.model_dump().items():
        setattr(t, alan, deger)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/teachers/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def ogretmen_sil(teacher_id: int, db: Session = Depends(get_db)):
    t = _getir(db, Teacher, teacher_id, "Öğretmen")
    db.delete(t)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bu öğretmenin müfredatta dersi var. Önce derslerini başka öğretmene aktarın.",
        )


def _musaitlik_oku(db: Session, model, alan, nesne_id: int) -> list[AvailabilityCell]:
    rows = db.scalars(select(model).where(alan == nesne_id))
    return [AvailabilityCell(period_id=r.period_id, state=r.state) for r in rows]


def _musaitlik_yaz(
    db: Session, model, alan_adi: str, nesne_id: int, payload: AvailabilityUpdate
) -> None:
    """Yalnızca 'uygun' dışındaki hücreler saklanır; kayıt yoksa uygun sayılır."""
    gecerli = set(db.scalars(select(Period.id)))
    alan = getattr(model, alan_adi)

    for row in db.scalars(select(model).where(alan == nesne_id)):
        db.delete(row)
    db.flush()

    for cell in payload.cells:
        if cell.state is Availability.UYGUN or cell.period_id not in gecerli:
            continue
        db.add(model(**{alan_adi: nesne_id}, period_id=cell.period_id, state=cell.state))
    db.commit()


@router.get("/teachers/{teacher_id}/availability", response_model=list[AvailabilityCell])
def musaitlik(teacher_id: int, db: Session = Depends(get_db)) -> list[AvailabilityCell]:
    _getir(db, Teacher, teacher_id, "Öğretmen")
    return _musaitlik_oku(db, TeacherAvailability, TeacherAvailability.teacher_id, teacher_id)


@router.put("/teachers/{teacher_id}/availability", response_model=list[AvailabilityCell])
def musaitlik_kaydet(
    teacher_id: int, payload: AvailabilityUpdate, db: Session = Depends(get_db)
) -> list[AvailabilityCell]:
    _getir(db, Teacher, teacher_id, "Öğretmen")
    _musaitlik_yaz(db, TeacherAvailability, "teacher_id", teacher_id, payload)
    return musaitlik(teacher_id, db)


# --- Dersler ---

@router.get("/subjects", response_model=list[SubjectOut])
def dersler(db: Session = Depends(get_db)) -> list[Subject]:
    return list(db.scalars(select(Subject).order_by(Subject.name)))


@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def ders_ekle(payload: SubjectIn, db: Session = Depends(get_db)) -> Subject:
    s = Subject(**payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/subjects/{subject_id}", response_model=SubjectOut)
def ders_guncelle(
    subject_id: int, payload: SubjectIn, db: Session = Depends(get_db)
) -> Subject:
    s = _getir(db, Subject, subject_id, "Ders")
    for alan, deger in payload.model_dump().items():
        setattr(s, alan, deger)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def ders_sil(subject_id: int, db: Session = Depends(get_db)):
    db.delete(_getir(db, Subject, subject_id, "Ders"))
    db.commit()


# --- Şubeler ---

@router.get("/sections", response_model=list[SectionOut])
def subeler(db: Session = Depends(get_db)) -> list[Section]:
    return list(db.scalars(select(Section).order_by(Section.grade_level, Section.name)))


@router.post("/sections", response_model=SectionOut, status_code=status.HTTP_201_CREATED)
def sube_ekle(payload: SectionIn, db: Session = Depends(get_db)) -> Section:
    if db.scalar(select(Section).where(Section.name == payload.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu adda bir şube zaten var.")
    s = Section(**payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/sections/{section_id}", response_model=SectionOut)
def sube_guncelle(
    section_id: int, payload: SectionIn, db: Session = Depends(get_db)
) -> Section:
    s = _getir(db, Section, section_id, "Şube")
    for alan, deger in payload.model_dump().items():
        setattr(s, alan, deger)
    db.commit()
    db.refresh(s)
    return s


@router.get("/sections/{section_id}/availability", response_model=list[AvailabilityCell])
def sube_musaitligi(section_id: int, db: Session = Depends(get_db)) -> list[AvailabilityCell]:
    """Şubenin ders görebileceği saatler. Sabahçı/akşamcı şubeler böyle sınırlanır."""
    _getir(db, Section, section_id, "Şube")
    return _musaitlik_oku(db, SectionAvailability, SectionAvailability.section_id, section_id)


@router.put("/sections/{section_id}/availability", response_model=list[AvailabilityCell])
def sube_musaitligi_kaydet(
    section_id: int, payload: AvailabilityUpdate, db: Session = Depends(get_db)
) -> list[AvailabilityCell]:
    _getir(db, Section, section_id, "Şube")
    _musaitlik_yaz(db, SectionAvailability, "section_id", section_id, payload)
    return sube_musaitligi(section_id, db)


@router.post("/sections/{section_id}/availability/copy",
             response_model=AvailabilityCopyOut)
def sube_musaitligini_kopyala(
    section_id: int, payload: AvailabilityCopyIn, db: Session = Depends(get_db)
) -> AvailabilityCopyOut:
    """Kaynak şubenin müsaitlik tablosunu hedef şubelere aynen yazar.

    Hedeflerin önceki işaretlemeleri tamamen silinir; birleştirme yapılmaz.
    """
    _getir(db, Section, section_id, "Şube")

    kaynak = list(db.scalars(
        select(SectionAvailability).where(SectionAvailability.section_id == section_id)
    ))
    hucreler = [
        AvailabilityCell(period_id=r.period_id, state=r.state) for r in kaynak
    ]

    hedefler = [
        s for s in db.scalars(select(Section).where(Section.id.in_(payload.section_ids)))
        if s.id != section_id
    ]
    if not hedefler:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Kopyalanacak geçerli bir hedef şube yok."
        )

    for hedef in hedefler:
        _musaitlik_yaz(
            db, SectionAvailability, "section_id", hedef.id,
            AvailabilityUpdate(cells=hucreler),
        )

    return AvailabilityCopyOut(
        copied_to=sorted(h.name for h in hedefler), cells=len(hucreler)
    )


@router.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def sube_sil(section_id: int, db: Session = Depends(get_db)):
    db.delete(_getir(db, Section, section_id, "Şube"))
    db.commit()


# --- Müfredat ---

@router.get("/curriculum", response_model=list[CurriculumOut])
def mufredat(
    section_id: int | None = None, db: Session = Depends(get_db)
) -> list[CurriculumEntry]:
    sorgu = select(CurriculumEntry).options(
        selectinload(CurriculumEntry.subject), selectinload(CurriculumEntry.teacher)
    )
    if section_id is not None:
        sorgu = sorgu.where(CurriculumEntry.section_id == section_id)
    return list(db.scalars(sorgu.order_by(CurriculumEntry.section_id)))


@router.post("/curriculum", response_model=CurriculumOut,
             status_code=status.HTTP_201_CREATED)
def mufredat_ekle(payload: CurriculumIn, db: Session = Depends(get_db)) -> CurriculumEntry:
    _getir(db, Section, payload.section_id, "Şube")
    _getir(db, Subject, payload.subject_id, "Ders")
    _getir(db, Teacher, payload.teacher_id, "Öğretmen")
    e = CurriculumEntry(**payload.model_dump())
    db.add(e)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Bu şubede bu ders zaten tanımlı."
        )
    db.refresh(e)
    return e


@router.post("/curriculum/copy", response_model=CurriculumCopyOut,
             status_code=status.HTTP_201_CREATED)
def mufredat_kopyala(
    payload: CurriculumCopyIn, db: Session = Depends(get_db)
) -> CurriculumCopyOut:
    """Satırları hedef şubelere kopyalar; yalnızca şube değişir, gerisi aynı kalır.

    Hedef şubede o ders zaten varsa satır atlanır ve gerekçesi bildirilir.
    """
    kaynaklar = list(db.scalars(
        select(CurriculumEntry)
        .options(selectinload(CurriculumEntry.subject))
        .where(CurriculumEntry.id.in_(payload.entry_ids))
    ))
    if not kaynaklar:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kopyalanacak satır bulunamadı.")

    hedefler = list(db.scalars(
        select(Section).where(Section.id.in_(payload.section_ids))
    ))
    if not hedefler:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hedef şube bulunamadı.")

    # Hangi şubede hangi dersin zaten tanımlı olduğu.
    mevcut = {
        (sid, subid)
        for sid, subid in db.execute(
            select(CurriculumEntry.section_id, CurriculumEntry.subject_id)
        )
    }

    yeniler: list[CurriculumEntry] = []
    atlananlar: list[str] = []

    for hedef in sorted(hedefler, key=lambda s: s.name):
        for kaynak in kaynaklar:
            if hedef.id == kaynak.section_id:
                atlananlar.append(
                    f"{hedef.name} · {kaynak.subject.name}: kaynak şubenin kendisi."
                )
                continue
            if (hedef.id, kaynak.subject_id) in mevcut:
                atlananlar.append(
                    f"{hedef.name} · {kaynak.subject.name}: bu şubede zaten tanımlı."
                )
                continue
            kopya = CurriculumEntry(
                section_id=hedef.id,
                subject_id=kaynak.subject_id,
                teacher_id=kaynak.teacher_id,
                weekly_hours=kaynak.weekly_hours,
                block_pattern=kaynak.block_pattern,
                max_per_day=kaynak.max_per_day,
            )
            db.add(kopya)
            yeniler.append(kopya)
            mevcut.add((hedef.id, kaynak.subject_id))

    db.commit()
    for k in yeniler:
        db.refresh(k)
    return CurriculumCopyOut(
        created=[CurriculumOut.model_validate(k) for k in yeniler],
        skipped=atlananlar,
    )


@router.put("/curriculum/{entry_id}", response_model=CurriculumOut)
def mufredat_guncelle(
    entry_id: int, payload: CurriculumIn, db: Session = Depends(get_db)
) -> CurriculumEntry:
    e = _getir(db, CurriculumEntry, entry_id, "Müfredat satırı")
    for alan, deger in payload.model_dump().items():
        setattr(e, alan, deger)
    db.commit()
    db.refresh(e)
    return e


@router.delete("/curriculum/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def mufredat_sil(entry_id: int, db: Session = Depends(get_db)):
    db.delete(_getir(db, CurriculumEntry, entry_id, "Müfredat satırı"))
    db.commit()
