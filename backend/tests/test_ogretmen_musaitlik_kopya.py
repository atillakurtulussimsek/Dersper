"""Öğretmen müsaitliği başka öğretmenlere toplu kopyalanır."""
from fastapi.testclient import TestClient


def _kur(c: TestClient) -> dict:
    ogr = {ad: c.post("/api/teachers", json={"full_name": ad}).json()["id"]
           for ad in ("Ayşe Yılmaz", "Mehmet Demir", "Zeynep Kaya")}
    saatler = sorted(c.get("/api/timegrid").json()[0]["periods"], key=lambda p: p["index"])
    kapali = [saatler[0]["id"], saatler[1]["id"]]
    r = c.put(f"/api/teachers/{ogr['Ayşe Yılmaz']}/availability",
              json={"cells": [{"period_id": p, "state": "uygun_degil"} for p in kapali]})
    assert r.status_code == 200, r.text
    # Hedefte eski, farklı bir işaret dursun: kopya onu silmeli.
    c.put(f"/api/teachers/{ogr['Mehmet Demir']}/availability",
          json={"cells": [{"period_id": saatler[5]["id"], "state": "uygun_degil"}]})
    return {"ogr": ogr, "kapali": kapali}


def _kapali(c: TestClient, tid: int) -> list[int]:
    return sorted(m["period_id"] for m in c.get(f"/api/teachers/{tid}/availability").json()
                  if m["state"] == "uygun_degil")


def test_tablo_hedef_ogretmenlere_aynen_yazilir(yonetici: TestClient):
    k = _kur(yonetici)
    o = k["ogr"]
    r = yonetici.post(f"/api/teachers/{o['Ayşe Yılmaz']}/availability/copy",
                      json={"teacher_ids": [o["Mehmet Demir"], o["Zeynep Kaya"]]})
    assert r.status_code == 200, r.text
    assert r.json() == {"copied_to": ["Mehmet Demir", "Zeynep Kaya"], "cells": 2}
    for ad in ("Mehmet Demir", "Zeynep Kaya"):
        assert _kapali(yonetici, o[ad]) == sorted(k["kapali"]), ad
    # Kaynak değişmedi.
    assert _kapali(yonetici, o["Ayşe Yılmaz"]) == sorted(k["kapali"])


def test_kendisi_hedef_listesinde_yok_sayilir(yonetici: TestClient):
    o = _kur(yonetici)["ogr"]
    r = yonetici.post(f"/api/teachers/{o['Ayşe Yılmaz']}/availability/copy",
                      json={"teacher_ids": [o["Ayşe Yılmaz"]]})
    assert r.status_code == 404


def test_baska_donemin_ogretmeni_hedef_olamaz(yonetici: TestClient):
    o = _kur(yonetici)["ogr"]
    yeni = yonetici.post("/api/terms", json={"name": "Öteki"}).json()["id"]
    yonetici.post(f"/api/terms/{yeni}/activate")
    yabanci = yonetici.post("/api/teachers", json={"full_name": "Yabancı"}).json()["id"]
    r = yonetici.post(f"/api/teachers/{yabanci}/availability/copy",
                      json={"teacher_ids": [o["Mehmet Demir"]]})
    assert r.status_code == 404
