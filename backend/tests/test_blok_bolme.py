"""Zorunlu kalınca blok bölme: 2+2 kurulamıyorsa 2+1+1, 1+1+1+1."""
from fastapi.testclient import TestClient

from app.solver import yerel
from app.solver.engine import SolveInput, solve
from tests.conftest import uret_ve_bekle
from tests.test_engine import _dizi_uzunluklari, ders, izgara


def _bolunebilir(d):
    from dataclasses import replace

    return replace(d, bolunebilir=True)


def _kapali(slots, acik: dict[int, set[int]]) -> set[int]:
    """Yalnız `acik` (gün -> ders saatleri) açık; gerisi kapalı."""
    return {s.period_id for s in slots if s.period_index not in acik.get(s.day_index, set())}


def test_bolunebilir_blok_zorunlu_kalinca_bolunur():
    slots = izgara(gun_sayisi=2, ders_sayisi=4)
    # Pazartesi 0-1 bitişik açık; Salı yalnız 0 ve 2: ikinci blok sığmaz.
    kapali = _kapali(slots, {0: {0, 1}, 1: {0, 2}})
    d = _bolunebilir(ders(1, 1, 10, "Matematik", 4, desen="2+2", kapali=kapali))
    sonuc = solve(SolveInput(slots=slots, lessons=[d], esnek_gunluk=True,
                             time_limit_seconds=10))
    assert sonuc.ok, sonuc.status_name
    assert sorted(_dizi_uzunluklari(slots, sonuc.placements)) == [1, 1, 2]


def test_bolme_yalniz_izinli_derste_olur():
    slots = izgara(gun_sayisi=2, ders_sayisi=4)
    kapali = _kapali(slots, {0: {0, 1}, 1: {0, 2}})
    d = ders(1, 1, 10, "Matematik", 4, desen="2+2", kapali=kapali)
    sonuc = solve(SolveInput(slots=slots, lessons=[d], esnek_gunluk=True,
                             time_limit_seconds=10))
    assert not sonuc.ok
    assert sonuc.unplaced == {1: 2}


def test_bolme_esnetmeden_once_denenmez():
    """Esnek kip kapalıyken (ilk denemeler) bölme yapılmaz."""
    slots = izgara(gun_sayisi=2, ders_sayisi=4)
    kapali = _kapali(slots, {0: {0, 1}, 1: {0, 2}})
    d = _bolunebilir(ders(1, 1, 10, "Matematik", 4, desen="2+2", kapali=kapali))
    sonuc = solve(SolveInput(slots=slots, lessons=[d], time_limit_seconds=10))
    assert not sonuc.ok


def test_gerekmedikce_bolunmez():
    slots = izgara(gun_sayisi=2, ders_sayisi=4)
    d = _bolunebilir(ders(1, 1, 10, "Matematik", 4, desen="2+2"))
    # Sert model zaten kurar; bölme kipine hiç girilmez.
    sonuc = solve(SolveInput(slots=slots, lessons=[d], esnek_gunluk=True,
                             time_limit_seconds=10))
    assert sonuc.ok
    assert sorted(_dizi_uzunluklari(slots, sonuc.placements)) == [2, 2]


def test_uclu_blok_2_1_olarak_bolunur():
    slots = izgara(gun_sayisi=2, ders_sayisi=4)
    # Hiçbir günde 3 bitişik saat yok; Pazartesi 0-1 ve Salı 0 açık.
    kapali = _kapali(slots, {0: {0, 1}, 1: {0}})
    d = _bolunebilir(ders(1, 1, 10, "Fen", 3, desen="3", gunluk=3, kapali=kapali))
    sonuc = solve(SolveInput(slots=slots, lessons=[d], esnek_gunluk=True,
                             time_limit_seconds=10))
    assert sonuc.ok, sonuc.status_name
    assert sorted(_dizi_uzunluklari(slots, sonuc.placements)) == [1, 2]


def test_yerel_arama_da_boler():
    slots = izgara(gun_sayisi=2, ders_sayisi=4)
    kapali = _kapali(slots, {0: {0, 1}, 1: {0, 2}})
    d = _bolunebilir(ders(1, 1, 10, "Matematik", 4, desen="2+2", kapali=kapali))
    sonuc = yerel.coz(SolveInput(slots=slots, lessons=[d], esnek_gunluk=True,
                                 time_limit_seconds=2))
    assert sonuc.ok, sonuc.unplaced
    assert sorted(_dizi_uzunluklari(slots, sonuc.placements)) == [1, 1, 2]


def test_bolunen_ders_uyari_olarak_bildirilir(yonetici: TestClient):
    c = yonetici
    izgara_ = c.get("/api/timegrid").json()
    for g in izgara_:
        g["is_active"] = g["index"] in (0, 1)
    c.put("/api/timegrid", json=izgara_)
    aktif = [g for g in c.get("/api/timegrid").json() if g["is_active"]]

    d = c.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    o = c.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    s = c.post("/api/sections", json={"name": "5-A"}).json()["id"]
    # Pazartesi 1-2. saat bitişik açık; Salı yalnız 1. ve 3. saat.
    acik = {aktif[0]["periods"][0]["id"], aktif[0]["periods"][1]["id"],
            aktif[1]["periods"][0]["id"], aktif[1]["periods"][2]["id"]}
    c.put(f"/api/teachers/{o}/availability", json={"cells": [
        {"period_id": p["id"], "state": "uygun_degil"}
        for g in aktif for p in g["periods"] if p["id"] not in acik
    ]})
    r = c.post("/api/curriculum", json={
        "section_id": s, "subject_id": d, "teacher_id": o,
        "weekly_hours": 4, "block_pattern": "2+2", "max_per_day": 2,
        "allow_split": True,
    })
    assert r.json()["allow_split"] is True
    pid = c.post("/api/timetables", json={"name": "Bölme"}).json()["id"]

    kayit = uret_ve_bekle(c, pid, saniye=180)
    assert kayit["status"] == "basarili"
    uyarilar = c.get(f"/api/timetables/{pid}/warnings").json()
    bolunme = [u for u in uyarilar if u["tur"] == "bolunme"]
    assert len(bolunme) == 1
    assert "2+2 yerine 2+1+1" in bolunme[0]["baslik"]
