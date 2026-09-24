"""Zaman ızgarası: günler ve ders saatleri. Ders saati sayısı güne göre değişir.

Izgara döneme aittir; her dönem kendi zil düzenini tanımlar.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import aktif_donem, current_user
from app.models import (
    Assignment, CurriculumEntry, Day, Period, SectionAvailability,
    TeacherAvailability, Term, Timetable,
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


def _dolu_saatler(db: Session, donem: Term) -> dict[int, list[Assignment]]:
    """period_id -> o saatte yerleşmiş dersler (silinmemiş programlarda).

    Izgara değişikliğinin sınırı budur: dersi olan bir saat silinemez,
    teneffüse çevrilemez, günü kapatılamaz. Dersi olmayan gün ve saatler
    program varken de değiştirilebilir — "Cuma boş, kaldıralım" gibi.
    """
    atamalar = db.scalars(
        select(Assignment)
        .join(Timetable, Timetable.id == Assignment.timetable_id)
        .options(
            selectinload(Assignment.timetable),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.teacher),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.section),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.subject),
        )
        .where(Timetable.term_id == donem.id, Timetable.deleted_at.is_(None))
    )
    dolu: dict[int, list[Assignment]] = {}
    for a in atamalar:
        dolu.setdefault(a.period_id, []).append(a)
    return dolu


def _dolu_engeli(
    gun_adi: str, ne: str, saatler: list[Period], dolu: dict[int, list[Assignment]],
) -> None:
    """Verilen saatlerden birinde ders varsa 409 ile durdurur.

    İleti dersleri tek tek sayar — program, öğretmen, şube, ders, saat —
    çünkü kullanıcı ekranda başka bir programa bakıyor olabilir ve "ders yok"
    sanır; hangi programın tuttuğunu görmesi gerekir.
    """
    saatler = sorted(saatler, key=lambda p: p.index)
    dersler = [(p, a) for p in saatler for a in dolu.get(p.id, [])]
    if not dersler:
        return
    satirlar = [
        f"{a.timetable.name} programı, {p.name}: {a.entry.teacher.full_name} — "
        f"{a.entry.section.name} {a.entry.subject.name}"
        for p, a in dersler[:12]
    ]
    kalan = len(dersler) - len(satirlar)
    raise HTTPException(
        status.HTTP_409_CONFLICT,
        f"{gun_adi} {ne}: bu saatlerde yerleşmiş {len(dersler)} ders var. Önce o "
        f"dersleri başka saate taşıyın ya da programı silin. "
        + "; ".join(satirlar)
        + (f"; … ve {kalan} ders daha." if kalan > 0 else "."),
    )


def _saatleri_esitle(
    db: Session, gun: Day, gelen: list[PeriodIn],
    dolu: dict[int, list[Assignment]] | None = None,
) -> None:
    """Günün ders saatlerini gelen listeye göre yerinde günceller.

    Var olan kayıtlar korunur; bu sayede ders saati kimlikleri sabit kalır ve
    onlara bağlı öğretmen/şube müsaitlik işaretleri hayatta kalır. Baştan silip
    yeniden yaratmak, adı ya da saati bile değişmemiş satırların müsaitliğini
    de silerdi.

    Eşleştirme, gönderildiyse KİMLİĞE göre yapılır. Sıraya göre eşleştirmek
    satırlar yeniden sıralandığında müsaitliği yanlış satıra bağlardı: araya
    teneffüs eklendiğinde "2. ders"in işaretleri teneffüsün üstünde kalırdı.
    Kimlik göndermeyen istemciler için sıraya göre eşleştirme sürüyor.
    """
    kimlige_gore = {p.id: p for p in gun.periods}
    siraya_gore = {p.index: p for p in gun.periods}

    # İki geçiş: kimlik eşleşmesi sıradan ÖNCE bağlanır. Tek geçişte, araya
    # eklenen kimliksiz satır kendi sırasındaki kaydı kapar ve o kaydı kimliğiyle
    # isteyen asıl satıra bir şey kalmazdı.
    eslesme: list[tuple[PeriodIn, Period | None]] = [(p, None) for p in gelen]
    kullanilan: set[int] = set()

    for i, gelen_saat in enumerate(gelen):
        if gelen_saat.id is None:
            continue
        var_olan = kimlige_gore.get(gelen_saat.id)
        if var_olan is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"{gun.name} gününe ait olmayan bir ders saati gönderildi.",
            )
        kullanilan.add(var_olan.id)
        eslesme[i] = (gelen_saat, var_olan)

    for i, gelen_saat in enumerate(gelen):
        if gelen_saat.id is not None:
            continue
        var_olan = siraya_gore.get(gelen_saat.index)
        if var_olan is None or var_olan.id in kullanilan:
            continue                # gerçekten yeni satır
        kullanilan.add(var_olan.id)
        eslesme[i] = (gelen_saat, var_olan)

    dolu = dolu or {}
    silinecek = [p for p in gun.periods if p.id not in kullanilan]
    _dolu_engeli(gun.name, "gününden ders saati silinemez", silinecek, dolu)
    # Dersi olan saat teneffüse çevrilemez: teneffüse ders konmaz.
    _dolu_engeli(
        gun.name, "gününde dersi olan saat teneffüse çevrilemez",
        [v for g, v in eslesme if v is not None and g.is_break and not v.is_break],
        dolu,
    )
    _saatleri_sil(db, silinecek)

    # Sıralama değişmiş olabilir. (day_id, index) benzersiz olduğu için önce
    # geçici negatif sıralar yazılır; yoksa 3. satırı 1'e taşırken oradaki
    # satırla çakışılırdı.
    for gecici, (_, var_olan) in enumerate(eslesme, start=1):
        if var_olan is not None:
            var_olan.index = -gecici
    db.flush()

    for gelen_saat, var_olan in eslesme:
        if var_olan is None:
            db.add(Period(day_id=gun.id, **gelen_saat.model_dump(exclude={"id"})))
            continue
        var_olan.index = gelen_saat.index
        var_olan.name = gelen_saat.name
        var_olan.start_time = gelen_saat.start_time
        var_olan.end_time = gelen_saat.end_time
        var_olan.is_break = gelen_saat.is_break
        var_olan.is_lunch = gelen_saat.is_lunch
    db.flush()


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
    """Izgarayı bütünüyle değiştirir.

    Yerleşmiş program varken de kaydedilir; sınır, dersi olan saatlerdir:
    böyle bir saat silinemez, teneffüse çevrilemez, günü kapatılamaz ya da
    silinemez. Ad, saat aralığı, sıra ve yeni satır serbesttir.
    """
    dolu = _dolu_saatler(db, donem)
    mevcut = {d.index: d for d in _gunleri_getir(db, donem)}
    gelen_indexler = {d.index for d in payload}

    # Listeden tamamen çıkarılan günler. Günü pasife almak silmek değildir:
    # pasif günün ders saatleri ve müsaitlik işaretleri olduğu gibi durur,
    # gün yeniden açıldığında geri gelir.
    for gun in mevcut.values():
        if gun.index not in gelen_indexler:
            _dolu_engeli(gun.name, "günü silinemez", list(gun.periods), dolu)
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
            if gun.is_active and not gelen.is_active:
                _dolu_engeli(gun.name, "günü kapatılamaz", list(gun.periods), dolu)
            gun.name, gun.is_active = gelen.name, gelen.is_active
        _saatleri_esitle(db, gun, gelen.periods, dolu)

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
    db.add(Period(day_id=day_id, **payload.model_dump(exclude={"id"})))
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
                          is_break=p.is_break, is_lunch=p.is_lunch))
    db.commit()
    db.expire_all()
    return _gunleri_getir(db, donem)
