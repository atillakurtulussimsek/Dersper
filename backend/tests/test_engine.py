"""Çözücü ve tanı katmanı testleri. Veritabanı gerektirmez."""
from app.bloklar import coz
from app.solver.diagnose import on_kontrol, rapor_olustur
from app.solver.engine import Lesson, Slot, SolveInput, solve
from app.solver.loader import sabah_mi

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]


def izgara(gun_sayisi: int = 5, ders_sayisi: int = 8) -> list[Slot]:
    """Öğle arası tanımlanmamış bir ızgara: gün ortadan ikiye bölünür."""
    sabah_siniri = -(-ders_sayisi // 2)
    slots, pid = [], 1
    for g in range(gun_sayisi):
        for p in range(ders_sayisi):
            slots.append(Slot(pid, g, p, GUNLER[g], f"{p + 1}. ders",
                              sabah=p < sabah_siniri))
            pid += 1
    return slots


def _dizi_uzunluklari(slots, placements) -> list[int]:
    """Yerleşimlerdeki kesintisiz blok uzunlukları, örn. [2, 2, 1]."""
    konum = {s.period_id: (s.day_index, s.period_index) for s in slots}
    gunluk: dict[int, list[int]] = {}
    for _, pid in placements:
        gun, saat = konum[pid]
        gunluk.setdefault(gun, []).append(saat)

    uzunluklar: list[int] = []
    for saatler in gunluk.values():
        saatler.sort()
        uzunluk = 1
        for a, b in zip(saatler, saatler[1:]):
            if b - a == 1:
                uzunluk += 1
            else:
                uzunluklar.append(uzunluk)
                uzunluk = 1
        uzunluklar.append(uzunluk)
    return uzunluklar


def ders(entry_id, sube, ogretmen, ad, saat, desen="", gunluk=2, kapali=()):
    return Lesson(
        entry_id=entry_id, section_id=sube, section_name=f"{sube}-A",
        teacher_id=ogretmen, teacher_name=f"Öğretmen {ogretmen}",
        subject_name=ad, weekly_hours=saat, blocks=tuple(coz(desen, saat)),
        max_per_day=gunluk, blocked_period_ids=frozenset(kapali),
    )


def test_kucuk_okul_cozulur():
    slots = izgara()
    dersler = [
        ders(1, 1, 10, "Matematik", 5),
        ders(2, 1, 11, "Türkçe", 5),
        ders(3, 1, 12, "Fen", 4, desen="2+2"),
        ders(4, 2, 10, "Matematik", 5),
        ders(5, 2, 11, "Türkçe", 5),
    ]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok, sonuc.status_name
    assert not sonuc.unplaced
    assert len(sonuc.placements) == sum(d.weekly_hours for d in dersler)


def test_sube_ve_ogretmen_cakismaz():
    slots = izgara(gun_sayisi=2, ders_sayisi=4)
    dersler = [ders(1, 1, 10, "Matematik", 4), ders(2, 1, 11, "Türkçe", 4)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    # aynı şube aynı saatte iki derste olamaz
    saatler = [pid for _, pid in sonuc.placements]
    assert len(saatler) == len(set(saatler))


def test_bloklar_ardisik_yerlesir():
    slots = izgara(gun_sayisi=1, ders_sayisi=6)
    dersler = [ders(1, 1, 10, "Fen", 4, desen="2+2", gunluk=4)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    yerler = sorted(pid for _, pid in sonuc.placements)
    ikili = [yerler[:2], yerler[2:]]
    assert all(b - a == 1 for a, b in ikili)


def test_kapasite_asimi_tespit_edilir():
    slots = izgara(gun_sayisi=5, ders_sayisi=4)     # haftada 20 saat
    dersler = [ders(1, 1, 10, "Matematik", 25, gunluk=10)]
    bulgular = on_kontrol(slots, dersler)
    kodlar = {b["kod"] for b in bulgular}
    assert "sube_kapasite" in kodlar
    assert "ogretmen_kapasite" in kodlar


def test_gunluk_sinir_tespit_edilir():
    slots = izgara()
    dersler = [ders(1, 1, 10, "Matematik", 15, gunluk=2)]   # 5 gün × 2 = 10 < 15
    kodlar = {b["kod"] for b in on_kontrol(slots, dersler)}
    assert "gunluk_sinir" in kodlar


def test_cozumsuz_durumda_yerlesmeyenler_raporlanir():
    """Tek öğretmen iki şubede kapasitesinin üstünde ders veriyor."""
    slots = izgara(gun_sayisi=2, ders_sayisi=4)     # 8 saat
    dersler = [
        ders(1, 1, 10, "Matematik", 6, gunluk=4),
        ders(2, 2, 10, "Matematik", 6, gunluk=4),
    ]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert not sonuc.ok
    assert sum(sonuc.unplaced.values()) == 4     # 12 saat istendi, 8 saat var

    rapor = rapor_olustur(slots, dersler, sonuc.unplaced, sonuc.status_name,
                          sonuc.seconds)
    assert rapor["ozet"]["yerlesmeyen_toplam"] == 4
    assert any(b["kod"] == "ogretmen_kapasite" for b in rapor["bulgular"])
    assert rapor["yerlesmeyenler"]


def test_musait_olmayan_saate_ders_konmaz():
    slots = izgara(gun_sayisi=1, ders_sayisi=7)
    kapali = {slots[0].period_id, slots[1].period_id}
    dersler = [ders(1, 1, 10, "Matematik", 3, kapali=kapali, gunluk=3)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    assert not ({pid for _, pid in sonuc.placements} & kapali)


def test_bos_izgara_engel_olarak_bildirilir():
    kodlar = {b["kod"] for b in on_kontrol([], [])}
    assert "zaman_izgarasi_bos" in kodlar


def ders_sube_kapali(entry_id, sube, ogretmen, ad, saat, desen="", gunluk=2,
                     ogretmen_kapali=(), sube_kapali=()):
    return Lesson(
        entry_id=entry_id, section_id=sube, section_name=f"{sube}-A",
        teacher_id=ogretmen, teacher_name=f"Öğretmen {ogretmen}",
        subject_name=ad, weekly_hours=saat, blocks=tuple(coz(desen, saat)),
        max_per_day=gunluk,
        blocked_period_ids=frozenset(ogretmen_kapali),
        section_blocked_period_ids=frozenset(sube_kapali),
    )


def test_sube_kapali_saate_ders_konmaz():
    """Akşamcı şube: günün ilk yarısı kapalı."""
    slots = izgara(gun_sayisi=5, ders_sayisi=8)
    aksam_disi = frozenset(s.period_id for s in slots if s.period_index < 4)
    dersler = [
        ders_sube_kapali(1, 1, 10, "Matematik", 8, gunluk=2, sube_kapali=aksam_disi),
    ]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok, sonuc.status_name
    assert not ({pid for _, pid in sonuc.placements} & aksam_disi)


def test_sube_ve_ogretmen_kapaliligi_birlesir():
    slots = izgara(gun_sayisi=1, ders_sayisi=6)
    sube_kapali = frozenset({slots[0].period_id, slots[1].period_id})
    ogretmen_kapali = frozenset({slots[5].period_id})
    dersler = [
        ders_sube_kapali(1, 1, 10, "Fen", 3, desen="3", gunluk=3,
                         ogretmen_kapali=ogretmen_kapali, sube_kapali=sube_kapali),
    ]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    # geriye yalnızca 3., 4. ve 5. ders saatleri kalır; 3 saatlik tek blok oraya oturur
    assert {pid for _, pid in sonuc.placements} == {
        slots[2].period_id, slots[3].period_id, slots[4].period_id
    }


def test_sube_kapasitesi_kapali_saatler_dusulerek_hesaplanir():
    slots = izgara(gun_sayisi=5, ders_sayisi=8)          # 40 saat
    yarim = frozenset(s.period_id for s in slots if s.period_index < 4)  # 20 saat kapalı
    dersler = [
        ders_sube_kapali(1, 1, 10, "Matematik", 25, gunluk=5, sube_kapali=yarim),
    ]
    bulgu = next(b for b in on_kontrol(slots, dersler) if b["kod"] == "sube_kapasite")
    assert bulgu["mevcut"] == 20
    assert bulgu["gereken"] == 25
    assert "kapatıldığı" in bulgu["detay"]


def test_tamamen_kapali_sube_bildirilir():
    slots = izgara(gun_sayisi=2, ders_sayisi=4)
    hepsi = frozenset(s.period_id for s in slots)
    dersler = [ders_sube_kapali(1, 1, 10, "Matematik", 2, sube_kapali=hepsi)]
    kodlar = {b["kod"] for b in on_kontrol(slots, dersler)}
    assert "sube_tamamen_kapali" in kodlar


def test_blok_kapali_saatlerle_bolununce_bildirilir():
    """Şube yalnızca tek tek saatler açık bırakırsa çift ders sığmaz."""
    slots = izgara(gun_sayisi=5, ders_sayisi=8)
    tek_saatler = frozenset(s.period_id for s in slots if s.period_index % 2 == 1)
    dersler = [
        ders_sube_kapali(1, 1, 10, "Fen", 4, desen="2+2", gunluk=4, sube_kapali=tek_saatler),
    ]
    bulgu = next(b for b in on_kontrol(slots, dersler) if b["kod"] == "blok_sigmiyor")
    assert "1 saat" in bulgu["detay"]


def test_serbest_blok_deseni_uygulanir():
    """5 saatlik ders 2+2+1 olarak istenirse tam olarak öyle yerleşir."""
    slots = izgara(gun_sayisi=5, ders_sayisi=8)
    dersler = [ders(1, 1, 10, "Matematik", 5, desen="2+2+1", gunluk=2)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok

    assert sorted(_dizi_uzunluklari(slots, sonuc.placements), reverse=True) == [2, 2, 1]


def test_desen_tek_saatlere_bolunebilir():
    slots = izgara(gun_sayisi=5, ders_sayisi=8)
    dersler = [ders(1, 1, 10, "Türkçe", 5, desen="1+1+1+1+1", gunluk=1)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    konum = {s.period_id: s.day_index for s in slots}
    gunler = [konum[pid] for _, pid in sonuc.placements]
    assert len(set(gunler)) == 5          # günde bir saat kuralı gereği beş ayrı gün


def test_uc_saatlik_blok_yerlesir():
    slots = izgara(gun_sayisi=5, ders_sayisi=8)
    dersler = [ders(1, 1, 10, "Atölye", 6, desen="3+3", gunluk=3)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    konum = {s.period_id: (s.day_index, s.period_index) for s in slots}
    gunluk: dict[int, list[int]] = {}
    for _, pid in sonuc.placements:
        gun, saat = konum[pid]
        gunluk.setdefault(gun, []).append(saat)
    assert len(gunluk) == 2               # iki ayrı gün, günde 3 saat
    for saatler in gunluk.values():
        saatler.sort()
        assert len(saatler) == 3
        assert saatler[2] - saatler[0] == 2   # kesintisiz


def test_ayni_dersin_bloklari_arka_arkaya_gelmez():
    """"2+2" deseni gün içinde 4 saatlik tek bloğa dönüşmemeli."""
    slots = izgara(gun_sayisi=1, ders_sayisi=8)
    dersler = [ders(1, 1, 10, "Fen", 4, desen="2+2", gunluk=4)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    assert sorted(_dizi_uzunluklari(slots, sonuc.placements)) == [2, 2]


def test_tek_saatler_ayni_gunde_bitisik_olmaz():
    slots = izgara(gun_sayisi=1, ders_sayisi=8)
    dersler = [ders(1, 1, 10, "Türkçe", 3, desen="1+1+1", gunluk=3)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    assert _dizi_uzunluklari(slots, sonuc.placements) == [1, 1, 1]


def test_esnek_kip_kapaliyken_gunluk_sinir_asilmaz():
    """Bir günde 6 saat gerekiyor ama sınır 2: sert modelde yerleşemez."""
    slots = izgara(gun_sayisi=1, ders_sayisi=8)
    dersler = [ders(1, 1, 10, "Matematik", 6, gunluk=2)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert not sonuc.ok
    assert sonuc.relaxations == []


def test_esnek_kip_gunluk_siniri_asarak_yerlestirir():
    slots = izgara(gun_sayisi=1, ders_sayisi=8)
    dersler = [ders(1, 1, 10, "Matematik", 4, gunluk=2)]
    sonuc = solve(SolveInput(
        slots=slots, lessons=dersler, time_limit_seconds=20, esnek_gunluk=True,
    ))
    assert sonuc.ok
    assert len(sonuc.placements) == 4
    # Esnetme raporlanır: 1 numaralı satır, 0. gün, 4 saat kondu, sınır 2 idi.
    assert sonuc.relaxations == [(1, 0, 4, 2)]
    # Araya başka ders girsin diye saatler bitişik olmaz.
    assert _dizi_uzunluklari(slots, sonuc.placements) == [1, 1, 1, 1]


def test_esnek_kip_gereksizse_devreye_girmez():
    slots = izgara(gun_sayisi=5, ders_sayisi=8)
    dersler = [ders(1, 1, 10, "Matematik", 4, gunluk=2)]
    sonuc = solve(SolveInput(
        slots=slots, lessons=dersler, time_limit_seconds=20, esnek_gunluk=True,
    ))
    assert sonuc.ok
    assert sonuc.relaxations == []      # sert model zaten çözdü


def test_esnek_kip_asimi_en_aza_indirir():
    """8 saat, günlük sınır 2, iki gün var: aşım mümkün olduğunca küçük olmalı."""
    slots = izgara(gun_sayisi=2, ders_sayisi=8)
    dersler = [ders(1, 1, 10, "Matematik", 6, gunluk=2)]
    sonuc = solve(SolveInput(
        slots=slots, lessons=dersler, time_limit_seconds=20, esnek_gunluk=True,
    ))
    assert sonuc.ok
    toplam_asim = sum(konan - sinir for _, _, konan, sinir in sonuc.relaxations)
    assert toplam_asim == 2      # 6 saat, 2 günde 4 saat sınır → en az 2 aşım


# --- Öğretmenin haftalık gün sınırı ---

def _ogretmen_gunleri(slots, placements, dersler, ogretmen_id) -> set[int]:
    """Öğretmenin ders verdiği ayrı günler."""
    konum = {s.period_id: s for s in slots}
    benim = {d.entry_id for d in dersler if d.teacher_id == ogretmen_id}
    return {konum[pid].day_index for eid, pid in placements if eid in benim}


def _ogretmen_yarimlari(slots, placements, dersler, ogretmen_id) -> set[tuple[int, bool]]:
    """Öğretmenin bulunduğu (gün, sabah mı) yarım günleri."""
    konum = {s.period_id: s for s in slots}
    benim = {d.entry_id for d in dersler if d.teacher_id == ogretmen_id}
    return {
        (konum[pid].day_index, konum[pid].sabah)
        for eid, pid in placements
        if eid in benim
    }


def test_gun_siniri_ogretmene_bos_gun_birakir():
    """4 gün sınırı olan öğretmen 5 güne yayılmaz."""
    slots = izgara()
    dersler = [
        ders(1, 1, 10, "Matematik", 8, gunluk=2),
        ders(2, 2, 11, "Türkçe", 10, gunluk=2),
    ]
    sonuc = solve(SolveInput(
        slots=slots, lessons=dersler, ogretmen_yarim_gun={10: 8},
        time_limit_seconds=20,
    ))
    assert sonuc.ok, sonuc.status_name
    assert len(_ogretmen_gunleri(slots, sonuc.placements, dersler, 10)) <= 4
    # Sınırı olmayan öğretmen etkilenmez.
    assert len(_ogretmen_gunleri(slots, sonuc.placements, dersler, 11)) == 5


def test_yarim_gun_siniri_uygulanir():
    """4,5 gün = 9 yarım gün: 5 güne yayılsa bile biri yarım kalır."""
    slots = izgara()
    # Günde en fazla 2 saat × 10 saat → en az 5 gün gerekiyor.
    dersler = [ders(1, 1, 10, "Matematik", 10, gunluk=2)]
    sonuc = solve(SolveInput(
        slots=slots, lessons=dersler, ogretmen_yarim_gun={10: 9},
        time_limit_seconds=20,
    ))
    assert sonuc.ok, sonuc.status_name
    yarimlar = _ogretmen_yarimlari(slots, sonuc.placements, dersler, 10)
    assert len(_ogretmen_gunleri(slots, sonuc.placements, dersler, 10)) == 5
    assert len(yarimlar) <= 9


def test_gun_siniri_ogle_arasina_gore_bolunur():
    """Öğle arası erkene alınırsa yarım gün sınırı da oraya göre kayar."""
    # 6 ders saati; öğle arası 2. dersten sonra → sabah 2 saat, öğleden sonra 4.
    slots = []
    pid = 1
    for g in range(5):
        for p in range(6):
            slots.append(Slot(pid, g, p, GUNLER[g], f"{p + 1}. ders", sabah=p < 2))
            pid += 1
    dersler = [ders(1, 1, 10, "Matematik", 10, gunluk=2)]
    sonuc = solve(SolveInput(
        slots=slots, lessons=dersler, ogretmen_yarim_gun={10: 9},
        time_limit_seconds=20,
    ))
    assert sonuc.ok, sonuc.status_name
    yarimlar = _ogretmen_yarimlari(slots, sonuc.placements, dersler, 10)
    assert len(yarimlar) <= 9
    # Yarım kalan günde saatlerin hepsi tek dilimde olmalı.
    gunler = _ogretmen_gunleri(slots, sonuc.placements, dersler, 10)
    yarim_gunler = [g for g in gunler if sum(1 for y in yarimlar if y[0] == g) == 1]
    assert yarim_gunler, "en az bir gün yarım olmalıydı"


def test_gun_siniri_sigmiyorsa_esnetilir():
    """Yük sınıra sığmıyorsa program yine kurulur, sınır aşılarak."""
    # 2 gün (4 yarım) sınırı; 2 günde en çok 16 saat var, 20 saat isteniyor.
    slots = izgara()
    dersler = [ders(1, 1, 10, "Matematik", 20, gunluk=4)]
    kati = solve(SolveInput(
        slots=slots, lessons=dersler, ogretmen_yarim_gun={10: 4},
        time_limit_seconds=20,
    ))
    assert not kati.ok

    esnek = solve(SolveInput(
        slots=slots, lessons=dersler, ogretmen_yarim_gun={10: 4},
        time_limit_seconds=20, esnek_gunluk=True,
    ))
    assert esnek.ok, esnek.status_name
    assert len(esnek.placements) == 20
    assert len(_ogretmen_gunleri(slots, esnek.placements, dersler, 10)) > 2


def test_gun_siniri_gereksizse_programi_bozmaz():
    """Sınır haftadan genişse hiçbir şeyi değiştirmez."""
    slots = izgara()
    dersler = [
        ders(1, 1, 10, "Matematik", 5),
        ders(2, 1, 11, "Türkçe", 5),
    ]
    sonuc = solve(SolveInput(
        slots=slots, lessons=dersler, ogretmen_yarim_gun={10: 10, 11: 10},
        time_limit_seconds=20,
    ))
    assert sonuc.ok
    assert len(sonuc.placements) == 10


def test_gun_siniri_tani_raporunda_gorunur():
    slots = izgara()
    dersler = [ders(1, 1, 10, "Matematik", 20, gunluk=4)]
    bulgular = on_kontrol(slots, dersler, {10: 4})
    kodlar = [b["kod"] for b in bulgular]
    assert "ogretmen_gun_siniri" in kodlar
    bulgu = next(b for b in bulgular if b["kod"] == "ogretmen_gun_siniri")
    assert bulgu["mevcut"] == 16      # 2 gün × 8 saat
    assert bulgu["gereken"] == 20
    assert "2 gün" in bulgu["baslik"]


def test_gun_siniri_yetiyorsa_tani_sessiz():
    slots = izgara()
    dersler = [ders(1, 1, 10, "Matematik", 8, gunluk=2)]
    bulgular = on_kontrol(slots, dersler, {10: 8})
    assert not [b for b in bulgular if b["kod"] == "ogretmen_gun_siniri"]


# --- Sabah / öğleden sonra ayrımı ---

class _SahteSaat:
    """`sabah_mi` yalnızca bu dört alanı okur."""

    def __init__(self, pid, index, is_break=False, is_lunch=False):
        self.id, self.index = pid, index
        self.is_break, self.is_lunch = is_break, is_lunch


def test_ogle_arasi_gunu_boler():
    saatler = [
        _SahteSaat(1, 0), _SahteSaat(2, 1), _SahteSaat(3, 2, is_lunch=True),
        _SahteSaat(4, 3), _SahteSaat(5, 4),
    ]
    # Yalnızca ders saatleri sorulur: öğle arasının kendisi slot olmadığı için
    # onun değeri hiçbir yerde kullanılmaz.
    dersler = [p for p in saatler if not p.is_break and not p.is_lunch]
    assert [sabah_mi(saatler, p) for p in dersler] == [True, True, False, False]


def test_ogle_arasi_yoksa_ortadan_bolunur():
    saatler = [_SahteSaat(i + 1, i) for i in range(8)]
    assert [sabah_mi(saatler, p) for p in saatler] == [True] * 4 + [False] * 4


def test_tek_sayida_saatte_fazlalik_sabaha_yazilir():
    saatler = [_SahteSaat(i + 1, i) for i in range(7)]
    assert [sabah_mi(saatler, p) for p in saatler] == [True] * 4 + [False] * 3


def test_teneffusler_bolmede_sayilmaz():
    """Ortadan bölme ders saatlerine göre yapılır; teneffüs sayıyı kaydırmaz."""
    saatler = [
        _SahteSaat(1, 0), _SahteSaat(2, 1), _SahteSaat(3, 2, is_break=True),
        _SahteSaat(4, 3), _SahteSaat(5, 4),
    ]
    dersler = [p for p in saatler if not p.is_break]
    assert [sabah_mi(saatler, p) for p in dersler] == [True, True, False, False]
