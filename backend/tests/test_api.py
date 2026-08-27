"""Uçtan uca API testleri: kurulumdan yayına kadar tüm akış."""
from fastapi.testclient import TestClient


def _tanimlar(c: TestClient, ek: str = "") -> dict:
    """Küçük bir okul kurar ve kimlikleri döner. `ek`, adları benzersizleştirir."""
    gunler = [g for g in c.get("/api/timegrid").json() if g["is_active"]]
    dersler = [
        c.post("/api/subjects", json={"name": ad}).json()["id"]
        for ad in (f"Matematik{ek}", f"Türkçe{ek}", f"Fen{ek}", f"Sosyal{ek}")
    ]
    ogretmenler = [
        c.post("/api/teachers", json={"full_name": ad}).json()["id"]
        for ad in (f"Ayşe{ek}", f"Mehmet{ek}", f"Zeynep{ek}", f"Ali{ek}")
    ]
    subeler = [
        c.post("/api/sections", json={"name": ad, "grade_level": 5}).json()["id"]
        for ad in (f"5-A{ek}", f"5-B{ek}")
    ]
    for sube in subeler:
        for i, ders in enumerate(dersler):
            c.post("/api/curriculum", json={
                "section_id": sube, "subject_id": ders, "teacher_id": ogretmenler[i],
                "weekly_hours": 5 if i < 2 else 4,
                "block_size": 2 if i == 2 else 1, "max_per_day": 2,
            })
    return {"gunler": gunler, "dersler": dersler, "ogretmenler": ogretmenler,
            "subeler": subeler}


def test_kurulum_ve_oturum(yonetici: TestClient):
    assert yonetici.get("/api/setup/status").json()["completed"] is True
    # kurulumda verilen parolayla yeniden giriş yapılabilir
    r = yonetici.post("/api/auth/login", json={
        "email": "yonetici@ornek.com", "password": "parola1234",
    })
    assert r.status_code == 200
    assert yonetici.get("/api/auth/me").json()["email"] == "yonetici@ornek.com"
    assert yonetici.get("/api/institution").json()["name"] == "Test Ortaokulu"


def test_kurulum_ikinci_kez_reddedilir(yonetici: TestClient):
    r = yonetici.post("/api/setup", json={
        "institution_name": "İkinci Okul", "institution_type": "k12",
        "full_name": "Biri", "email": "baska@ornek.com", "password": "parola1234",
    })
    assert r.status_code == 409


def test_jetonsuz_erisim_engellenir(istemci: TestClient):
    istemci.headers.pop("Authorization", None)
    assert istemci.get("/api/teachers").status_code == 401


def test_varsayilan_zaman_izgarasi(yonetici: TestClient):
    aktif = [g for g in yonetici.get("/api/timegrid").json() if g["is_active"]]
    assert len(aktif) == 5                      # Pazartesi–Cuma
    assert len(aktif[0]["periods"]) == 8


def test_musaitlik_kaydedilir(yonetici: TestClient):
    ogretmen = yonetici.post("/api/teachers", json={"full_name": "Müsaitlik Testi"}).json()
    cuma = [g for g in yonetici.get("/api/timegrid").json() if g["is_active"]][4]
    yonetici.put(f"/api/teachers/{ogretmen['id']}/availability", json={
        "cells": [{"period_id": p["id"], "state": "uygun_degil"} for p in cuma["periods"]]
    })
    kayitli = yonetici.get(f"/api/teachers/{ogretmen['id']}/availability").json()
    assert len(kayitli) == len(cuma["periods"])
    assert all(h["state"] == "uygun_degil" for h in kayitli)


def test_ayni_derste_iki_mufredat_satiri_olamaz(yonetici: TestClient):
    d = yonetici.post("/api/subjects", json={"name": "Tekrar Dersi"}).json()["id"]
    o = yonetici.post("/api/teachers", json={"full_name": "Tekrar Öğretmeni"}).json()["id"]
    s = yonetici.post("/api/sections", json={"name": "9-Z"}).json()["id"]
    govde = {"section_id": s, "subject_id": d, "teacher_id": o, "weekly_hours": 2}
    assert yonetici.post("/api/curriculum", json=govde).status_code == 201
    assert yonetici.post("/api/curriculum", json=govde).status_code == 409


def test_program_uretilir_ve_yayinlanir(yonetici: TestClient):
    _tanimlar(yonetici)
    pid = yonetici.post("/api/timetables", json={"name": "2026 Güz"}).json()["id"]

    deneme = yonetici.post(f"/api/timetables/{pid}/solve?time_limit_seconds=30").json()
    assert deneme["status"] == "basarili", deneme["report"]

    izgara = yonetici.get(f"/api/timetables/{pid}/grid").json()
    assert len(izgara["cells"]) == 36           # 2 şube × 18 saat

    # Dolu bir saate taşımak reddedilir.
    h = izgara["cells"][0]
    diger = next(x for x in izgara["cells"]
                 if x["section_id"] == h["section_id"] and x["period_id"] != h["period_id"])
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{h['assignment_id']}",
                       json={"period_id": diger["period_id"]})
    assert r.status_code == 409

    yayin = yonetici.post(f"/api/timetables/{pid}/publish").json()
    assert yayin["public_token"]

    # Yayınlanan program girişsiz okunabilir.
    yonetici.headers.pop("Authorization")
    acik = yonetici.get(f"/api/public/timetables/{yayin['public_token']}").json()
    assert len(acik["cells"]) == 36


def test_cikti_bicimleri(yonetici: TestClient):
    _tanimlar(yonetici)
    pid = yonetici.post("/api/timetables", json={"name": "Çıktı"}).json()["id"]
    yonetici.post(f"/api/timetables/{pid}/solve?time_limit_seconds=30")
    assert yonetici.get(f"/api/timetables/{pid}/export/xlsx?bakis=sube").status_code == 200
    assert yonetici.get(f"/api/timetables/{pid}/export/html?bakis=ogretmen").status_code == 200


def test_cozumsuz_program_tani_raporu_uretir(yonetici: TestClient):
    """Tek öğretmen iki şubede haftalık 50 saat: ızgarada 40 saat var, sığmaz."""
    d = yonetici.post("/api/subjects", json={"name": "Aşırı Yük"}).json()["id"]
    o = yonetici.post("/api/teachers", json={"full_name": "Yorgun Öğretmen"}).json()["id"]
    for ad in ("12-Y", "12-Z"):
        s = yonetici.post("/api/sections", json={"name": ad}).json()["id"]
        r = yonetici.post("/api/curriculum", json={
            "section_id": s, "subject_id": d, "teacher_id": o,
            "weekly_hours": 25, "block_size": 1, "max_per_day": 8,
        })
        assert r.status_code == 201, r.text
    pid = yonetici.post("/api/timetables", json={"name": "Çözümsüz"}).json()["id"]
    deneme = yonetici.post(f"/api/timetables/{pid}/solve?time_limit_seconds=20").json()

    assert deneme["status"] == "cozumsuz"
    kodlar = {b["kod"] for b in deneme["report"]["bulgular"]}
    assert "ogretmen_kapasite" in kodlar
    assert deneme["report"]["ozet"]["yerlesmeyen_toplam"] > 0
    # Yapay zeka kapalıyken açıklama üretilmez ama üretim yine de tamamlanır.
    assert deneme["ai_explanation"] is None


def test_yapay_zeka_anahtari_geri_okunmaz(yonetici: TestClient):
    assert yonetici.get("/api/ai/settings").json()["has_api_key"] is False
    yonetici.put("/api/ai/settings", json={
        "enabled": True, "base_url": "http://yok.local/v1",
        "model": "test", "api_key": "sk-gizli-anahtar-1234",
    })
    ayar = yonetici.get("/api/ai/settings").json()
    assert ayar["has_api_key"] is True
    assert ayar["api_key_masked"] == "sk-gi…1234"
    assert "api_key" not in ayar          # ham anahtar hiçbir zaman dönmez
