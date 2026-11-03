"""Programa özel zaman ızgarası: genelden bağımsız günler, saatler ve müsaitlik."""
from fastapi.testclient import TestClient

from tests.conftest import uret_ve_bekle
from tests.test_duzenle import _okul


def _olustur(c: TestClient, mod: str) -> dict:
    r = c.post("/api/timetables", json={"name": f"Özel {mod}", "grid_mode": mod})
    assert r.status_code == 201, r.text
    return r.json()


def test_kopya_genelden_bagimsizdir(yonetici: TestClient):
    okul = _okul(yonetici, gun_sayisi=2)
    ayse = okul["ogretmenler"]["ayse"]
    ilk = okul["saatler"][0]["id"]
    yonetici.put(f"/api/teachers/{ayse}/availability",
                 json={"cells": [{"period_id": ilk, "state": "uygun_degil"}]})

    p = _olustur(yonetici, "kopya")
    assert p["own_grid"] is True
    ozel = yonetici.get(f"/api/timetables/{p['id']}/timegrid").json()
    genel = yonetici.get("/api/timegrid").json()
    assert [g["name"] for g in ozel] == [g["name"] for g in genel]
    ozel_saatler = {x["id"] for g in ozel for x in g["periods"]}
    assert not ozel_saatler & {x["id"] for g in genel for x in g["periods"]}

    # Müsaitlik kopyalandı, ama programa özel.
    ozel_ilk = sorted(ozel[0]["periods"], key=lambda x: x["index"])[0]["id"]
    m = yonetici.get(f"/api/teachers/{ayse}/availability",
                     params={"timetable_id": p["id"]}).json()
    assert m == [{"period_id": ozel_ilk, "state": "uygun_degil"}]

    # Programda açılan saat genelde kapalı kalır.
    yonetici.put(f"/api/teachers/{ayse}/availability",
                 params={"timetable_id": p["id"]}, json={"cells": []})
    assert yonetici.get(f"/api/teachers/{ayse}/availability").json() == [
        {"period_id": ilk, "state": "uygun_degil"}
    ]

    # Genel ızgarada gün kapatmak programın ızgarasına dokunmaz.
    genel[0]["is_active"] = False
    assert yonetici.put("/api/timegrid", json=genel).status_code == 200
    assert yonetici.get(f"/api/timetables/{p['id']}/timegrid").json()[0]["is_active"]


def test_bos_izgara_kendi_saatleriyle_uretir(yonetici: TestClient):
    _okul(yonetici, gun_sayisi=2)
    p = _olustur(yonetici, "bos")
    gunler = yonetici.get(f"/api/timetables/{p['id']}/timegrid").json()
    assert gunler and all(not g["periods"] for g in gunler)

    # Yalnızca Cumartesi, 4 saat.
    yeni = [{**g, "is_active": g["index"] == 5,
             "periods": [{"index": i, "name": f"{i + 1}. ders"} for i in range(4)]
             if g["index"] == 5 else []}
            for g in gunler]
    r = yonetici.put(f"/api/timetables/{p['id']}/timegrid", json=yeni)
    assert r.status_code == 200, r.text
    cumartesi = {x["id"] for g in r.json() if g["index"] == 5 for x in g["periods"]}

    # Her şey programın kendi Cumartesisine yerleşir.
    uret_ve_bekle(yonetici, p["id"])
    hucreler = yonetici.get(f"/api/timetables/{p['id']}/grid").json()["cells"]
    assert hucreler and {h["period_id"] for h in hucreler} <= cumartesi


def test_genel_programin_izgarasi_degistirilemez(yonetici: TestClient):
    _okul(yonetici)
    p = _olustur(yonetici, "genel")
    assert p["own_grid"] is False
    izgara = yonetici.get(f"/api/timetables/{p['id']}/timegrid").json()
    assert izgara == yonetici.get("/api/timegrid").json()
    assert yonetici.put(f"/api/timetables/{p['id']}/timegrid",
                        json=izgara).status_code == 404
    # Genel ızgaralı programın müsaitliği genel müsaitliktir.
    assert yonetici.get("/api/availability/closed", params={"timetable_id": p["id"]}
                        ).json() == yonetici.get("/api/availability/closed").json()
