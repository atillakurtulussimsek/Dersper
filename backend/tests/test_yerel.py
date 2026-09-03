"""Yerel arama motoru: sert kurallara uyar, eksik saati düşürür."""
from app.solver import yerel
from app.solver.engine import SolveInput
from tests.test_engine import ders, izgara


def _dogrula(slots, lessons, sonuc):
    """Yerleşim CP-SAT'in sert kurallarını tutuyor mu?"""
    konum = {s.period_id: s for s in slots}
    by_entry = {l.entry_id: l for l in lessons}
    ogretmen, sube = set(), set()
    gunluk = {}
    for entry_id, pid in sonuc.placements:
        l = by_entry[entry_id]
        s = konum[pid]
        assert pid not in l.blocked_period_ids and pid not in l.section_blocked_period_ids
        assert (l.teacher_id, pid) not in ogretmen, "öğretmen çakışması"
        ogretmen.add((l.teacher_id, pid))
        assert (l.section_id, pid) not in sube, "şube çakışması"
        sube.add((l.section_id, pid))
        gunluk[(entry_id, s.day_index)] = gunluk.get((entry_id, s.day_index), 0) + 1
    for (entry_id, _), n in gunluk.items():
        assert n <= by_entry[entry_id].max_per_day


def test_kucuk_okulu_tam_yerlestirir():
    slots = izgara()
    dersler = [ders(1, 1, 10, "Matematik", 5, desen="2+2+1"),
               ders(2, 1, 11, "Türkçe", 5), ders(3, 2, 10, "Matematik", 4, desen="2+2"),
               ders(4, 2, 11, "Türkçe", 3)]
    sonuc = yerel.coz(SolveInput(slots=slots, lessons=dersler, time_limit_seconds=3))
    assert sonuc.ok, sonuc.unplaced
    assert len(sonuc.placements) == 17
    _dogrula(slots, dersler, sonuc)


def test_bloklar_ardisik_ve_bitisik_degil():
    slots = izgara()
    d = ders(1, 1, 10, "Fen", 4, desen="2+2", gunluk=2)
    sonuc = yerel.coz(SolveInput(slots=slots, lessons=[d], time_limit_seconds=2))
    assert sonuc.ok
    konum = {s.period_id: (s.day_index, s.period_index) for s in slots}
    gunler = {}
    for _, pid in sonuc.placements:
        g, p = konum[pid]
        gunler.setdefault(g, []).append(p)
    # Her gün tam 2 saat ve ardışık: bloklar bütün, aynı güne iki blok konmadı.
    assert all(sorted(v) == [v[0], v[0] + 1] if len(v) == 2 else False
               for v in (sorted(x) for x in gunler.values()))
    assert len(gunler) == 2


def test_kapali_saate_koymaz_ve_eksigi_bildirir():
    slots = izgara()
    hepsi = frozenset(s.period_id for s in slots)
    kapali = ders(1, 1, 10, "Matematik", 2, kapali=hepsi)
    sonuc = yerel.coz(SolveInput(slots=slots, lessons=[kapali], time_limit_seconds=1))
    assert not sonuc.ok and sonuc.unplaced == {1: 2}
    assert sonuc.placements == []


def test_kilitli_saat_yerinde_kalir():
    slots = izgara()
    d = ders(1, 1, 10, "Matematik", 3, desen="1+1+1", gunluk=1)
    kilit = slots[7].period_id
    sonuc = yerel.coz(SolveInput(slots=slots, lessons=[d], locked={1: [kilit]},
                                 time_limit_seconds=1))
    assert sonuc.ok
    assert (1, kilit) in sonuc.placements


def test_ipucundan_baslar():
    slots = izgara()
    d = ders(1, 1, 10, "Matematik", 2, desen="1+1", gunluk=1)
    ipucu = ((1, slots[3].period_id), (1, slots[9].period_id))
    sonuc = yerel.coz(SolveInput(slots=slots, lessons=[d], ipucu=ipucu,
                                 time_limit_seconds=0.5, seed=3))
    assert sonuc.ok
    # Çözüm zaten sıfır cezalı: ipucu olduğu gibi korunur.
    assert set(sonuc.placements) == set(ipucu)
