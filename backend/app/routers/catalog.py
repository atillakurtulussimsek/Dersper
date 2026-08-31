"""Öğretmen, ders, şube ve ders ataması yönetimi.

Her kayıt aktif döneme aittir; listeler yalnızca o dönemin silinmemiş
kayıtlarını döndürür. Silme yumuşaktır: satır `deleted_at` ile işaretlenir,
veritabanından kaldırılmaz.

Her tanım türü için "geçmiş dönemden aktar" ucu vardır: kaynak dönemdeki
kayıtlar listelenir, seçilenler aktif döneme kopyalanır.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import aktif_donem, current_user
from app.models import (
    Availability, CurriculumEntry, Period, Section, SectionAvailability, Subject,
    Teacher, TeacherAvailability, Term,
)
from app.schemas import (
    AvailabilityCell, AvailabilityCopyIn, AvailabilityCopyOut, AvailabilityUpdate,
    ClosedAvailabilityOut, CurriculumCopyIn, CurriculumCopyOut, CurriculumIn,
    CurriculumOut, ImportIn, ImportOut, SectionIn, SectionOut, SubjectIn, SubjectOut,
    TeacherIn, TeacherOut,
)

router = APIRouter(tags=["tanımlar"], dependencies=[Depends(current_user)])


def _simdi() -> datetime:
    return datetime.now(timezone.utc)


def _getir(db: Session, model, nesne_id: int, ad: str, donem: Term | None = None):
    """Kaydı getirir; yoksa, silinmişse ya da başka döneme aitse 404 verir."""
    nesne = db.get(model, nesne_id)
    if nesne is None or getattr(nesne, "deleted_at", None) is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{ad} bulunamadı.")
    if donem is not None and getattr(nesne, "term_id", donem.id) != donem.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{ad} bu dönemde bulunamadı.")
    return nesne


def _donemin(model, donem: Term):
    """Aktif dönemin silinmemiş kayıtları."""
    return select(model).where(model.term_id == donem.id, model.deleted_at.is_(None))


def _kaynak_donem(db: Session, term_id: int, donem: Term) -> Term:
    kaynak = db.get(Term, term_id)
    # Başka kurumun dönemi, kimliği bilinse bile okunamaz.
    if kaynak is None or kaynak.institution_id != donem.institution_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kaynak dönem bulunamadı.")
    if kaynak.id == donem.id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Kaynak dönem, üzerinde çalıştığınız dönemin kendisi.",
        )
    return kaynak


# --- Öğretmenler ---

def _ogretmen_alanlari(payload: TeacherIn) -> dict:
    """Şemanın gün sınırını (4,5) veritabanının birimine (9 yarım gün) çevirir."""
    alanlar = payload.model_dump(exclude={"max_days"})
    alanlar["max_half_days"] = payload.max_half_days
    return alanlar


@router.get("/teachers", response_model=list[TeacherOut])
def ogretmenler(
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Teacher]:
    return list(db.scalars(_donemin(Teacher, donem).order_by(Teacher.full_name)))


@router.post("/teachers", response_model=TeacherOut, status_code=status.HTTP_201_CREATED)
def ogretmen_ekle(
    payload: TeacherIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Teacher:
    t = Teacher(term_id=donem.id, **_ogretmen_alanlari(payload))
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.put("/teachers/{teacher_id}", response_model=TeacherOut)
def ogretmen_guncelle(
    teacher_id: int,
    payload: TeacherIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Teacher:
    t = _getir(db, Teacher, teacher_id, "Öğretmen", donem)
    for alan, deger in _ogretmen_alanlari(payload).items():
        setattr(t, alan, deger)
    db.commit()
    db.refresh(t)
    return t


@router.delete("/teachers/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def ogretmen_sil(
    teacher_id: int,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
):
    """Yumuşak silme. Müfredatta dersi varsa engellenir."""
    t = _getir(db, Teacher, teacher_id, "Öğretmen", donem)
    kullaniliyor = db.scalar(
        select(CurriculumEntry.id).where(
            CurriculumEntry.teacher_id == t.id, CurriculumEntry.deleted_at.is_(None)
        ).limit(1)
    )
    if kullaniliyor:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bu öğretmenin müfredatta dersi var. Önce derslerini başka öğretmene aktarın.",
        )
    t.deleted_at = _simdi()
    db.commit()


@router.get("/teachers/import/{term_id}", response_model=list[TeacherOut])
def aktarilabilir_ogretmenler(
    term_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Teacher]:
    """Kaynak dönemdeki öğretmenler — aktarım ekranında seçim için."""
    kaynak = _kaynak_donem(db, term_id, donem)
    return list(db.scalars(_donemin(Teacher, kaynak).order_by(Teacher.full_name)))


@router.post("/teachers/import", response_model=ImportOut,
             status_code=status.HTTP_201_CREATED)
def ogretmen_aktar(
    payload: ImportIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> ImportOut:
    kaynak = _kaynak_donem(db, payload.term_id, donem)
    mevcut = {
        t.full_name.casefold()
        for t in db.scalars(_donemin(Teacher, donem))
    }
    secilenler = db.scalars(
        _donemin(Teacher, kaynak).where(Teacher.id.in_(payload.ids))
    )

    sayi, atlanan = 0, []
    for kaynak_t in secilenler:
        if kaynak_t.full_name.casefold() in mevcut:
            atlanan.append(f"{kaynak_t.full_name}: bu dönemde zaten var.")
            continue
        db.add(Teacher(
            term_id=donem.id,
            full_name=kaynak_t.full_name,
            short_code=kaynak_t.short_code,
            branch=kaynak_t.branch,
            max_daily_hours=kaynak_t.max_daily_hours,
            max_half_days=kaynak_t.max_half_days,
            notes=kaynak_t.notes,
            color=kaynak_t.color,
            is_active=kaynak_t.is_active,
        ))
        mevcut.add(kaynak_t.full_name.casefold())
        sayi += 1
    db.commit()
    return ImportOut(imported=sayi, skipped=atlanan)


# --- Müsaitlik (öğretmen ve şube ortak) ---

def _musaitlik_oku(db: Session, model, alan, nesne_id: int) -> list[AvailabilityCell]:
    rows = db.scalars(select(model).where(alan == nesne_id))
    return [AvailabilityCell(period_id=r.period_id, state=r.state) for r in rows]


def _musaitlik_yaz(
    db: Session, model, alan_adi: str, nesne_id: int, payload: AvailabilityUpdate,
    gecerli: set[int],
) -> None:
    """Yalnızca 'uygun' dışındaki hücreler saklanır; kayıt yoksa uygun sayılır."""
    alan = getattr(model, alan_adi)
    for row in db.scalars(select(model).where(alan == nesne_id)):
        db.delete(row)
    db.flush()

    for cell in payload.cells:
        if cell.state is Availability.UYGUN or cell.period_id not in gecerli:
            continue
        db.add(model(**{alan_adi: nesne_id}, period_id=cell.period_id, state=cell.state))
    db.commit()


def _donem_saatleri(db: Session, donem: Term) -> set[int]:
    """Aktif dönemin ders saati kimlikleri; başka dönemin saati yazılamaz."""
    from app.models import Day

    return set(
        db.scalars(
            select(Period.id).join(Day, Day.id == Period.day_id).where(
                Day.term_id == donem.id
            )
        )
    )


@router.get("/availability/closed", response_model=ClosedAvailabilityOut)
def kapali_saatler(
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> ClosedAvailabilityOut:
    """Dönemdeki bütün kapalı saatler, kayıt kimliğine göre gruplanmış.

    Çarşaf görünümü boş bir hücrenin neden boş olduğunu ayırt etmek için
    kullanır: doldurulmamış saat mi, yoksa o şubeye/öğretmene kapalı saat mi.
    Tek uçta toplanır; satır başına ayrı istek atmak çarşafta onlarca çağrı
    demek olurdu.
    """
    donem_saatleri = _donem_saatleri(db, donem)

    def topla(model, alan, sahip) -> dict[int, list[int]]:
        sonuc: dict[int, list[int]] = {}
        rows = db.scalars(
            select(model)
            .join(sahip, sahip.id == alan)
            .where(sahip.term_id == donem.id,
                   sahip.deleted_at.is_(None),
                   model.state == Availability.UYGUN_DEGIL)
        )
        for r in rows:
            if r.period_id in donem_saatleri:
                sonuc.setdefault(getattr(r, alan.key), []).append(r.period_id)
        return sonuc

    return ClosedAvailabilityOut(
        teachers=topla(TeacherAvailability, TeacherAvailability.teacher_id, Teacher),
        sections=topla(SectionAvailability, SectionAvailability.section_id, Section),
    )


@router.get("/teachers/{teacher_id}/availability", response_model=list[AvailabilityCell])
def musaitlik(
    teacher_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[AvailabilityCell]:
    _getir(db, Teacher, teacher_id, "Öğretmen", donem)
    return _musaitlik_oku(db, TeacherAvailability, TeacherAvailability.teacher_id,
                          teacher_id)


@router.put("/teachers/{teacher_id}/availability", response_model=list[AvailabilityCell])
def musaitlik_kaydet(
    teacher_id: int,
    payload: AvailabilityUpdate,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> list[AvailabilityCell]:
    _getir(db, Teacher, teacher_id, "Öğretmen", donem)
    _musaitlik_yaz(db, TeacherAvailability, "teacher_id", teacher_id, payload,
                   _donem_saatleri(db, donem))
    return musaitlik(teacher_id, db, donem)


# --- Dersler ---

@router.get("/subjects", response_model=list[SubjectOut])
def dersler(
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Subject]:
    return list(db.scalars(_donemin(Subject, donem).order_by(Subject.name)))


@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def ders_ekle(
    payload: SubjectIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Subject:
    s = Subject(term_id=donem.id, **payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/subjects/{subject_id}", response_model=SubjectOut)
def ders_guncelle(
    subject_id: int,
    payload: SubjectIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Subject:
    s = _getir(db, Subject, subject_id, "Ders", donem)
    for alan, deger in payload.model_dump().items():
        setattr(s, alan, deger)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def ders_sil(
    subject_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
):
    s = _getir(db, Subject, subject_id, "Ders", donem)
    kullaniliyor = db.scalar(
        select(CurriculumEntry.id).where(
            CurriculumEntry.subject_id == s.id, CurriculumEntry.deleted_at.is_(None)
        ).limit(1)
    )
    if kullaniliyor:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bu ders müfredatta kullanılıyor. Önce ilgili müfredat satırlarını silin.",
        )
    s.deleted_at = _simdi()
    db.commit()


@router.get("/subjects/import/{term_id}", response_model=list[SubjectOut])
def aktarilabilir_dersler(
    term_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Subject]:
    kaynak = _kaynak_donem(db, term_id, donem)
    return list(db.scalars(_donemin(Subject, kaynak).order_by(Subject.name)))


@router.post("/subjects/import", response_model=ImportOut,
             status_code=status.HTTP_201_CREATED)
def ders_aktar(
    payload: ImportIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> ImportOut:
    kaynak = _kaynak_donem(db, payload.term_id, donem)
    mevcut = {s.name.casefold() for s in db.scalars(_donemin(Subject, donem))}
    sayi, atlanan = 0, []
    for k in db.scalars(_donemin(Subject, kaynak).where(Subject.id.in_(payload.ids))):
        if k.name.casefold() in mevcut:
            atlanan.append(f"{k.name}: bu dönemde zaten var.")
            continue
        db.add(Subject(term_id=donem.id, name=k.name, short_code=k.short_code,
                       color=k.color, is_active=k.is_active))
        mevcut.add(k.name.casefold())
        sayi += 1
    db.commit()
    return ImportOut(imported=sayi, skipped=atlanan)


# --- Şubeler ---

@router.get("/sections", response_model=list[SectionOut])
def subeler(
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Section]:
    return list(
        db.scalars(_donemin(Section, donem).order_by(Section.grade_level, Section.name))
    )


@router.post("/sections", response_model=SectionOut, status_code=status.HTTP_201_CREATED)
def sube_ekle(
    payload: SectionIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Section:
    if db.scalar(_donemin(Section, donem).where(Section.name == payload.name)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Bu dönemde bu adda bir şube zaten var."
        )
    s = Section(term_id=donem.id, **payload.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/sections/{section_id}", response_model=SectionOut)
def sube_guncelle(
    section_id: int,
    payload: SectionIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Section:
    s = _getir(db, Section, section_id, "Şube", donem)
    cakisan = db.scalar(
        _donemin(Section, donem).where(Section.name == payload.name, Section.id != s.id)
    )
    if cakisan:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Bu dönemde bu adda bir şube zaten var."
        )
    for alan, deger in payload.model_dump().items():
        setattr(s, alan, deger)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def sube_sil(
    section_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
):
    """Şube ve müfredat satırları yumuşak silinir."""
    s = _getir(db, Section, section_id, "Şube", donem)
    s.deleted_at = _simdi()
    for e in db.scalars(
        select(CurriculumEntry).where(
            CurriculumEntry.section_id == s.id, CurriculumEntry.deleted_at.is_(None)
        )
    ):
        e.deleted_at = s.deleted_at
    db.commit()


@router.get("/sections/{section_id}/availability", response_model=list[AvailabilityCell])
def sube_musaitligi(
    section_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[AvailabilityCell]:
    """Şubenin ders görebileceği saatler. Sabahçı/akşamcı şubeler böyle sınırlanır."""
    _getir(db, Section, section_id, "Şube", donem)
    return _musaitlik_oku(db, SectionAvailability, SectionAvailability.section_id,
                          section_id)


@router.put("/sections/{section_id}/availability", response_model=list[AvailabilityCell])
def sube_musaitligi_kaydet(
    section_id: int,
    payload: AvailabilityUpdate,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> list[AvailabilityCell]:
    _getir(db, Section, section_id, "Şube", donem)
    _musaitlik_yaz(db, SectionAvailability, "section_id", section_id, payload,
                   _donem_saatleri(db, donem))
    return sube_musaitligi(section_id, db, donem)


@router.post("/sections/{section_id}/availability/copy",
             response_model=AvailabilityCopyOut)
def sube_musaitligini_kopyala(
    section_id: int,
    payload: AvailabilityCopyIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> AvailabilityCopyOut:
    """Kaynak şubenin müsaitlik tablosunu hedef şubelere aynen yazar.

    Hedeflerin önceki işaretlemeleri tamamen silinir; birleştirme yapılmaz.
    """
    _getir(db, Section, section_id, "Şube", donem)
    hucreler = _musaitlik_oku(db, SectionAvailability, SectionAvailability.section_id,
                              section_id)

    hedefler = [
        s for s in db.scalars(
            _donemin(Section, donem).where(Section.id.in_(payload.section_ids))
        )
        if s.id != section_id
    ]
    if not hedefler:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Kopyalanacak geçerli bir hedef şube yok."
        )

    gecerli = _donem_saatleri(db, donem)
    for hedef in hedefler:
        _musaitlik_yaz(db, SectionAvailability, "section_id", hedef.id,
                       AvailabilityUpdate(cells=hucreler), gecerli)

    return AvailabilityCopyOut(
        copied_to=sorted(h.name for h in hedefler), cells=len(hucreler)
    )


@router.get("/sections/import/{term_id}", response_model=list[SectionOut])
def aktarilabilir_subeler(
    term_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Section]:
    kaynak = _kaynak_donem(db, term_id, donem)
    return list(
        db.scalars(_donemin(Section, kaynak).order_by(Section.grade_level, Section.name))
    )


@router.post("/sections/import", response_model=ImportOut,
             status_code=status.HTTP_201_CREATED)
def sube_aktar(
    payload: ImportIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> ImportOut:
    kaynak = _kaynak_donem(db, payload.term_id, donem)
    mevcut = {s.name.casefold() for s in db.scalars(_donemin(Section, donem))}
    sayi, atlanan = 0, []
    for k in db.scalars(_donemin(Section, kaynak).where(Section.id.in_(payload.ids))):
        if k.name.casefold() in mevcut:
            atlanan.append(f"{k.name}: bu dönemde zaten var.")
            continue
        db.add(Section(term_id=donem.id, name=k.name, grade_level=k.grade_level,
                       student_count=k.student_count, is_active=k.is_active))
        mevcut.add(k.name.casefold())
        sayi += 1
    db.commit()
    return ImportOut(imported=sayi, skipped=atlanan)


# --- Müfredat ---

def _atama_getir(db: Session, entry_id: int, donem: Term) -> CurriculumEntry:
    """Ders atamasını getirir; başka döneme (dolayısıyla kuruma) aitse 404.

    Atamanın kendi `term_id`si yoktur; dönem bağı şube üzerinden kurulur.
    """
    e = db.get(CurriculumEntry, entry_id)
    if e is None or e.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ders ataması bulunamadı.")
    sube = db.get(Section, e.section_id)
    if sube is None or sube.term_id != donem.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ders ataması bulunamadı.")
    return e


def _mufredat_sorgusu(donem: Term):
    return (
        select(CurriculumEntry)
        .join(Section, Section.id == CurriculumEntry.section_id)
        .where(Section.term_id == donem.id, CurriculumEntry.deleted_at.is_(None))
        .options(
            selectinload(CurriculumEntry.subject),
            selectinload(CurriculumEntry.teacher),
            selectinload(CurriculumEntry.section),
        )
    )


@router.get("/curriculum", response_model=list[CurriculumOut])
def mufredat(
    section_id: int | None = None,
    teacher_id: int | None = None,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> list[CurriculumEntry]:
    """Ders atamaları. Şubeye ya da öğretmene göre süzülebilir.

    Öğretmen süzgeci, atamalara öğretmen tarafından bakmak için: bir
    öğretmenin hangi şubelerde neyi okuttuğu tek listede görünür.
    """
    sorgu = _mufredat_sorgusu(donem)
    if section_id is not None:
        sorgu = sorgu.where(CurriculumEntry.section_id == section_id)
    if teacher_id is not None:
        sorgu = sorgu.where(CurriculumEntry.teacher_id == teacher_id)
    return list(db.scalars(
        sorgu.join(Subject, Subject.id == CurriculumEntry.subject_id)
        .order_by(CurriculumEntry.section_id, Subject.name, CurriculumEntry.id)
    ))


def _atama_var_mi(db: Session, section_id: int, subject_id: int, teacher_id: int,
                  haric: int | None = None) -> bool:
    """Aynı şube–ders–öğretmen üçlüsü zaten var mı?

    Bir derse birden fazla öğretmen girebilir (örneğin İngilizce'nin 2 saati bir,
    2 saati başka öğretmende); bu yüzden şube–ders çifti tek başına engel değildir.
    Engellenen, birebir aynı üçlünün tekrarıdır.
    """
    sorgu = select(CurriculumEntry.id).where(
        CurriculumEntry.section_id == section_id,
        CurriculumEntry.subject_id == subject_id,
        CurriculumEntry.teacher_id == teacher_id,
        CurriculumEntry.deleted_at.is_(None),
    )
    if haric is not None:
        sorgu = sorgu.where(CurriculumEntry.id != haric)
    return db.scalar(sorgu.limit(1)) is not None


@router.post("/curriculum", response_model=CurriculumOut,
             status_code=status.HTTP_201_CREATED)
def mufredat_ekle(
    payload: CurriculumIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> CurriculumEntry:
    _getir(db, Section, payload.section_id, "Şube", donem)
    _getir(db, Subject, payload.subject_id, "Ders", donem)
    _getir(db, Teacher, payload.teacher_id, "Öğretmen", donem)
    if _atama_var_mi(db, payload.section_id, payload.subject_id, payload.teacher_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bu şubede bu ders bu öğretmenle zaten tanımlı. "
            "Aynı dersi başka bir öğretmenle ekleyebilirsiniz.",
        )

    e = CurriculumEntry(**payload.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.post("/curriculum/copy", response_model=CurriculumCopyOut,
             status_code=status.HTTP_201_CREATED)
def mufredat_kopyala(
    payload: CurriculumCopyIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> CurriculumCopyOut:
    """Satırları hedef şubelere kopyalar; yalnızca şube değişir, gerisi aynı kalır.

    Hedef şubede o ders zaten varsa satır atlanır ve gerekçesi bildirilir.
    """
    kaynaklar = list(db.scalars(
        _mufredat_sorgusu(donem).where(CurriculumEntry.id.in_(payload.entry_ids))
    ))
    if not kaynaklar:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kopyalanacak satır bulunamadı.")

    hedefler = list(db.scalars(
        _donemin(Section, donem).where(Section.id.in_(payload.section_ids))
    ))
    if not hedefler:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hedef şube bulunamadı.")

    mevcut = {
        (e.section_id, e.subject_id, e.teacher_id)
        for e in db.scalars(_mufredat_sorgusu(donem))
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
            if (hedef.id, kaynak.subject_id, kaynak.teacher_id) in mevcut:
                atlananlar.append(
                    f"{hedef.name} · {kaynak.subject.name}: bu şubede "
                    f"{kaynak.teacher.full_name} ile zaten tanımlı."
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
            mevcut.add((hedef.id, kaynak.subject_id, kaynak.teacher_id))

    db.commit()
    for k in yeniler:
        db.refresh(k)
    return CurriculumCopyOut(
        created=[CurriculumOut.model_validate(k) for k in yeniler],
        skipped=atlananlar,
    )


@router.get("/curriculum/import/{term_id}", response_model=list[CurriculumOut])
def aktarilabilir_mufredat(
    term_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[CurriculumEntry]:
    kaynak = _kaynak_donem(db, term_id, donem)
    return list(db.scalars(_mufredat_sorgusu(kaynak).order_by(CurriculumEntry.section_id)))


@router.post("/curriculum/import", response_model=ImportOut,
             status_code=status.HTTP_201_CREATED)
def mufredat_aktar(
    payload: ImportIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> ImportOut:
    """Müfredat satırlarını aktarır. Şube, ders ve öğretmen adlarına göre bu
    dönemdeki karşılıkları bulunur; karşılığı olmayan satır atlanır."""
    kaynak = _kaynak_donem(db, payload.term_id, donem)

    def ad_haritasi(model):
        return {
            n.name.casefold() if hasattr(n, "name") else n.full_name.casefold(): n.id
            for n in db.scalars(_donemin(model, donem))
        }

    subeler_ = ad_haritasi(Section)
    dersler_ = ad_haritasi(Subject)
    ogretmenler_ = ad_haritasi(Teacher)
    mevcut = {
        (e.section_id, e.subject_id, e.teacher_id)
        for e in db.scalars(_mufredat_sorgusu(donem))
    }

    sayi, atlanan = 0, []
    for k in db.scalars(
        _mufredat_sorgusu(kaynak).where(CurriculumEntry.id.in_(payload.ids))
    ):
        etiket = f"{k.section.name} · {k.subject.name}"
        sube_id = subeler_.get(k.section.name.casefold())
        ders_id = dersler_.get(k.subject.name.casefold())
        ogretmen_id = ogretmenler_.get(k.teacher.full_name.casefold())

        eksik = [
            ad for ad, deger in (
                (f"{k.section.name} şubesi", sube_id),
                (f"{k.subject.name} dersi", ders_id),
                (f"{k.teacher.full_name} öğretmeni", ogretmen_id),
            ) if deger is None
        ]
        if eksik:
            atlanan.append(f"{etiket}: bu dönemde {', '.join(eksik)} tanımlı değil.")
            continue
        if (sube_id, ders_id, ogretmen_id) in mevcut:
            atlanan.append(
                f"{etiket}: bu şubede {k.teacher.full_name} ile zaten tanımlı."
            )
            continue

        db.add(CurriculumEntry(
            section_id=sube_id, subject_id=ders_id, teacher_id=ogretmen_id,
            weekly_hours=k.weekly_hours, block_pattern=k.block_pattern,
            max_per_day=k.max_per_day,
        ))
        mevcut.add((sube_id, ders_id, ogretmen_id))
        sayi += 1
    db.commit()
    return ImportOut(imported=sayi, skipped=atlanan)


@router.put("/curriculum/{entry_id}", response_model=CurriculumOut)
def mufredat_guncelle(
    entry_id: int,
    payload: CurriculumIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> CurriculumEntry:
    e = _atama_getir(db, entry_id, donem)
    _getir(db, Section, payload.section_id, "Şube", donem)
    _getir(db, Subject, payload.subject_id, "Ders", donem)
    _getir(db, Teacher, payload.teacher_id, "Öğretmen", donem)
    if _atama_var_mi(db, payload.section_id, payload.subject_id, payload.teacher_id,
                     haric=e.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bu şubede bu ders bu öğretmenle zaten tanımlı.",
        )
    for alan, deger in payload.model_dump().items():
        setattr(e, alan, deger)
    db.commit()
    db.refresh(e)
    return e


@router.delete("/curriculum/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def mufredat_sil(
    entry_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
):
    e = _atama_getir(db, entry_id, donem)
    e.deleted_at = _simdi()
    db.commit()
