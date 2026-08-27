"""Çözücü ve tanı katmanı testleri. Veritabanı gerektirmez."""
from app.solver.diagnose import on_kontrol, rapor_olustur
from app.solver.engine import Lesson, Slot, SolveInput, _bloklara_bol, solve

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma"]


def izgara(gun_sayisi: int = 5, ders_sayisi: int = 8) -> list[Slot]:
    slots, pid = [], 1
    for g in range(gun_sayisi):
        for p in range(ders_sayisi):
            slots.append(Slot(pid, g, p, GUNLER[g], f"{p + 1}. ders"))
            pid += 1
    return slots


def ders(entry_id, sube, ogretmen, ad, saat, blok=1, gunluk=2, kapali=()):
    return Lesson(
        entry_id=entry_id, section_id=sube, section_name=f"{sube}-A",
        teacher_id=ogretmen, teacher_name=f"Öğretmen {ogretmen}",
        subject_name=ad, weekly_hours=saat, block_size=blok, max_per_day=gunluk,
        blocked_period_ids=frozenset(kapali),
    )


def test_bloklara_bol():
    assert _bloklara_bol(5, 2) == [2, 2, 1]
    assert _bloklara_bol(4, 2) == [2, 2]
    assert _bloklara_bol(3, 1) == [1, 1, 1]
    assert _bloklara_bol(2, 5) == [2]      # blok, haftalık saati aşamaz


def test_kucuk_okul_cozulur():
    slots = izgara()
    dersler = [
        ders(1, 1, 10, "Matematik", 5),
        ders(2, 1, 11, "Türkçe", 5),
        ders(3, 1, 12, "Fen", 4, blok=2),
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
    dersler = [ders(1, 1, 10, "Fen", 4, blok=2, gunluk=4)]
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
    slots = izgara(gun_sayisi=1, ders_sayisi=5)
    kapali = {slots[0].period_id, slots[1].period_id}
    dersler = [ders(1, 1, 10, "Matematik", 3, kapali=kapali, gunluk=3)]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    assert not ({pid for _, pid in sonuc.placements} & kapali)


def test_bos_izgara_engel_olarak_bildirilir():
    kodlar = {b["kod"] for b in on_kontrol([], [])}
    assert "zaman_izgarasi_bos" in kodlar


def ders_sube_kapali(entry_id, sube, ogretmen, ad, saat, blok=1, gunluk=2,
                     ogretmen_kapali=(), sube_kapali=()):
    return Lesson(
        entry_id=entry_id, section_id=sube, section_name=f"{sube}-A",
        teacher_id=ogretmen, teacher_name=f"Öğretmen {ogretmen}",
        subject_name=ad, weekly_hours=saat, block_size=blok, max_per_day=gunluk,
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
        ders_sube_kapali(1, 1, 10, "Fen", 3, gunluk=3,
                         ogretmen_kapali=ogretmen_kapali, sube_kapali=sube_kapali),
    ]
    sonuc = solve(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=20))
    assert sonuc.ok
    # geriye yalnızca 3., 4. ve 5. ders saatleri kalır
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
        ders_sube_kapali(1, 1, 10, "Fen", 4, blok=2, gunluk=4, sube_kapali=tek_saatler),
    ]
    bulgu = next(b for b in on_kontrol(slots, dersler) if b["kod"] == "blok_sigmiyor")
    assert "1 saat" in bulgu["detay"]
