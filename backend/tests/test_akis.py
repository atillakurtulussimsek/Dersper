"""Akış kontrolü: dersler sığabilecekleri saatlere gerçekten sığıyor mu?"""
from app.solver.akis import darbogaz, ogretmen_bulgulari, sube_bulgulari
from app.solver.diagnose import on_kontrol
from app.solver.engine import Lesson
from tests.test_engine import izgara


def _ders(eid, sube, ogr, ad, saat, sube_kapali=(), ogr_kapali=(), ek_sube=None):
    subeler = ((sube, f"{sube}-A"),) + (((ek_sube, f"{ek_sube}-A"),) if ek_sube else ())
    return Lesson(
        entry_id=eid, section_id=sube, section_name=f"{sube}-A",
        teacher_id=ogr, teacher_name=f"Öğretmen {ogr}", subject_name=ad,
        weekly_hours=saat, blocks=(1,) * saat, max_per_day=2,
        sections=subeler if ek_sube else (),
        blocked_period_ids=frozenset(ogr_kapali),
        section_blocked_period_ids=frozenset(sube_kapali),
        section_blocked_map=tuple((si, frozenset(sube_kapali)) for si, _ in subeler),
    )


def test_ayni_dar_pencereye_sikisan_dersler_yakalanir():
    slots = izgara()                                   # 40 saat
    pencere = {s.period_id for s in slots[:4]}         # 3 şube de yalnız ilk 4 saat açık
    kapali = [s.period_id for s in slots if s.period_id not in pencere]
    dersler = [_ders(i, i, 10, "Matematik", 2, sube_kapali=kapali) for i in (1, 2, 3)]
    d = darbogaz(slots, dersler)
    assert d is not None
    assert (d.gereken, d.sigan, d.fazla) == (6, 4, 2)
    assert {l.section_id for l in d.dersler} == {1, 2, 3}

    b = ogretmen_bulgulari(slots, dersler)
    assert len(b) == 1 and b[0]["kod"] == "ogretmen_akis"
    assert "2 saat fazla" in b[0]["detay"]
    assert "en az 2 saatini başka öğretmene" in b[0]["oneri"]


def test_darbogaz_kumesi_rahat_dersleri_disarida_birakir():
    slots = izgara()
    pencere = {s.period_id for s in slots[:4]}
    kapali = [s.period_id for s in slots if s.period_id not in pencere]
    sikisik = [_ders(i, i, 10, "Matematik", 3, sube_kapali=kapali) for i in (1, 2)]
    rahat = _ders(9, 9, 10, "Matematik", 5)            # her yere sığar
    d = darbogaz(slots, sikisik + [rahat])
    assert d is not None
    assert {l.section_id for l in d.dersler} == {1, 2}
    assert (d.gereken, d.sigan) == (6, 4)


def test_sayimla_rahat_gorunen_ogretmen_akista_yakalanir():
    """Sayım: 6 yük / 40 açık. Akış: 6 yük / 4 saat."""
    slots = izgara()
    pencere = {s.period_id for s in slots[:4]}
    kapali = [s.period_id for s in slots if s.period_id not in pencere]
    dersler = [_ders(i, i, 10, "Matematik", 2, sube_kapali=kapali) for i in (1, 2, 3)]
    kodlar = [b["kod"] for b in on_kontrol(slots, dersler)]
    assert "ogretmen_kapasite" not in kodlar
    assert "ogretmen_akis" in kodlar


def test_sigan_dersler_bulgu_uretmez():
    slots = izgara()
    dersler = [_ders(i, i, 10, "Matematik", 5) for i in (1, 2, 3)]
    assert darbogaz(slots, dersler) is None
    assert ogretmen_bulgulari(slots, dersler) == []
    assert sube_bulgulari(slots, dersler) == []


def test_birlesik_ders_bir_kez_sayilir():
    slots = izgara()
    pencere = {s.period_id for s in slots[:4]}
    kapali = [s.period_id for s in slots if s.period_id not in pencere]
    ortak = _ders(1, 1, 10, "Beden", 4, sube_kapali=kapali, ek_sube=2)
    assert darbogaz(slots, [ortak]) is None            # 4 saat, 4 saat açık


def test_subenin_ogretmenleri_acik_saatlerde_yoksa_yakalanir():
    slots = izgara()
    acik = [s.period_id for s in slots[:6]]            # şube 6 saat açık
    sube_kapali = [s.period_id for s in slots if s.period_id not in acik]
    # İki öğretmen de şubenin ilk saatinde yok: 5 saate 6 saat ders.
    ogr_kapali = [acik[0]]
    dersler = [
        _ders(1, 1, 10, "Matematik", 3, sube_kapali=sube_kapali, ogr_kapali=ogr_kapali),
        _ders(2, 1, 11, "Türkçe", 3, sube_kapali=sube_kapali, ogr_kapali=ogr_kapali),
    ]
    b = sube_bulgulari(slots, dersler)
    assert len(b) == 1 and b[0]["kod"] == "sube_akis"
    assert (b[0]["gereken"], b[0]["mevcut"]) == (6, 5)
    assert "1 saat müsaitlik açın" in b[0]["oneri"]


def test_kapasite_engeli_yazilan_kaynak_tekrarlanmaz():
    slots = izgara()
    kapali = [s.period_id for s in slots[:38]]          # öğretmene 2 saat açık
    dersler = [_ders(1, 1, 10, "Matematik", 5, ogr_kapali=kapali)]
    kodlar = [b["kod"] for b in on_kontrol(slots, dersler)]
    assert kodlar.count("ogretmen_kapasite") == 1
    assert "ogretmen_akis" not in kodlar
