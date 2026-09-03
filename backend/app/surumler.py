"""Ders programının sürüm geçmişi.

Programda yapılan her değişiklik — çözücü üretimi de, elle düzenleme de —
arka planda yeni bir sürüm yazar. Sürümler EKLENİR, hiç silinmez.

Geçmiş bir ağaçtır, düz bir liste değil. Geri alıp başka bir yöne gidince eski
dal olduğu yerde durur ve listeden geri yüklenebilir; silinmez. Her sürüm
ebeveynini bilir:

  * geri al  → ebeveyne git
  * ileri al → en yeni çocuğa git
  * geri yükle → herhangi bir sürüme atla (sonrası yine durur)

Programın hangi sürümde durduğu `Timetable.current_version_id` imlecinde
tutulur; ayrı bir adım yığını yoktur, tek geçmiş vardır.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assignment, CurriculumEntry, Period, Timetable, TimetableVersion, VersionKind,
)


def anlik_goruntu(db: Session, timetable_id: int) -> list[list]:
    """Programın o anki yerleşimleri: [[müfredat satırı, ders saati, kilitli], ...]

    Sıralı üretilir; aynı içerik her zaman aynı listeyi verir, böylece iki
    sürümü karşılaştırmak anlamlıdır.
    """
    satirlar = db.execute(
        select(Assignment.curriculum_entry_id, Assignment.period_id, Assignment.is_locked)
        .where(Assignment.timetable_id == timetable_id)
        .order_by(Assignment.period_id, Assignment.curriculum_entry_id)
    ).all()
    return [[e, p, bool(k)] for e, p, k in satirlar]


def surum_yaz(
    db: Session, program: Timetable, kind: VersionKind, label: str
) -> TimetableVersion:
    """Programın ŞU ANKİ hâlini yeni bir sürüm olarak yazar ve imleci ona taşır.

    Değişiklik uygulandıktan SONRA çağrılır: sürüm, değişikliğin sonucudur.
    Ebeveyni o anki imleçtir; geri aldıktan sonra yapılan değişiklik böylece
    eski dalı silmeden yeni bir dal açar.
    """
    # Bekleyen değişiklikler önce yazılmalı: sürüm, değişikliğin SONUCUDUR.
    # Otomatik boşaltmaya güvenmek, anlık görüntünün bir adım geride
    # kalmasına yol açabiliyor.
    db.flush()
    yerlesimler = anlik_goruntu(db, program.id)
    sonraki = (db.scalar(
        select(func.max(TimetableVersion.number))
        .where(TimetableVersion.timetable_id == program.id)
    ) or 0) + 1

    surum = TimetableVersion(
        timetable_id=program.id,
        number=sonraki,
        parent_id=program.current_version_id,
        kind=kind,
        label=label[:200],
        placements=yerlesimler,
        placed=len(yerlesimler),
    )
    db.add(surum)
    db.flush()
    program.current_version_id = surum.id
    return surum


def deneme_surumu_yaz(
    db: Session, program: Timetable, yerlesimler: list[tuple[int, int]],
    kilitli: dict[int, list[int]], label: str,
) -> TimetableVersion:
    """Bir çözücü denemesini sürüm olarak yazar; imleci OYNATMAZ.

    Sonsuz modda her deneme geçmişe girer ki kullanıcı ister incelesin ister
    ona dönsün; ama ızgarada duran hâl (imleç) en iyi deneme kalır. Böylece
    ekran her turda değişmez, geçmiş ise eksiksizdir. Ebeveyn o anki imleçtir:
    denemeler geçerli hâlin kardeş dalları olur.
    """
    sonraki = (db.scalar(
        select(func.max(TimetableVersion.number))
        .where(TimetableVersion.timetable_id == program.id)
    ) or 0) + 1
    sirali = sorted(
        [[e, p, p in kilitli.get(e, [])] for e, p in yerlesimler],
        key=lambda x: (x[1], x[0]),
    )
    surum = TimetableVersion(
        timetable_id=program.id, number=sonraki, parent_id=program.current_version_id,
        kind=VersionKind.URETIM, label=label[:200], placements=sirali, placed=len(sirali),
    )
    db.add(surum)
    db.flush()
    return surum


def _gecerli_yerlesimler(
    db: Session, program: Timetable, yerlesimler: list[list]
) -> tuple[list[list], int]:
    """Sürümdeki yerleşimlerden hâlâ uygulanabilir olanlar.

    Sürüm yazıldıktan sonra ders ataması silinmiş ya da zaman ızgarası
    değişmiş olabilir. Böyle satırlar atlanır; kaç tanesinin atlandığı
    çağırana bildirilir ki kullanıcıya söylenebilsin.
    """
    entry_ids = {e for e, _, _ in yerlesimler}
    period_ids = {p for _, p, _ in yerlesimler}
    yasayan_entry = set(db.scalars(
        select(CurriculumEntry.id).where(
            CurriculumEntry.id.in_(entry_ids), CurriculumEntry.deleted_at.is_(None)
        )
    )) if entry_ids else set()
    yasayan_period = set(db.scalars(
        select(Period.id).where(Period.id.in_(period_ids))
    )) if period_ids else set()

    tutulan = [
        satir for satir in yerlesimler
        if satir[0] in yasayan_entry and satir[1] in yasayan_period
    ]
    return tutulan, len(yerlesimler) - len(tutulan)


def surumu_uygula(db: Session, program: Timetable, surum: TimetableVersion) -> int:
    """Sürümün yerleşimlerini programa yazar ve imleci ona taşır.

    Atlanan satır sayısını döner (silinmiş ders ataması ya da kaldırılmış
    ders saati yüzünden).
    """
    tutulan, atlanan = _gecerli_yerlesimler(db, program, surum.placements or [])

    for a in db.scalars(select(Assignment).where(Assignment.timetable_id == program.id)):
        db.delete(a)
    db.flush()
    for entry_id, period_id, kilitli in tutulan:
        db.add(Assignment(
            timetable_id=program.id,
            curriculum_entry_id=entry_id,
            period_id=period_id,
            is_locked=bool(kilitli),
        ))
    program.current_version_id = surum.id
    db.commit()
    return atlanan


def _surum(db: Session, program: Timetable, surum_id: int | None) -> TimetableVersion | None:
    if surum_id is None:
        return None
    surum = db.get(TimetableVersion, surum_id)
    if surum is None or surum.timetable_id != program.id:
        return None
    return surum


def gecerli_surum(db: Session, program: Timetable) -> TimetableVersion | None:
    return _surum(db, program, program.current_version_id)


def onceki_surum(db: Session, program: Timetable) -> TimetableVersion | None:
    """Geri alınacak sürüm: imlecin ebeveyni."""
    simdiki = gecerli_surum(db, program)
    return None if simdiki is None else _surum(db, program, simdiki.parent_id)


def sonraki_surum(db: Session, program: Timetable) -> TimetableVersion | None:
    """İleri alınacak sürüm: imlecin EN YENİ çocuğu.

    Geri alıp yeni bir değişiklik yapılmışsa o dal en yenidir; ileri alma
    kullanıcının en son gittiği yöne gider.
    """
    if program.current_version_id is None:
        return None
    return db.scalar(
        select(TimetableVersion)
        .where(TimetableVersion.timetable_id == program.id,
               TimetableVersion.parent_id == program.current_version_id)
        .order_by(TimetableVersion.number.desc())
        .limit(1)
    )


def geri_al(db: Session, program: Timetable) -> int:
    hedef = onceki_surum(db, program)
    if hedef is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Geri alınacak bir değişiklik yok.")
    return surumu_uygula(db, program, hedef)


def ileri_al(db: Session, program: Timetable) -> int:
    hedef = sonraki_surum(db, program)
    if hedef is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "İleri alınacak bir değişiklik yok.")
    return surumu_uygula(db, program, hedef)


def geri_yukle(db: Session, program: Timetable, number: int) -> int:
    """Listeden seçilen bir sürüme döner. Sonraki sürümler silinmez."""
    hedef = db.scalar(
        select(TimetableVersion)
        .where(TimetableVersion.timetable_id == program.id,
               TimetableVersion.number == number)
    )
    if hedef is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sürüm bulunamadı.")
    if hedef.id == program.current_version_id:
        return 0
    return surumu_uygula(db, program, hedef)


def baslangici_guvence_al(db: Session, program: Timetable) -> None:
    """Programın hiç sürümü yoksa o anki hâlini başlangıç sürümü yapar.

    Yeni program boş açılır; sürümleme öncesinden kalan programlar ise dolu
    olabilir. İkisinde de ilk değişiklikten önce bir geri dönüş noktası
    bulunmalı, yoksa ilk düzenleme geri alınamaz.
    """
    if program.current_version_id is not None:
        return
    var_mi = db.scalar(
        select(TimetableVersion.id)
        .where(TimetableVersion.timetable_id == program.id).limit(1)
    )
    if var_mi is not None:
        return
    surum_yaz(db, program, VersionKind.ILK, "Başlangıç")


# --- Sürüm farkı ---

def _surum_numarasiyla(db: Session, program: Timetable, number: int) -> TimetableVersion:
    surum = db.scalar(
        select(TimetableVersion).where(
            TimetableVersion.timetable_id == program.id,
            TimetableVersion.number == number,
        )
    )
    if surum is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"v{number} sürümü bulunamadı.")
    return surum


def fark(db: Session, program: Timetable, a_no: int, b_no: int) -> dict:
    """İki sürüm arasında ne değişti? A'dan B'ye giden değişiklikler.

    Fark ders (müfredat satırı) bazında okunur: aynı dersin bir saati gidip
    başka bir saati geldiyse bu bir TAŞIMAdır, ayrı ayrı "çıktı" ve "eklendi"
    değil. Eşleme gün/saat sırasına göre yapılır; bir dersin üç saati birden
    yer değiştirdiyse üç taşıma görünür. Eşleşmeden kalanlar çıkan ya da
    eklenen saatlerdir. Aynı yerde duran ama kilidi değişen saat ayrıca
    listelenir.

    Silinmiş ders ya da ders saati sürümde hâlâ duruyor olabilir; adları
    silinmiş kayıttan okunur, yoksa "silinmiş" yazılır.
    """
    from collections import defaultdict

    from app.duzenle import saatleri_oku

    a = _surum_numarasiyla(db, program, a_no)
    b = _surum_numarasiyla(db, program, b_no)
    saatler = saatleri_oku(db, program.term)

    def konum(period_id: int) -> dict:
        s = saatler.get(period_id)
        if s is None:
            return {"period_id": period_id, "gun": "silinmiş", "saat": "saat",
                    "gun_index": 99, "period_index": 99}
        # Izgaranın satır numarası ve sürüm etiketiyle aynı dil: "6. saat".
        # Saatin kendi adı ("5. ders") teneffüsleri saymaz; aynı ekranda iki
        # ayrı sayı görünmesin.
        return {"period_id": s.id, "gun": s.gun_adi, "saat": f"{s.period_index + 1}. saat",
                "gun_index": s.gun_index, "period_index": s.period_index}

    def sira(period_id: int) -> tuple[int, int]:
        k = konum(period_id)
        return (k["gun_index"], k["period_index"])

    # entry_id -> {period_id: kilitli}
    def yerlesim(surum: TimetableVersion) -> dict[int, dict[int, bool]]:
        d: dict[int, dict[int, bool]] = defaultdict(dict)
        for e, p, k in surum.placements or []:
            d[e][p] = bool(k)
        return d

    ya, yb = yerlesim(a), yerlesim(b)
    entry_ids = set(ya) | set(yb)
    entries = {
        e.id: e for e in db.scalars(
            select(CurriculumEntry).where(CurriculumEntry.id.in_(entry_ids))
        )
    } if entry_ids else {}

    def etiket(entry_id: int) -> dict:
        e = entries.get(entry_id)
        if e is None:
            return {"entry_id": entry_id, "sube": "silinmiş ders", "ders": "",
                    "ogretmen": ""}
        return {
            "entry_id": entry_id,
            "sube": " + ".join(sb.name for sb in e.sections),
            "ders": e.subject.name,
            "ogretmen": e.teacher.full_name,
        }

    degisiklikler: list[dict] = []
    for entry_id in entry_ids:
        eski, yeni = ya.get(entry_id, {}), yb.get(entry_id, {})
        gidenler = sorted((p for p in eski if p not in yeni), key=sira)
        gelenler = sorted((p for p in yeni if p not in eski), key=sira)
        kim = etiket(entry_id)

        for g, y in zip(gidenler, gelenler):
            degisiklikler.append({**kim, "tur": "tasindi",
                                  "kaynak": konum(g), "hedef": konum(y)})
        for g in gidenler[len(gelenler):]:
            degisiklikler.append({**kim, "tur": "cikti",
                                  "kaynak": konum(g), "hedef": None})
        for y in gelenler[len(gidenler):]:
            degisiklikler.append({**kim, "tur": "eklendi",
                                  "kaynak": None, "hedef": konum(y)})
        for p in eski.keys() & yeni.keys():
            if eski[p] != yeni[p]:
                degisiklikler.append({**kim,
                                      "tur": "kilitlendi" if yeni[p] else "kilit_acildi",
                                      "kaynak": konum(p), "hedef": konum(p)})

    # Okunur sıra: önce türe göre, sonra şube/ders, sonra zamana göre.
    tur_sirasi = {"tasindi": 0, "cikti": 1, "eklendi": 2, "kilitlendi": 3, "kilit_acildi": 3}
    degisiklikler.sort(key=lambda d: (
        tur_sirasi[d["tur"]], d["sube"], d["ders"],
        sira((d["kaynak"] or d["hedef"])["period_id"]),
    ))

    sayim = {t: 0 for t in ("tasindi", "cikti", "eklendi", "kilit")}
    for d in degisiklikler:
        sayim["kilit" if d["tur"].startswith("kilit") else d["tur"]] += 1
    sayim["degisen_ders"] = len({d["entry_id"] for d in degisiklikler})

    return {"a": a, "b": b, "ozet": sayim, "degisiklikler": degisiklikler}
