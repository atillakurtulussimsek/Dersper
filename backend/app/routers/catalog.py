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
    AvailabilityCell, AvailabilityUpdate, CurriculumIn, CurriculumOut, SectionIn,
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
    if payload.block_size > payload.weekly_hours:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Blok boyu haftalık ders saatinden büyük olamaz.",
        )
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
