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
    # (öğretmen, gün) -> [(ders saati sırası, bina adı)]
    gunluk: dict[tuple[int, int], list[tuple[int, str]]] = defaultdict(list)
    ogretmenler: dict[int, object] = {}
    gun_adlari: dict[int, str] = {}
    for a in atamalar:
        konum = saatler.get(a.period_id)
        bina = a.entry.section.building
        if konum is None or bina is None:
            continue
        gun, saat, gun_adi, _ = konum
        gunluk[(a.entry.teacher_id, gun)].append((saat, bina.name))
        ogretmenler[a.entry.teacher_id] = a.entry.teacher
        gun_adlari[gun] = gun_adi

    uyarilar: list[dict] = []
    for (tid, gun), sira in sorted(gunluk.items()):
        binalar = {b for _, b in sira}
        if len(binalar) < 2:
            continue
        dizi = [b for _, b in sorted(sira)]
        gecis = sum(1 for a, b in zip(dizi, dizi[1:]) if a != b)
        # Ardışık tekrarları at: "A, B, A" gibi okunsun.
        yol = [b for i, b in enumerate(dizi) if i == 0 or b != dizi[i - 1]]
        ogretmen = ogretmenler[tid]
        anahtar = f"bina:{tid}:{gun}"
        gidip_gelme = gecis > 1
        uyarilar.append({
            "key": anahtar,
            "tur": "bina_gecisi",
            "baslik": (f"{ogretmen.full_name}: {gun_adlari[gun]} günü "
                       + (f"{gecis} kez bina değiştiriyor" if gidip_gelme
                          else f"{len(binalar)} binada ders var")),
            "detay": (
                f"Sıra: {' → '.join(yol)}. Program başka türlü tamamlanamadığı "
                f"için bina kuralı esnetildi"
                + (", üstelik önce bir binayı bitirip öbürüne geçmek de mümkün "
                   "olmadı; öğretmen gün içinde gidip geliyor" if gidip_gelme else "")
                + ". Dersleri binaya göre ayrı günlere toplamak için öğretmenin "
                f"yükünü ya da müsaitliğini gözden geçirin."
            ),
            "sube": "",
            "ders": "",
            "ogretmen": ogretmen.full_name,
            "gun": gun_adlari[gun],
            "konan": gecis,
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
            selectinload(Assignment.merged_entry).selectinload(CurriculumEntry.section),
            selectinload(Assignment.merged_entry).selectinload(CurriculumEntry.subject),
            selectinload(Assignment.merged_entry).selectinload(CurriculumEntry.teacher),
        )
        .where(Assignment.timetable_id == program.id)
    ))

    # (müfredat satırı, gün) -> ders saati sıraları. Ortak okutulan saat iki
    # satırın da gününe yazılır: her iki şube o saatte dersi görür.
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
        if a.merged_entry is not None:
            gunluk[(a.merged_entry_id, gun)].append(saat)
            satirlar[a.merged_entry_id] = a.merged_entry
        gun_adlari[gun] = gun_adi

    gizlenen = set(program.ignored_warnings or [])
    uyarilar: list[dict] = _gun_siniri_uyarilari(program, atamalar, saatler, gizlenen)
    # Bina kuralı kapalıysa geçiş bir sorun değildir; uyarı da üretilmez.
    if program.term.block_building_switch:
        uyarilar += _bina_uyarilari(program, atamalar, saatler, gizlenen)

    for (entry_id, gun), saatler_listesi in sorted(gunluk.items()):
        e = satirlar[entry_id]
        saatler_listesi.sort()
        # Birleşik derste uyarı tüm şubeleri ilgilendirir; adı öyle yazılır.
        sube_adi = " + ".join(sb.name for sb in e.sections)
        etiket = f"{sube_adi} · {e.subject.name}"
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
                "sube": sube_adi,
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
                "sube": sube_adi,
                "ders": e.subject.name,
                "ogretmen": e.teacher.full_name,
                "gun": gun_adi,
                "konan": _en_uzun_dizi(saatler_listesi),
                "sinir": en_uzun_blok,
                "ignored": anahtar in gizlenen,
            })

    from app.solver.loader import ders_gruplarini_yukle

    gruplar = ders_gruplarini_yukle(db, program.term)
    if program.term.same_subject_apart or gruplar:
        uyarilar += _ayrilma_uyarilari(gunluk, satirlar, gun_adlari, gizlenen,
                                       program.term.same_subject_apart, gruplar)

    return uyarilar


def _ayrilma_uyarilari(gunluk: dict, satirlar: dict, gun_adlari: dict,
                       gizlenen: set[str], ayni_ders: bool,
                       gruplar: dict[int, tuple[int, str]]) -> list[dict]:
    """Bir şubede arka arkaya gelmemesi gereken satırlar bitişik yerleşmiş:
    aynı ders farklı öğretmende (kural açıkken) ya da aynı ders grubu.
    Çözücü buna izin vermez; elle taşımayla oluşabilir."""
    # (şube, küme adı, gün) -> [(saat, entry_id)]
    kumeler: dict[tuple[str, str, int], list[tuple[int, int]]] = defaultdict(list)
    for (entry_id, gun), saatler in gunluk.items():
        e = satirlar[entry_id]
        adlar = []
        if ayni_ders:
            adlar.append(e.subject.name)
        grup = gruplar.get(e.subject_id)
        if grup is not None:
            adlar.append(f"{grup[1]} grubu")
        for sb in e.sections:
            for ad in adlar:
                for saat in saatler:
                    kumeler[(sb.name, ad, gun)].append((saat, entry_id))

    uyarilar: list[dict] = []
    for (sube, ad, gun), liste in sorted(kumeler.items()):
        if len({eid for _, eid in liste}) < 2:
            continue
        liste.sort()
        bitisik = [(a, b) for a, b in zip(liste, liste[1:])
                   if b[0] - a[0] == 1 and a[1] != b[1]]
        if not bitisik:
            continue
        dersler = sorted({f"{satirlar[eid].subject.name} ({satirlar[eid].teacher.full_name})"
                          for _, eid in liste})
        anahtar = f"ayrilma:{sube}:{ad}:{gun}"
        uyarilar.append({
            "key": anahtar,
            "tur": "bitisik",
            "baslik": f"{sube} · {ad}: {gun_adlari[gun]} günü arka arkaya",
            "detay": (f"{'; '.join(dersler)} {gun_adlari[gun]} günü bitişik saatlerde. "
                      f"Kısıtlamalar'daki kurala göre bunlar arka arkaya gelmemeli; "
                      f"araya başka bir ders koyun."),
            "sube": sube,
            "ders": ad,
            "ogretmen": "",
            "gun": gun_adlari[gun],
            "konan": len(bitisik) + 1,
            "sinir": 1,
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
