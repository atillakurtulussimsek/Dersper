"""Zaman ızgarası: günler ve ders saatleri. Ders saati sayısı güne göre değişir.

Izgara döneme aittir; her dönem kendi zil düzenini tanımlar.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import aktif_donem, current_user
from app.models import (
    Assignment, Day, Period, SectionAvailability, TeacherAvailability, Term,
    Timetable,
)
from app.schemas import DayIn, DayOut, PeriodIn

router = APIRouter(prefix="/timegrid", tags=["zaman ızgarası"],
                   dependencies=[Depends(current_user)])


def _gunleri_getir(db: Session, donem: Term) -> list[Day]:
    return list(
        db.scalars(
            select(Day)
            .options(selectinload(Day.periods))
            .where(Day.term_id == donem.id)
            .order_by(Day.index)
        )
    )


def _bagli_kayitlari_sil(db: Session, saatler: list[Period]) -> None:
    """Verilen ders saatlerine bağlı müsaitlik işaretlerini ve yerleşimleri siler.

    Ders saatinin kendisini silmez; çağıran ya saati tek tek siler ya da günü
    silip ORM'in art arda silmesine bırakır. Veritabanı seviyesindeki art arda
    silmeye güvenmiyoruz: SQLite yabancı anahtarları varsayılan olarak zorlamaz.
    """
    kimlikler = [p.id for p in saatler]
    if not kimlikler:
        return
    for model in (TeacherAvailability, SectionAvailability, Assignment):
        for satir in db.scalars(select(model).where(model.period_id.in_(kimlikler))):
            db.delete(satir)
    db.flush()


def _saatleri_sil(db: Session, saatler: list[Period]) -> None:
    """Ders saatlerini ve onlara bağlı kayıtları siler."""
    _bagli_kayitlari_sil(db, saatler)
    for p in saatler:
        db.delete(p)
    db.flush()


def _saatleri_esitle(db: Session, gun: Day, gelen: list[PeriodIn]) -> None:
    """Günün ders saatlerini gelen listeye göre yerinde günceller.

    Eşleştirme sıraya (`index`) göre yapılır ve var olan kayıtlar korunur; bu
    sayede ders saati kimlikleri sabit kalır ve onlara bağlı öğretmen/şube
    müsaitlik işaretleri hayatta kalır. Baştan silip yeniden yaratmak, adı ya
    da saati bile değişmemiş satırların müsaitliğini de silerdi.
    """
    mevcut = {p.index: p for p in gun.periods}
    gelen_indexler = {p.index for p in gelen}

    _saatleri_sil(db, [p for i, p in mevcut.items() if i not in gelen_indexler])

    for p in gelen:
        var_olan = mevcut.get(p.index)
        if var_olan is None:
            db.add(Period(day_id=gun.id, **p.model_dump()))
            continue
        var_olan.name = p.name
        var_olan.start_time = p.start_time
        var_olan.end_time = p.end_time
        var_olan.is_break = p.is_break


def _kaynak_donem(db: Session, term_id: int, donem: Term) -> Term:
    """Aynı kuruma ait, farklı bir dönem."""
    kaynak = db.get(Term, term_id)
    if (kaynak is None or kaynak.id == donem.id
            or kaynak.institution_id != donem.institution_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kaynak dönem bulunamadı.")
    return kaynak


def _yerlesim_var_mi(db: Session, donem: Term) -> bool:
    """Dönemde yerleşmiş ders var mı.

    Silinmiş programlar sayılmaz: silme yumuşak olduğu için yerleşimleri
    veritabanında durur, ama kullanıcı o programı listede görmez. Sayılırsa
    "programı silin" denip duran, çıkışı olmayan bir hataya dönüşür.
    """
    return db.scalar(
        select(Assignment.id)
        .join(Timetable, Timetable.id == Assignment.timetable_id)
        .where(Timetable.term_id == donem.id, Timetable.deleted_at.is_(None))
        .limit(1)
    ) is not None


@router.get("", response_model=list[DayOut])
def izgarayi_getir(
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Day]:
    return _gunleri_getir(db, donem)


@router.put("", response_model=list[DayOut])
def izgarayi_kaydet(
    payload: list[DayIn],
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> list[Day]:
    """Izgarayı bütünüyle değiştirir. Yerleşmiş program varsa reddedilir."""
    if _yerlesim_var_mi(db, donem):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Yerleşmiş bir ders programı varken zaman ızgarası değiştirilemez. "
            "Önce programı silin.",
        )

    mevcut = {d.index: d for d in _gunleri_getir(db, donem)}
    gelen_indexler = {d.index for d in payload}

    # Listeden tamamen çıkarılan günler. Günü pasife almak silmek değildir:
    # pasif günün ders saatleri ve müsaitlik işaretleri olduğu gibi durur,
    # gün yeniden açıldığında geri gelir.
    for gun in mevcut.values():
        if gun.index not in gelen_indexler:
            _bagli_kayitlari_sil(db, list(gun.periods))
            db.delete(gun)      # ders saatlerini ORM art arda siler
    db.flush()

    for gelen in payload:
        gun = mevcut.get(gelen.index)
        if gun is None:
            gun = Day(term_id=donem.id, index=gelen.index, name=gelen.name,
                      is_active=gelen.is_active)
            db.add(gun)
            db.flush()
        else:
            gun.name, gun.is_active = gelen.name, gelen.is_active
        _saatleri_esitle(db, gun, gelen.periods)

    db.commit()
    # Oturum commit'te nesneleri geçersiz kılmıyor (expire_on_commit=False);
    # yeniden okumadan önce elle geçersiz kılınmazsa eski ders saatleri döner.
    db.expire_all()
    return _gunleri_getir(db, donem)


@router.post("/days/{day_id}/periods", response_model=DayOut,
             status_code=status.HTTP_201_CREATED)
def ders_saati_ekle(
    day_id: int,
    payload: PeriodIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Day:
    gun = db.get(Day, day_id)
    if gun is None or gun.term_id != donem.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gün bulunamadı.")
    db.add(Period(day_id=day_id, **payload.model_dump()))
    db.commit()
    db.expire_all()
    return db.get(Day, day_id)


@router.get("/import/{term_id}", response_model=list[DayOut])
def aktarilabilir_izgara(
    term_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Day]:
    """Kaynak dönemin zaman ızgarası — aktarmadan önce göstermek için."""
    kaynak = _kaynak_donem(db, term_id, donem)
    return _gunleri_getir(db, kaynak)


@router.post("/import/{term_id}", response_model=list[DayOut],
             status_code=status.HTTP_201_CREATED)
def izgarayi_aktar(
    term_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Day]:
    """Kaynak dönemin ızgarasını bu döneme kopyalar; mevcut ızgaranın yerine geçer."""
    kaynak = _kaynak_donem(db, term_id, donem)
    if _yerlesim_var_mi(db, donem):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Yerleşmiş bir ders programı varken zaman ızgarası değiştirilemez. "
            "Önce programı silin.",
        )

    # Aktarım ızgaranın tamamını kaynak dönemden alır; eski saatler ve onlara
    # bağlı müsaitlik işaretleri bu durumda gerçekten geçersizleşir.
    for gun in _gunleri_getir(db, donem):
        _bagli_kayitlari_sil(db, list(gun.periods))
        db.delete(gun)          # ders saatlerini ORM art arda siler
    db.flush()

    for kaynak_gun in _gunleri_getir(db, kaynak):
        gun = Day(term_id=donem.id, index=kaynak_gun.index, name=kaynak_gun.name,
                  is_active=kaynak_gun.is_active)
        db.add(gun)
        db.flush()
        for p in sorted(kaynak_gun.periods, key=lambda x: x.index):
            db.add(Period(day_id=gun.id, index=p.index, name=p.name,
                          start_time=p.start_time, end_time=p.end_time,
                          is_break=p.is_break))
    db.commit()
    db.expire_all()
    return _gunleri_getir(db, donem)
