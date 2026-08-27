"""Çözümsüzlük tanısı.

İki aşamalıdır:
  1. Çözücüyü hiç çalıştırmadan yapılan sayısal ön kontroller. Gerçek hayattaki
     tıkanmaların çoğu buradan çıkar ve tam olarak neyin neye yetmediğini söyler.
  2. Çözücü gevşetilmiş modelde hangi saatleri yerleştiremediğini bildirir.

Çıktı, arayüzde doğrudan gösterilebilecek ve yapay zekaya girdi olabilecek
yapılandırılmış bir sözlüktür.
"""
from __future__ import annotations

from collections import defaultdict

from app.solver.engine import Lesson, Slot, _gune_gore


def _gun_adlari(slots: list[Slot]) -> dict[int, str]:
    return {s.day_index: s.day_name for s in slots}


def on_kontrol(slots: list[Slot], lessons: list[Lesson]) -> list[dict]:
    """Çözücüden önce yapılan kapasite kontrolleri. Bulgu listesi döner."""
    bulgular: list[dict] = []
    if not slots:
        return [{
            "kod": "zaman_izgarasi_bos",
            "baslik": "Zaman ızgarası tanımlı değil",
            "detay": "Hiç ders saati tanımlanmamış. Önce Ayarlar > Zaman Izgarası "
                     "bölümünden günleri ve ders saatlerini tanımlayın.",
            "onem": "engel",
        }]
    if not lessons:
        return [{
            "kod": "mufredat_bos",
            "baslik": "Müfredat boş",
            "detay": "Hiç ders tanımlanmamış. Şubelere ders ve öğretmen atayın.",
            "onem": "engel",
        }]

    gunler = _gune_gore(slots)
    gun_adlari = _gun_adlari(slots)
    toplam_slot = len(slots)

    # --- Şube kapasitesi ---
    sube_yuku: dict[int, int] = defaultdict(int)
    sube_adi: dict[int, str] = {}
    for l in lessons:
        sube_yuku[l.section_id] += l.weekly_hours
        sube_adi[l.section_id] = l.section_name

    for sid, yuk in sube_yuku.items():
        if yuk > toplam_slot:
            bulgular.append({
                "kod": "sube_kapasite",
                "baslik": f"{sube_adi[sid]} şubesine haftada sığmayacak kadar ders var",
                "detay": f"Şubenin haftalık ders yükü {yuk} saat, ama haftada yalnızca "
                         f"{toplam_slot} ders saati tanımlı. En az {yuk - toplam_slot} "
                         f"saat fazla.",
                "onem": "engel",
                "sube": sube_adi[sid],
                "gereken": yuk,
                "mevcut": toplam_slot,
            })

    # --- Öğretmen kapasitesi ---
    ogretmen_yuku: dict[int, int] = defaultdict(int)
    ogretmen_adi: dict[int, str] = {}
    ogretmen_kapali: dict[int, frozenset[int]] = {}
    for l in lessons:
        ogretmen_yuku[l.teacher_id] += l.weekly_hours
        ogretmen_adi[l.teacher_id] = l.teacher_name
        ogretmen_kapali[l.teacher_id] = l.blocked_period_ids

    for tid, yuk in ogretmen_yuku.items():
        musait = toplam_slot - len(ogretmen_kapali.get(tid, frozenset()))
        if yuk > musait:
            bulgular.append({
                "kod": "ogretmen_kapasite",
                "baslik": f"{ogretmen_adi[tid]} öğretmenin yükü müsait saatlerini aşıyor",
                "detay": f"Toplam {yuk} saat ders veriyor, ama müsaitlik matrisine göre "
                         f"haftada yalnızca {musait} saati uygun. "
                         f"{yuk - musait} saat açık var.",
                "onem": "engel",
                "ogretmen": ogretmen_adi[tid],
                "gereken": yuk,
                "mevcut": musait,
            })

    # --- Blok ders gün içine sığıyor mu ---
    en_uzun_ardisik = 0
    for gun_slotlari in gunler.values():
        uzunluk = 1
        for a, b in zip(gun_slotlari, gun_slotlari[1:]):
            if slots[b].period_index - slots[a].period_index == 1:
                uzunluk += 1
                en_uzun_ardisik = max(en_uzun_ardisik, uzunluk)
            else:
                uzunluk = 1
        en_uzun_ardisik = max(en_uzun_ardisik, uzunluk if gun_slotlari else 0)

    for l in lessons:
        boy = min(l.block_size, l.weekly_hours)
        if boy > en_uzun_ardisik:
            bulgular.append({
                "kod": "blok_sigmiyor",
                "baslik": f"{l.section_name} · {l.subject_name} blok dersi hiçbir güne sığmıyor",
                "detay": f"{boy} saatlik blok isteniyor, ama hiçbir günde art arda "
                         f"{boy} ders saati yok (en uzun kesintisiz dizi "
                         f"{en_uzun_ardisik} saat). Teneffüsler diziyi bölüyor olabilir.",
                "onem": "engel",
                "sube": l.section_name,
                "ders": l.subject_name,
            })

    # --- Günlük tekrar sınırı haftalık yükü karşılıyor mu ---
    gun_sayisi = len(gunler)
    for l in lessons:
        tavan = l.max_per_day * gun_sayisi
        if l.weekly_hours > tavan:
            bulgular.append({
                "kod": "gunluk_sinir",
                "baslik": f"{l.section_name} · {l.subject_name} günlük sınıra sığmıyor",
                "detay": f"Haftada {l.weekly_hours} saat isteniyor, ama günde en fazla "
                         f"{l.max_per_day} saat kuralıyla {gun_sayisi} günde en çok "
                         f"{tavan} saat yerleşebilir. Günlük sınırı yükseltin.",
                "onem": "engel",
                "sube": l.section_name,
                "ders": l.subject_name,
            })

    # --- Öğretmen bazında gün gün darboğaz ---
    for tid, kapali in ogretmen_kapali.items():
        yuk = ogretmen_yuku[tid]
        gunluk_musait = {
            gi: sum(1 for si in idx if slots[si].period_id not in kapali)
            for gi, idx in gunler.items()
        }
        bos_gunler = [gun_adlari[gi] for gi, n in gunluk_musait.items() if n == 0]
        if bos_gunler and yuk > 0:
            kalan = sum(n for n in gunluk_musait.values())
            if kalan < yuk:
                bulgular.append({
                    "kod": "ogretmen_gun_kapali",
                    "baslik": f"{ogretmen_adi[tid]} öğretmenin kapalı günleri yükü sıkıştırıyor",
                    "detay": f"{', '.join(bos_gunler)} günleri tamamen kapalı. "
                             f"Kalan günlerde {kalan} saat müsaitlik var, "
                             f"{yuk} saat ders veriyor.",
                    "onem": "engel",
                    "ogretmen": ogretmen_adi[tid],
                })

    return bulgular


def rapor_olustur(
    slots: list[Slot],
    lessons: list[Lesson],
    unplaced: dict[int, int],
    status_name: str,
    seconds: float,
) -> dict:
    """Ön kontrolleri ve çözücü sonucunu tek yapılandırılmış rapora toplar."""
    bulgular = on_kontrol(slots, lessons)
    ders_by_id = {l.entry_id: l for l in lessons}

    yerlesmeyenler = []
    for entry_id, saat in sorted(unplaced.items(), key=lambda kv: -kv[1]):
        l = ders_by_id.get(entry_id)
        if l is None:
            continue
        yerlesmeyenler.append({
            "sube": l.section_name,
            "ders": l.subject_name,
            "ogretmen": l.teacher_name,
            "istenen_saat": l.weekly_hours,
            "yerlesmeyen_saat": saat,
        })
        bulgular.append({
            "kod": "yerlesemedi",
            "baslik": f"{l.section_name} · {l.subject_name}: {saat} saat yerleşemedi",
            "detay": f"{l.teacher_name} öğretmenle {l.weekly_hours} saatin "
                     f"{saat} saati boş kaldı. Bu dersin öğretmeni ya da şubesi "
                     f"o saatlerde başka bir dersle dolu.",
            "onem": "uyari",
            "sube": l.section_name,
            "ders": l.subject_name,
            "ogretmen": l.teacher_name,
        })

    return {
        "durum": status_name,
        "sure_sn": round(seconds, 2),
        "ozet": {
            "ders_saati_sayisi": len(slots),
            "gun_sayisi": len({s.day_index for s in slots}),
            "mufredat_satiri": len(lessons),
            "toplam_ders_saati": sum(l.weekly_hours for l in lessons),
            "sube_sayisi": len({l.section_id for l in lessons}),
            "ogretmen_sayisi": len({l.teacher_id for l in lessons}),
            "yerlesmeyen_toplam": sum(unplaced.values()),
        },
        "bulgular": bulgular,
        "yerlesmeyenler": yerlesmeyenler,
    }
