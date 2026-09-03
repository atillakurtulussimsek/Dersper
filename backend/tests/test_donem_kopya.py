"""Dönem kopyası: tanımların tamamı yeni döneme, kimlikler yeniden eşlenerek."""
from fastapi.testclient import TestClient


def _dolu_donem(c: TestClient) -> dict:
    """Bina, öğretmen (kapalı saatli), ders, iki şube (biri binalı, kapalı
    saatli, elle sıralı) ve biri birleşik iki ders ataması."""
    bina = c.post("/api/buildings", json={"name": "Ek Bina", "short_code": "EK"}).json()["id"]
    ogr = c.post("/api/teachers", json={"full_name": "Ayşe Yılmaz", "max_half_days": 9,
                                        "color": "#123456"}).json()["id"]
    ders = c.post("/api/subjects", json={"name": "Matematik", "short_code": "MAT"}).json()["id"]
    a = c.post("/api/sections", json={"name": "9-A", "building_id": bina, "grade_level": 9}).json()["id"]
    b = c.post("/api/sections", json={"name": "9-B"}).json()["id"]
    saatler = sorted(c.get("/api/timegrid").json()[0]["periods"], key=lambda p: p["index"])
    ilk = saatler[0]["id"]
    for yol in (f"/api/teachers/{ogr}/availability", f"/api/sections/{a}/availability"):
        r = c.put(yol, json={"cells": [{"period_id": ilk, "state": "uygun_degil"}]})
        assert r.status_code == 200, r.text
    c.put("/api/sections/order", json={"ids": [b, a]})
    c.post("/api/curriculum", json={"section_id": a, "subject_id": ders, "teacher_id": ogr,
                                    "weekly_hours": 4, "block_pattern": "2+2"})
    c.post("/api/curriculum", json={"section_id": a, "extra_section_ids": [b],
                                    "subject_id": ders, "teacher_id": ogr, "weekly_hours": 2})
    donem = next(d for d in c.get("/api/terms").json() if d["is_active"])
    # PUT tüm alanları yazar; elle sıra ayarı da açıkça gönderilmeli.
    r = c.put(f"/api/terms/{donem['id']}", json={"name": donem["name"], "conflict_basis": "saat",
                                                   "block_building_switch": True,
                                                   "section_order": "elle"})
    assert r.status_code == 200, r.text
    return {"donem": donem["id"], "ilk_saat": ilk}


def test_donem_tamamen_kopyalanir_ve_aktif_olur(yonetici: TestClient):
    k = _dolu_donem(yonetici)
    r = yonetici.post(f"/api/terms/{k['donem']}/copy", json={"name": "2027-2028 Güz"})
    assert r.status_code == 201, r.text
    veri = r.json()
    assert veri["term"]["is_active"] is True
    # Varsayılan ızgara 7 gün (hafta sonu kapalı), açık günlerde 8'er saat.
    assert veri["copied"] == {"gun": 7, "ders_saati": 40, "bina": 1, "ogretmen": 1,
                              "ders": 1, "sube": 2, "mufredat": 2}

    # Ayarlar geldi.
    yeni = veri["term"]
    assert yeni["conflict_basis"] == "saat" and yeni["block_building_switch"] is True
    assert yeni["section_order"] == "elle"

    # Elle sıra korundu, bina yeni döneme eşlendi.
    subeler = yonetici.get("/api/sections").json()
    assert [s["name"] for s in subeler] == ["9-B", "9-A"]
    bina = yonetici.get("/api/buildings").json()[0]
    assert next(s for s in subeler if s["name"] == "9-A")["building_id"] == bina["id"]

    # Birleşik ders yeni şube kimlikleriyle.
    atamalar = yonetici.get("/api/curriculum").json()
    assert sorted(len(e["sections"]) for e in atamalar) == [1, 2]
    assert all(e["teacher"]["full_name"] == "Ayşe Yılmaz" for e in atamalar)

    # Müsaitlik yeni ders saatlerine eşlendi: ilk saat kapalı.
    yeni_ilk = sorted(yonetici.get("/api/timegrid").json()[0]["periods"], key=lambda p: p["index"])[0]["id"]
    assert yeni_ilk != k["ilk_saat"]
    ogr = yonetici.get("/api/teachers").json()[0]
    kapali = [m for m in yonetici.get(f"/api/teachers/{ogr['id']}/availability").json()
              if m["state"] == "uygun_degil"]
    assert [m["period_id"] for m in kapali] == [yeni_ilk]
    sube = next(s for s in subeler if s["name"] == "9-A")
    sube_kapali = [m for m in yonetici.get(f"/api/sections/{sube['id']}/availability").json()
                   if m["state"] == "uygun_degil"]
    assert [m["period_id"] for m in sube_kapali] == [yeni_ilk]


def test_kaynak_donem_dokunulmaz(yonetici: TestClient):
    k = _dolu_donem(yonetici)
    once = yonetici.get("/api/curriculum").json()
    yonetici.post(f"/api/terms/{k['donem']}/copy", json={"name": "Kopya", "activate": False})
    # Kaynak hâlâ aktif ve aynı.
    assert next(d for d in yonetici.get("/api/terms").json() if d["is_active"])["id"] == k["donem"]
    assert yonetici.get("/api/curriculum").json() == once


def test_programlar_kopyalanmaz(yonetici: TestClient):
    k = _dolu_donem(yonetici)
    yonetici.post("/api/timetables", json={"name": "Eski program"})
    r = yonetici.post(f"/api/terms/{k['donem']}/copy", json={"name": "Kopya"})
    assert r.json()["term"]["counts"]["program"] == 0
    assert yonetici.get("/api/timetables").json() == []


def test_silinmis_kayitlar_kopyalanmaz(yonetici: TestClient):
    k = _dolu_donem(yonetici)
    fazla = yonetici.post("/api/subjects", json={"name": "Resim"}).json()["id"]
    assert yonetici.delete(f"/api/subjects/{fazla}").status_code == 204
    r = yonetici.post(f"/api/terms/{k['donem']}/copy", json={"name": "Kopya"})
    assert r.json()["copied"]["ders"] == 1
    assert [d["name"] for d in yonetici.get("/api/subjects").json()] == ["Matematik"]


def test_baska_kurumun_donemi_kopyalanamaz(yonetici: TestClient, ikinci_kurum: TestClient):
    k = _dolu_donem(yonetici)
    assert ikinci_kurum.post(f"/api/terms/{k['donem']}/copy", json={"name": "X"}).status_code == 404
