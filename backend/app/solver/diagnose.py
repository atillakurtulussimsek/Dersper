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

from app.solver.engine import (
    Lesson, Slot, _gune_gore, sube_ciftleri, sube_etiketi, sube_kapali_saatleri,
)


def birlesme_indirimi(lessons: list[Lesson]) -> dict[int, int]:
    """teacher_id -> birleştirme kurallarıyla en çok kaç saat düşebilir.

    Ortak saat öğretmenin iki dersini tek saatte okutur; kapasite denetimleri
    öğretmenin yükünü bu kadar hafif sayar. Kural başına, o öğretmenin
    eşleşmelerinin toplamı ile kuralın saatinin küçüğü.
    """
    kapasite: dict[tuple[int, int], int] = defaultdict(int)
    kural_saat: dict[int, int] = {}
    for l in lessons:
        if l.ortak:
            kapasite[(l.teacher_id, l.ortak_kural_id)] += l.weekly_hours
            kural_saat[l.ortak_kural_id] = l.kural_saat
    indirim: dict[int, int] = defaultdict(int)
    for (tid, kid), kap in kapasite.items():
        indirim[tid] += min(kap, kural_saat[kid])
    return indirim


def kural_bulgulari(slots: list[Slot], lessons: list[Lesson]) -> list[dict]:
    """Kuralın ortak dersleri izinli günlerde, öğretmen ve iki şube açıkken
    kuralın saati kadar yer bulabiliyor mu? Bulamıyorsa kesin engel."""
    kurallar: dict[int, list[Lesson]] = defaultdict(list)
    for l in lessons:
        if l.ortak:
            kurallar[l.ortak_kural_id].append(l)
    bulgular = []
    for uyeler in kurallar.values():
        ornek = uyeler[0]
        acik_saatler = {
            s.period_id for s in slots
            if ornek.izinli_gunler is None or s.day_index in ornek.izinli_gunler
        }
        kapasite = sum(
            min(l.weekly_hours,
                sum(1 for p in acik_saatler if p not in l.engelli_period_ids))
            for l in uyeler
        )
        if kapasite >= ornek.kural_saat:
            continue
        bulgular.append({
            "kod": "birlestirme_sigmiyor",
            "baslik": f"{ornek.kural_adi} birleştirme kuralı seçilen günlere sığmıyor",
            "detay": (f"Kural haftada {ornek.kural_saat} saat ortak ders istiyor, ama "
                      f"seçilen günlerde öğretmenin ve iki şubenin birlikte açık olduğu "
                      f"saatlerle en çok {kapasite} saat ortak okutulabilir."),
            "oneri": (f"Kurala gün ekleyin, saatini {kapasite} ya da altına düşürün "
                      f"ya da o günlerde müsaitlik açın."),
            "onem": "engel",
            "sube": ornek.kural_adi,
            "gereken": ornek.kural_saat,
            "mevcut": kapasite,
        })
    return bulgular


def _gun_adlari(slots: list[Slot]) -> dict[int, str]:
    return {s.day_index: s.day_name for s in slots}


def _en_uzun_ardisik(
    slots: list[Slot], gunler: dict[int, list[int]], engelli: frozenset[int]
) -> int:
    """Engelli saatler çıkarıldığında bir gün içindeki en uzun kesintisiz dizi."""
    en_uzun = 0
    for gun_slotlari in gunler.values():
        uzunluk = 0
        onceki: int | None = None
        for si in gun_slotlari:
            if slots[si].period_id in engelli:
                uzunluk, onceki = 0, None
                continue
            bitisik = onceki is not None and slots[si].period_index - onceki == 1
            uzunluk = uzunluk + 1 if bitisik else 1
            onceki = slots[si].period_index
            en_uzun = max(en_uzun, uzunluk)
    return en_uzun


def _gun_siniri_kapasitesi(
    slots: list[Slot], gunler: dict[int, list[int]], kapali: frozenset[int],
    yarim_gun_siniri: int,
) -> int:
    """Öğretmenin gün sınırı içinde verebileceği EN FAZLA ders saati.

    Her gün için dört seçenek var: uğrama, yalnız sabah, yalnız öğleden sonra,
    tam gün. Seçim iki bütçeyle sınırlı — ayrı gün sayısı ve toplam yarım gün.
    Küçük bir dinamik programlama tam sonucu verir (en çok 7 gün), böylece
    "sığmıyor" dediğimizde gerçekten sığmıyordur.
    """
    gun_tavani = -(-yarim_gun_siniri // 2)

    # (kullanilan_gun, kullanilan_yarim) -> en çok saat
    durumlar: dict[tuple[int, int], int] = {(0, 0): 0}
    for gun_slotlari in gunler.values():
        musait = [si for si in gun_slotlari if slots[si].period_id not in kapali]
        sabah = sum(1 for si in musait if slots[si].sabah)
        oglenden = len(musait) - sabah

        yeni: dict[tuple[int, int], int] = {}
        for (g, y), saat in durumlar.items():
            secenekler = [(0, 0, 0)]                      # uğrama
            if sabah:
                secenekler.append((1, 1, sabah))
            if oglenden:
                secenekler.append((1, 1, oglenden))
            if sabah or oglenden:
                secenekler.append((1, 2, sabah + oglenden))
            for dg, dy, ds in secenekler:
                anahtar = (g + dg, y + dy)
                if anahtar[0] > gun_tavani or anahtar[1] > yarim_gun_siniri:
                    continue
                if yeni.get(anahtar, -1) < saat + ds:
                    yeni[anahtar] = saat + ds
        durumlar = yeni

    return max(durumlar.values(), default=0)


def on_kontrol(
    slots: list[Slot],
    lessons: list[Lesson],
    gun_sinirlari: dict[int, int] | None = None,
) -> list[dict]:
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
            "baslik": "Hiç ders ataması yok",
            "detay": "Şubelere henüz ders atanmamış. Ders Atamaları bölümünden "
                     "her şubeye dersleri ve öğretmenlerini ekleyin.",
            "onem": "engel",
        }]

    gunler = _gune_gore(slots)
    gun_adlari = _gun_adlari(slots)
    toplam_slot = len(slots)

    # Ortak dersler (birleştirme kuralı) yük sayımlarına girmez: saatleri
    # ebeveynlerde zaten sayılı. Öğretmen yükü kuralın düşürebileceği kadar
    # hafifletilir; kuralın kendisi ayrıca sınanır.
    bulgular.extend(kural_bulgulari(slots, lessons))
    indirim = birlesme_indirimi(lessons)
    lessons = [l for l in lessons if not l.ortak]

    # --- Şube kapasitesi (şubenin kapattığı saatler düşülerek) ---
    sube_yuku: dict[int, int] = defaultdict(int)
    sube_adi: dict[int, str] = {}
    sube_kapali: dict[int, frozenset[int]] = {}
    for l in lessons:
        # Birleşik ders her şubenin yükünü ayrı ayrı doldurur: 9-A+9-B ortak
        # beden dersi ikisinin de haftalık saatinden yer alır.
        for si, ad in sube_ciftleri(l):
            sube_yuku[si] += l.weekly_hours
            sube_adi[si] = ad
            sube_kapali[si] = sube_kapali_saatleri(l, si)

    for sid, yuk in sube_yuku.items():
        kapali = sube_kapali.get(sid, frozenset())
        musait = toplam_slot - len(kapali)
        if yuk <= musait:
            continue
        if kapali:
            detay = (f"Şubenin haftalık ders yükü {yuk} saat. Müsaitlik matrisinde "
                     f"{len(kapali)} saat kapatıldığı için haftada {musait} saate "
                     f"ders konabiliyor. {yuk - musait} saat fazla.")
        else:
            detay = (f"Şubenin haftalık ders yükü {yuk} saat, ama haftada yalnızca "
                     f"{toplam_slot} ders saati tanımlı. {yuk - toplam_slot} saat fazla.")
        bulgular.append({
            "kod": "sube_kapasite",
            "baslik": f"{sube_adi[sid]} şubesine haftada sığmayacak kadar ders var",
            "detay": detay,
            "onem": "engel",
            "sube": sube_adi[sid],
            "gereken": yuk,
            "mevcut": musait,
        })

    # --- Öğretmen kapasitesi ---
    ogretmen_yuku: dict[int, int] = defaultdict(int)
    ogretmen_adi: dict[int, str] = {}
    ogretmen_kapali: dict[int, frozenset[int]] = {}
    for l in lessons:
        ogretmen_yuku[l.teacher_id] += l.weekly_hours
        ogretmen_adi[l.teacher_id] = l.teacher_name
        ogretmen_kapali[l.teacher_id] = l.blocked_period_ids

    for tid, ham_yuk in ogretmen_yuku.items():
        yuk = ham_yuk - indirim.get(tid, 0)
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

    # --- Akış kontrolü: dersler gerçekten sığabilecekleri saatlere sığıyor mu ---
    # Sayımla yakalanmayan asıl tıkanma: öğretmenin dersleri dar pencereli
    # şubelerde toplanmış, ya da şubenin öğretmenleri şubenin açık saatlerinde
    # yok. Zaten kapasite engeli yazılan kaynaklar tekrarlanmaz.
    from app.solver import akis
    bildirilen_ogr = {b["ogretmen"] for b in bulgular if b["kod"] == "ogretmen_kapasite"}
    bildirilen_sube = {b["sube"] for b in bulgular if b["kod"] == "sube_kapasite"}
    bulgular.extend(akis.ogretmen_bulgulari(
        slots, lessons,
        atla={tid for tid, ad in ogretmen_adi.items() if ad in bildirilen_ogr},
        indirim=indirim,
    ))
    bulgular.extend(akis.sube_bulgulari(
        slots, lessons,
        atla={sid for sid, ad in sube_adi.items() if ad in bildirilen_sube},
    ))

    # --- Blok ders gün içine sığıyor mu (dersin kendi kapalı saatlerine göre) ---
    for l in lessons:
        boy = max(l.blocks, default=1)
        if boy < 2:
            continue
        en_uzun = _en_uzun_ardisik(slots, gunler, l.engelli_period_ids)
        if boy > en_uzun:
            bulgular.append({
                "kod": "blok_sigmiyor",
                "baslik": f"{l.section_name} · {l.subject_name} blok dersi hiçbir güne sığmıyor",
                "detay": f"{boy} saatlik blok isteniyor, ama {l.teacher_name} öğretmenin "
                         f"ve {l.section_name} şubesinin ortak müsait olduğu en uzun "
                         f"kesintisiz dizi {en_uzun} saat. Teneffüsler ya da kapalı "
                         f"saatler diziyi bölüyor.",
                "onem": "engel",
                "sube": l.section_name,
                "ders": l.subject_name,
            })

    # --- Şubenin tamamen kapalı olmadığı gün sayısı ---
    for sid, kapali in sube_kapali.items():
        if not kapali:
            continue
        acik_gun = [
            gun_adlari[gi]
            for gi, idx in gunler.items()
            if any(slots[si].period_id not in kapali for si in idx)
        ]
        if not acik_gun:
            bulgular.append({
                "kod": "sube_tamamen_kapali",
                "baslik": f"{sube_adi[sid]} şubesinin hiçbir saati açık değil",
                "detay": "Müsaitlik matrisinde tüm ders saatleri kapatılmış. "
                         "Şubeye ders yerleştirilemez.",
                "onem": "engel",
                "sube": sube_adi[sid],
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

    # --- Gün sınırı haftalık yükü taşıyor mu ---
    for tid, yarim_gun in (gun_sinirlari or {}).items():
        yuk = ogretmen_yuku.get(tid, 0) - indirim.get(tid, 0)
        if not yuk:
            continue
        tavan = _gun_siniri_kapasitesi(
            slots, gunler, ogretmen_kapali.get(tid, frozenset()), yarim_gun
        )
        if yuk <= tavan:
            continue
        gun_metni = f"{yarim_gun / 2:g}".replace(".", ",")
        bulgular.append({
            "kod": "ogretmen_gun_siniri",
            "baslik": f"{ogretmen_adi[tid]} öğretmenin yükü {gun_metni} güne sığmıyor",
            "detay": (
                f"Haftada {yuk} saat ders veriyor, ama {gun_metni} günlük sınırla "
                f"ve müsait saatleriyle en çok {tavan} saat yerleşebilir. "
                f"{yuk - tavan} saat fazla. Gün sınırı yükseltilmezse program "
                f"kurulurken bu sınır aşılacak."
            ),
            # Sınır esnetilebilir olduğu için bu bir engel değil: program yine
            # çıkar, ama anlaşmanın dışına taşarak.
            "onem": "uyari",
            "ogretmen": ogretmen_adi[tid],
            "gereken": yuk,
            "mevcut": tavan,
        })

    # --- Öğretmen bazında gün gün darboğaz ---
    for tid, kapali in ogretmen_kapali.items():
        yuk = ogretmen_yuku[tid] - indirim.get(tid, 0)
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
    gun_sinirlari: dict[int, int] | None = None,
    celisenler: list | None = None,
    ek_bulgular: list[dict] | None = None,
) -> dict:
    """Ön kontrolleri ve çözücü sonucunu tek yapılandırılmış rapora toplar."""
    bulgular = list(ek_bulgular or []) + on_kontrol(slots, lessons, gun_sinirlari)
    ders_by_id = {l.entry_id: l for l in lessons}

    yerlesmeyenler = []
    for entry_id, saat in sorted(unplaced.items(), key=lambda kv: -kv[1]):
        l = ders_by_id.get(entry_id)
        if l is None:
            continue
        sube = sube_etiketi(l)
        istenen = l.kural_saat if l.ortak else l.weekly_hours
        yerlesmeyenler.append({
            "sube": sube,
            "ders": l.subject_name + (" (ortak)" if l.ortak else ""),
            "ogretmen": l.teacher_name,
            "istenen_saat": istenen,
            "yerlesmeyen_saat": saat,
        })
        bulgular.append({
            "kod": "yerlesemedi",
            "baslik": f"{sube} · {l.subject_name}: {saat} saat yerleşemedi",
            "detay": (f"{sube} birleştirme kuralının {istenen} ortak saatinin {saat} "
                      f"saati konamadı: seçilen günlerde öğretmen ya da şubeler dolu."
                      if l.ortak else
                      f"{l.teacher_name} öğretmenle {l.weekly_hours} saatin "
                      f"{saat} saati boş kaldı. Bu dersin öğretmeni ya da şubesi "
                      f"o saatlerde başka bir dersle dolu."),
            "onem": "uyari",
            "sube": sube,
            "ders": l.subject_name,
            "ogretmen": l.teacher_name,
        })

    return {
        "durum": status_name,
        "sure_sn": round(seconds, 2),
        "ozet": {
            "ders_saati_sayisi": len(slots),
            "gun_sayisi": len({s.day_index for s in slots}),
            "ders_atamasi": len(lessons),
            "toplam_ders_saati": sum(l.weekly_hours for l in lessons if not l.ortak),
            "sube_sayisi": len({l.section_id for l in lessons if not l.ortak}),
            "ogretmen_sayisi": len({l.teacher_id for l in lessons if not l.ortak}),
            "yerlesmeyen_toplam": sum(unplaced.values()),
        },
        "bulgular": bulgular,
        "yerlesmeyenler": yerlesmeyenler,
        # Çözümsüzlük kanıtlandığında: hangi kısıtlar BİRLİKTE çelişiyor ve
        # hangisini tek başına değiştirmek yetiyor.
        "sikisiklik": sikisiklik_onerileri(slots, lessons, unplaced),
        "celiskiler": [
            {"tur": c.tur, "metin": c.metin, "oneri": c.oneri,
             "tek_basina_yeterli": c.tek_basina_yeterli}
            for c in (celisenler or [])
        ],
    }


def sikisiklik_onerileri(
    slots: list[Slot], lessons: list[Lesson], unplaced: dict[int, int]
) -> list[dict]:
    """Yerleşemeyen derslerin en sıkışık kaynakları — çekirdek bulunamadığında.

    Kesin bir çelişki kanıtı yoksa bile gevşek çözüm hangi derslerin dışarıda
    kaldığını söyler. O derslerin öğretmeni için "yük / açık saat" oranına
    bakılır: oran yüksekse o öğretmenin müsaitliğini açmak ya da yükünü
    azaltmak en olası çıkış yoludur. Kanıt değildir; öyle de sunulur.

    Şubeler listelenmez: şubenin programı tasarım gereği tam dolar, yükü açık
    saatine eşittir ve oran hep %100 çıkar. Yükün açık saati aştığı durumu
    ön kontrol zaten engel olarak bildirir.
    """
    if not unplaced:
        return []

    toplam = len(slots)
    ogretmen_yuk: dict[int, int] = defaultdict(int)
    for l in lessons:
        if not l.ortak:
            ogretmen_yuk[l.teacher_id] += l.weekly_hours

    ders_by_id = {l.entry_id: l for l in lessons}
    adaylar: dict[tuple[str, int], dict] = {}
    for entry_id in unplaced:
        l = ders_by_id.get(entry_id)
        if l is None:
            continue
        ogr_acik = toplam - len(l.blocked_period_ids)
        oran = ogretmen_yuk[l.teacher_id] / ogr_acik if ogr_acik else 9.9
        adaylar.setdefault(("ogretmen", l.teacher_id), {
            "tur": "ogretmen", "oran": oran, "ad": l.teacher_name,
            "yuk": ogretmen_yuk[l.teacher_id], "acik": ogr_acik,
            "kisitli": bool(l.blocked_period_ids),
        })

    sirali = sorted(adaylar.values(), key=lambda a: -a["oran"])[:6]
    sonuc = []
    for a in sirali:
        # Hiç açık saati olmayan kaynakta yüzde anlamsız: 100 üstü gösterilir.
        yuzde = min(round(a["oran"] * 100), 999) if a["acik"] else 999
        acik = f"{a['acik']} açık saati var" if a["acik"] else "hiç açık saati yok"
        metin = f"{a['ad']}: haftalık {a['yuk']} saat yükü, {acik}"
        if a["acik"]:
            metin += f" (%{yuzde})"
        # Kapalı saati olmayan öğretmene "saat açın" demek anlamsız: onun
        # sıkışıklığı başka şubelerle çakışmadan gelir, çare yükü paylaşmak.
        if a["kisitli"]:
            oneri = (f"{a['ad']} öğretmeninin müsaitlik matrisinde birkaç saat açın "
                     f"ya da yükünü başka öğretmene aktarın")
        else:
            oneri = f"{a['ad']} öğretmeninin yükünün bir kısmını başka öğretmene aktarın"
        sonuc.append({"tur": a["tur"], "metin": metin, "oneri": oneri, "oran": yuzde})
    return sonuc
