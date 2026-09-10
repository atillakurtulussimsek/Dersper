"""Şube birleştirme kuralı: çözücü hangi dersin kaç saatinin ortak okutulacağını seçer."""
from app.solver.engine import Lesson, SolveInput, solve
from tests.test_engine import izgara


def _ders(eid, sube, ad_s, ogr, ders, saat, desen, gunluk=2, **ek):
    from app.bloklar import coz
    return Lesson(
        entry_id=eid, section_id=sube, section_name=ad_s, teacher_id=ogr,
        teacher_name=f"Öğretmen {ogr}", subject_name=ders, weekly_hours=saat,
        blocks=tuple(coz(desen, saat)), max_per_day=gunluk, subject_id=hash(ders) % 1000,
        **ek,
    )


def _ortak(eid, a: Lesson, b: Lesson, kural_id, saat, gunler):
    """Loader'ın kuraldan türettiği sanal ortak ders."""
    en_az = min(a.weekly_hours, b.weekly_hours)
    return Lesson(
        entry_id=eid, section_id=a.section_id, section_name=a.section_name,
        sections=((a.section_id, a.section_name), (b.section_id, b.section_name)),
        teacher_id=a.teacher_id, teacher_name=a.teacher_name,
        subject_name=a.subject_name, subject_id=a.subject_id,
        weekly_hours=en_az, blocks=(1,) * en_az,
        max_per_day=min(a.max_per_day, b.max_per_day),
        blocked_period_ids=a.blocked_period_ids,
        section_blocked_period_ids=a.section_blocked_period_ids | b.section_blocked_period_ids,
        ortak_kural_id=kural_id, ortak_ebeveynler=(a.entry_id, b.entry_id),
        kural_saat=saat, kural_adi=f"{a.section_name} + {b.section_name}",
        izinli_gunler=frozenset(gunler),
    )


def _coz(lessons, gun=4, saat=4):
    return solve(SolveInput(slots=izgara(gun, saat), lessons=lessons, time_limit_seconds=10))


def test_kural_tam_saat_kadar_ortak_ders_koyar():
    a = _ders(1, 1, "9-A", 10, "Matematik", 3, "2+1")
    b = _ders(2, 2, "9-B", 10, "Matematik", 3, "2+1")
    o = _ortak(-1, a, b, 7, 2, {3})                    # Perşembe'de tam 2 saat
    sonuc = _coz([a, b, o])
    assert sonuc.ok, sonuc.status_name
    slots = izgara(4, 4)
    gun = {s.period_id: s.day_index for s in slots}
    ortak = [p for e, p in sonuc.placements if e == -1]
    assert len(ortak) == 2 and all(gun[p] == 3 for p in ortak)
    # Ebeveynlerin kalan saati: 3 - 2 = 1 (desen "2+1"in 1'lik bloğu)
    assert sum(1 for e, _ in sonuc.placements if e == 1) == 1
    assert sum(1 for e, _ in sonuc.placements if e == 2) == 1
    # Ortak saatte ebeveynlerin kendi dersi yok
    kendi = {p for e, p in sonuc.placements if e in (1, 2)}
    assert not (kendi & set(ortak))


def test_ortak_saat_desenle_uyumlu_olmali():
    """Her iki ders de tek 2'lik blok: 1 saat ortak okutmak deseni bozar."""
    a = _ders(1, 1, "9-A", 10, "Matematik", 2, "2")
    b = _ders(2, 2, "9-B", 10, "Matematik", 2, "2")
    o = _ortak(-1, a, b, 7, 1, {3})
    sonuc = _coz([a, b, o])
    assert not sonuc.ok and sonuc.proven_infeasible


def test_kural_izinli_gun_disina_cikmaz():
    a = _ders(1, 1, "9-A", 10, "Matematik", 2, "1+1")
    b = _ders(2, 2, "9-B", 10, "Matematik", 2, "1+1")
    o = _ortak(-1, a, b, 7, 2, {0})
    # Pazartesi şube 9-B için kapalı: ortak saat oraya konamaz → kural çözümsüz.
    slots = izgara(4, 4)
    pazartesi = frozenset(s.period_id for s in slots if s.day_index == 0)
    b_kapali = Lesson(**{**b.__dict__, "section_blocked_period_ids": pazartesi,
                         "section_blocked_map": ((2, pazartesi),)})
    o = Lesson(**{**o.__dict__, "section_blocked_period_ids": pazartesi})
    sonuc = _coz([a, b_kapali, o])
    assert not sonuc.ok and sonuc.proven_infeasible


def test_cozucu_en_uygun_dersi_secer():
    """İki eşleşen ders var; kural 2 saat. Fizik öğretmeni Perşembe kapalı:
    ortak saat Matematik'ten seçilmeli."""
    slots = izgara(4, 4)
    persembe = frozenset(s.period_id for s in slots if s.day_index == 3)
    a1 = _ders(1, 1, "9-A", 10, "Matematik", 2, "1+1")
    b1 = _ders(2, 2, "9-B", 10, "Matematik", 2, "1+1")
    a2 = _ders(3, 1, "9-A", 11, "Fizik", 2, "1+1", blocked_period_ids=persembe)
    b2 = _ders(4, 2, "9-B", 11, "Fizik", 2, "1+1", blocked_period_ids=persembe)
    o1 = _ortak(-1, a1, b1, 7, 2, {3})
    o2 = _ortak(-2, a2, b2, 7, 2, {3})
    sonuc = _coz([a1, b1, a2, b2, o1, o2])
    assert sonuc.ok, sonuc.status_name
    assert sum(1 for e, _ in sonuc.placements if e == -1) == 2
    assert sum(1 for e, _ in sonuc.placements if e == -2) == 0


def test_gunluk_sinir_ortak_saatleri_de_sayar():
    """Ebeveynin günlük sınırı 1: ortak 2 saat aynı güne konamaz (izinli gün tek) → çözümsüz."""
    a = _ders(1, 1, "9-A", 10, "Matematik", 2, "1+1", gunluk=1)
    b = _ders(2, 2, "9-B", 10, "Matematik", 2, "1+1", gunluk=1)
    o = _ortak(-1, a, b, 7, 2, {3})
    sonuc = _coz([a, b, o])
    assert not sonuc.ok


# --- Uçtan uca: kural → üretim → ızgara ---

from fastapi.testclient import TestClient
from tests.conftest import uret_ve_bekle


def _okul(c: TestClient) -> dict:
    ogr = c.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    mat = c.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    a = c.post("/api/sections", json={"name": "9-A"}).json()["id"]
    b = c.post("/api/sections", json={"name": "9-B"}).json()["id"]
    for s in (a, b):
        r = c.post("/api/curriculum", json={
            "section_id": s, "subject_id": mat, "teacher_id": ogr,
            "weekly_hours": 3, "block_pattern": "2+1", "max_per_day": 2,
        })
        assert r.status_code == 201, r.text
    return {"ogr": ogr, "mat": mat, "a": a, "b": b}


def test_kural_eslesen_dersleri_ve_ust_siniri_soyler(yonetici: TestClient):
    o = _okul(yonetici)
    r = yonetici.get(f"/api/merge-rules/preview?section_a_id={o['a']}&section_b_id={o['b']}")
    assert r.status_code == 200, r.text
    assert r.json()["max_hours"] == 3
    assert r.json()["pairs"][0]["subject_name"] == "Matematik"

    r = yonetici.post("/api/merge-rules", json={
        "section_a_id": o["a"], "section_b_id": o["b"], "hours": 4, "day_indexes": [4],
    })
    assert r.status_code == 422 and "en çok 3 saat" in r.text

    r = yonetici.post("/api/merge-rules", json={
        "section_a_id": o["a"], "section_b_id": o["b"], "hours": 2, "day_indexes": [4],
    })
    assert r.status_code == 201, r.text
    assert r.json()["section_a_name"] == "9-A" and r.json()["day_names"] == ["Cuma"]

    # Aynı çift ters sırayla ikinci kez girilemez.
    r = yonetici.post("/api/merge-rules", json={
        "section_a_id": o["b"], "section_b_id": o["a"], "hours": 1, "day_indexes": [4],
    })
    assert r.status_code == 409


def test_ortak_dersi_olmayan_cift_reddedilir(yonetici: TestClient):
    o = _okul(yonetici)
    c = yonetici.post("/api/sections", json={"name": "9-C"}).json()["id"]
    r = yonetici.post("/api/merge-rules", json={
        "section_a_id": o["a"], "section_b_id": c, "hours": 1, "day_indexes": [0],
    })
    assert r.status_code == 422 and "ortak bir ders yok" in r.text


def test_uretim_kurala_gore_ortak_saat_koyar(yonetici: TestClient):
    o = _okul(yonetici)
    yonetici.post("/api/merge-rules", json={
        "section_a_id": o["a"], "section_b_id": o["b"], "hours": 2, "day_indexes": [4],
    })
    pid = yonetici.post("/api/timetables", json={"name": "Ortak"}).json()["id"]
    deneme = uret_ve_bekle(yonetici, pid)
    assert deneme["status"] == "basarili", deneme["report"]
    assert deneme["required"] == 6 and deneme["best_placed"] == 6

    hucreler = yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]
    ortak = [h for h in hucreler if h["merged_entry_id"] is not None]
    assert len(ortak) == 2
    assert all(h["day_index"] == 4 for h in ortak)
    assert all(sorted(h["section_names"]) == ["9-A", "9-B"] for h in ortak)
    # Her şubenin kendi kalan saati: 3 - 2 = 1
    kendi = [h for h in hucreler if h["merged_entry_id"] is None]
    assert len(kendi) == 2 and {h["section_name"] for h in kendi} == {"9-A", "9-B"}
    # Bekleyen yok, uyarı yok.
    assert yonetici.get(f"/api/timetables/{pid}/pending").json() == []
    assert yonetici.get(f"/api/timetables/{pid}/warnings").json() == []

    # Sürüm geri yüklenince ortak saatler korunur.
    surum = yonetici.get(f"/api/timetables/{pid}/grid").json()["version"]
    r = yonetici.post(f"/api/timetables/{pid}/versions/{surum}/restore")
    assert r.status_code == 200
    assert sum(1 for h in r.json()["cells"] if h["merged_entry_id"] is not None) == 2

    # Ortak saat iki şubeyi de tutar: 9-B'nin kendi dersi oraya konamaz.
    ortak_saat = ortak[0]["period_id"]
    b_kendi = next(h for h in kendi if h["section_name"] == "9-B")
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{b_kendi['assignment_id']}",
                       json={"period_id": ortak_saat})
    assert r.status_code == 409, r.text


def test_kural_izinli_gunlere_sigmazsa_engel_yazilir(yonetici: TestClient):
    o = _okul(yonetici)
    # Cuma günü 9-B tamamen kapalı: ortak saat oraya konamaz.
    gunler = [g for g in yonetici.get("/api/timegrid").json() if g["is_active"]]
    cuma = gunler[4]
    yonetici.put(f"/api/sections/{o['b']}/availability", json={
        "cells": [{"period_id": p["id"], "state": "uygun_degil"} for p in cuma["periods"]]
    })
    yonetici.post("/api/merge-rules", json={
        "section_a_id": o["a"], "section_b_id": o["b"], "hours": 2, "day_indexes": [4],
    })
    pid = yonetici.post("/api/timetables", json={"name": "Sığmaz"}).json()["id"]
    from tests.conftest import cozumsuz_calistir
    deneme = cozumsuz_calistir(yonetici, pid)
    kodlar = [b["kod"] for b in deneme["report"]["bulgular"]]
    assert "birlestirme_sigmiyor" in kodlar, kodlar
