"""Yerleşmiş bir ders programındaki uyarılar.

Uyarılar kaydedilmez; her istendiğinde o anki yerleşimden hesaplanır. Böylece
elle sürükle-bırak yapıldığında da doğru kalırlar.

Üç tür uyarı vardır:
  * `gunluk_asim` — bir ders bir günde, kendi günlük sınırından fazla kez var.
    Çözücü bunu ancak kurala uyan bir program bulamadığında yapar.
  * `bitisik` — aynı dersin saatleri arka arkaya. Çözücü buna izin vermez;
    yalnızca elle taşımayla oluşabilir.
  * `gun_siniri` — öğretmen anlaştığından fazla gün okulda. Yine ancak program
    başka türlü tamamlanamadığında oluşur.
  * `bina_gecisi` — öğretmen bir günde birden fazla binada. Yalnızca dönem
    ayarı açıkken hesaplanır; kural esnetilebilir olduğu için oluşabilir.

Kullanıcı bir uyarıyı "görmezden gel" diyerek o program için kalıcı olarak
gizleyebilir.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Assignment, CurriculumEntry, Day, Period, Section, Timetable,
)
from app.solver.loader import sabah_mi


def _saat_bilgisi(db: Session) -> dict[int, tuple[int, int, str, bool]]:
    """period_id -> (gün sırası, ders saati sırası, gün adı, sabah mı)"""
    bilgi: dict[int, tuple[int, int, str, bool]] = {}
    for g in db.scalars(select(Day).options(selectinload(Day.periods))):
        saatler = sorted(g.periods, key=lambda x: x.index)
        for p in saatler:
            bilgi[p.id] = (g.index, p.index, g.name, sabah_mi(saatler, p))
    return bilgi


def _gun_metni(yarim_gun: int) -> str:
    """9 -> '4,5'. Kullanıcı gün konuşur, veritabanı yarım gün tutar."""
    return f"{yarim_gun / 2:g}".replace(".", ",")


def _gun_siniri_uyarilari(
    program: Timetable, atamalar: list, saatler: dict, gizlenen: set[str]
) -> list[dict]:
    """Gün sınırı aşılan öğretmenler.

    Sınır esnetilebilir olduğu için program yine üretilir; aşım burada
    görünür. Yerleşimden hesaplandığı için elle taşımadan sonra da doğrudur.
    """
    # teacher_id -> {(gün, sabah mı)}
    yarimlar: dict[int, set[tuple[int, bool]]] = defaultdict(set)
    ogretmenler: dict[int, object] = {}
    gun_adlari: dict[int, str] = {}
    for a in atamalar:
        konum = saatler.get(a.period_id)
        if konum is None:
            continue
        gun, _, gun_adi, sabah = konum
        yarimlar[a.entry.teacher_id].add((gun, sabah))
        ogretmenler[a.entry.teacher_id] = a.entry.teacher
        gun_adlari[gun] = gun_adi

    uyarilar: list[dict] = []
    for tid, kullanilan in sorted(yarimlar.items()):
        ogretmen = ogretmenler[tid]
        sinir = ogretmen.max_half_days
        if sinir is None:
            continue
        gunler = {gun for gun, _ in kullanilan}
        gun_tavani = -(-sinir // 2)
        if len(kullanilan) <= sinir and len(gunler) <= gun_tavani:
            continue

        parcalar = []
        for gun in sorted(gunler):
            tam = (gun, True) in kullanilan and (gun, False) in kullanilan
            parcalar.append(gun_adlari[gun] + ("" if tam else " (yarım)"))

        anahtar = f"gunsinir:{tid}"
        uyarilar.append({
            "key": anahtar,
            "tur": "gun_siniri",
            "baslik": (
                f"{ogretmen.full_name}: {_gun_metni(len(kullanilan))} gün okulda, "
                f"sınır {_gun_metni(sinir)} gün"
            ),
            "detay": (
                f"Program {', '.join(parcalar)} günlerine yayıldı. Başka türlü "
                f"tamamlanamadığı için gün sınırı esnetildi. Öğretmenin haftalık "
                f"yükünü azaltmak ya da müsaitlik matrisinden bazı günleri "
                f"kapatmak sınırın içinde kalmayı kolaylaştırır."
            ),
            "sube": "",
            "ders": "",
            "ogretmen": ogretmen.full_name,
            "gun": "",
            "konan": len(kullanilan),
            "sinir": sinir,
            "ignored": anahtar in gizlenen,
        })
    return uyarilar


def _bina_uyarilari(
    program: Timetable, atamalar: list, saatler: dict, gizlenen: set[str]
) -> list[dict]:
    """Bir günde birden fazla binada ders veren öğretmenler.

    Binası olmayan şubeler sayılmaz — kural onları da kapsamıyor.
    """
    # (öğretmen, gün) -> {bina adı}
    gunluk: dict[tuple[int, int], set[str]] = defaultdict(set)
    ogretmenler: dict[int, object] = {}
    gun_adlari: dict[int, str] = {}
    for a in atamalar:
        konum = saatler.get(a.period_id)
        bina = a.entry.section.building
        if konum is None or bina is None:
            continue
        gun, _, gun_adi, _ = konum
        gunluk[(a.entry.teacher_id, gun)].add(bina.name)
        ogretmenler[a.entry.teacher_id] = a.entry.teacher
        gun_adlari[gun] = gun_adi

    uyarilar: list[dict] = []
    for (tid, gun), binalar in sorted(gunluk.items()):
        if len(binalar) < 2:
            continue
        ogretmen = ogretmenler[tid]
        anahtar = f"bina:{tid}:{gun}"
        uyarilar.append({
            "key": anahtar,
            "tur": "bina_gecisi",
            "baslik": (f"{ogretmen.full_name}: {gun_adlari[gun]} günü "
                       f"{len(binalar)} binada ders var"),
            "detay": (
                f"{', '.join(sorted(binalar))} binalarında ders verecek. Program "
                f"başka türlü tamamlanamadığı için bina kuralı esnetildi. Dersleri "
                f"binaya göre ayrı günlere toplamak için öğretmenin yükünü ya da "
                f"müsaitliğini gözden geçirin."
            ),
            "sube": "",
            "ders": "",
            "ogretmen": ogretmen.full_name,
            "gun": gun_adlari[gun],
            "konan": len(binalar),
            "sinir": 1,
            "ignored": anahtar in gizlenen,
        })
    return uyarilar


def uyarilari_hesapla(db: Session, program: Timetable) -> list[dict]:
    saatler = _saat_bilgisi(db)
    atamalar = list(db.scalars(
        select(Assignment)
        .options(
            selectinload(Assignment.entry)
            .selectinload(CurriculumEntry.section)
            .selectinload(Section.building),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.subject),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.teacher),
        )
        .where(Assignment.timetable_id == program.id)
    ))

    # (müfredat satırı, gün) -> ders saati sıraları
    gunluk: dict[tuple[int, int], list[int]] = defaultdict(list)
    satirlar: dict[int, CurriculumEntry] = {}
    gun_adlari: dict[int, str] = {}
    for a in atamalar:
        konum = saatler.get(a.period_id)
        if konum is None:
            continue
        gun, saat, gun_adi, _ = konum
        gunluk[(a.curriculum_entry_id, gun)].append(saat)
        satirlar[a.curriculum_entry_id] = a.entry
        gun_adlari[gun] = gun_adi

    gizlenen = set(program.ignored_warnings or [])
    uyarilar: list[dict] = _gun_siniri_uyarilari(program, atamalar, saatler, gizlenen)
    # Bina kuralı kapalıysa geçiş bir sorun değildir; uyarı da üretilmez.
    if program.term.block_building_switch:
        uyarilar += _bina_uyarilari(program, atamalar, saatler, gizlenen)

    for (entry_id, gun), saatler_listesi in sorted(gunluk.items()):
        e = satirlar[entry_id]
        saatler_listesi.sort()
        etiket = f"{e.section.name} · {e.subject.name}"
        gun_adi = gun_adlari[gun]

        if len(saatler_listesi) > e.max_per_day:
            anahtar = f"gunluk:{entry_id}:{gun}"
            uyarilar.append({
                "key": anahtar,
                "tur": "gunluk_asim",
                "baslik": f"{etiket}: {gun_adi} günü {len(saatler_listesi)} saat",
                "detay": (
                    f"Bu ders için günlük sınır {e.max_per_day} saat, ama "
                    f"{gun_adi} günü {len(saatler_listesi)} saat yerleşti. "
                    f"Program başka türlü tamamlanamadığı için sınır esnetildi; "
                    f"araya başka dersler konarak saatler ayrıldı."
                ),
                "sube": e.section.name,
                "ders": e.subject.name,
                "ogretmen": e.teacher.full_name,
                "gun": gun_adi,
                "konan": len(saatler_listesi),
                "sinir": e.max_per_day,
                "ignored": anahtar in gizlenen,
            })

        bitisikler = [
            (a, b) for a, b in zip(saatler_listesi, saatler_listesi[1:]) if b - a == 1
        ]
        # Blok dersler zaten ardışıktır; yalnızca en uzun bloğu aşan diziler sorundur.
        en_uzun_blok = _en_uzun_blok(e)
        if bitisikler and _en_uzun_dizi(saatler_listesi) > en_uzun_blok:
            anahtar = f"bitisik:{entry_id}:{gun}"
            uyarilar.append({
                "key": anahtar,
                "tur": "bitisik",
                "baslik": f"{etiket}: {gun_adi} günü saatler arka arkaya",
                "detay": (
                    f"Bu dersin en uzun bloğu {en_uzun_blok} saat, ama {gun_adi} "
                    f"günü {_en_uzun_dizi(saatler_listesi)} saat kesintisiz. "
                    f"Aralarına başka bir ders koymak daha yararlı olur."
                ),
                "sube": e.section.name,
                "ders": e.subject.name,
                "ogretmen": e.teacher.full_name,
                "gun": gun_adi,
                "konan": _en_uzun_dizi(saatler_listesi),
                "sinir": en_uzun_blok,
                "ignored": anahtar in gizlenen,
            })

    return uyarilar


def _en_uzun_blok(e: CurriculumEntry) -> int:
    from app import bloklar

    return max(bloklar.coz(e.block_pattern, e.weekly_hours), default=1)


def _en_uzun_dizi(saatler: list[int]) -> int:
    en_uzun = uzunluk = 1
    for a, b in zip(saatler, saatler[1:]):
        uzunluk = uzunluk + 1 if b - a == 1 else 1
        en_uzun = max(en_uzun, uzunluk)
    return en_uzun
