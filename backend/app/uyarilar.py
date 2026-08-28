"""Yerleşmiş bir ders programındaki uyarılar.

Uyarılar kaydedilmez; her istendiğinde o anki yerleşimden hesaplanır. Böylece
elle sürükle-bırak yapıldığında da doğru kalırlar.

İki tür uyarı vardır:
  * `gunluk_asim` — bir ders bir günde, kendi günlük sınırından fazla kez var.
    Çözücü bunu ancak kurala uyan bir program bulamadığında yapar.
  * `bitisik` — aynı dersin saatleri arka arkaya. Çözücü buna izin vermez;
    yalnızca elle taşımayla oluşabilir.

Kullanıcı bir uyarıyı "görmezden gel" diyerek o program için kalıcı olarak
gizleyebilir.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Assignment, CurriculumEntry, Day, Period, Timetable


def _saat_bilgisi(db: Session) -> dict[int, tuple[int, int, str]]:
    """period_id -> (gün sırası, ders saati sırası, gün adı)"""
    return {
        p.id: (g.index, p.index, g.name)
        for g in db.scalars(select(Day).options(selectinload(Day.periods)))
        for p in g.periods
    }


def uyarilari_hesapla(db: Session, program: Timetable) -> list[dict]:
    saatler = _saat_bilgisi(db)
    atamalar = db.scalars(
        select(Assignment)
        .options(
            selectinload(Assignment.entry).selectinload(CurriculumEntry.section),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.subject),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.teacher),
        )
        .where(Assignment.timetable_id == program.id)
    )

    # (müfredat satırı, gün) -> ders saati sıraları
    gunluk: dict[tuple[int, int], list[int]] = defaultdict(list)
    satirlar: dict[int, CurriculumEntry] = {}
    gun_adlari: dict[int, str] = {}
    for a in atamalar:
        konum = saatler.get(a.period_id)
        if konum is None:
            continue
        gun, saat, gun_adi = konum
        gunluk[(a.curriculum_entry_id, gun)].append(saat)
        satirlar[a.curriculum_entry_id] = a.entry
        gun_adlari[gun] = gun_adi

    gizlenen = set(program.ignored_warnings or [])
    uyarilar: list[dict] = []

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
