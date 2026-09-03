"""Şube sırası: ada göre doğal sıra ya da elle sıra; her yerde tek gelenek."""
from fastapi.testclient import TestClient

from app.siralama import dogal_anahtar


def test_dogal_sira_sayilari_sayi_olarak_karsilastirir():
    adlar = ["10-A", "9-B", "9-A", "12-C", "Anasınıfı", "9-a"]
    assert sorted(adlar, key=dogal_anahtar) == ["9-A", "9-a", "9-B", "10-A", "12-C", "Anasınıfı"]


def _kur(c: TestClient, *adlar: str) -> dict[str, int]:
    return {ad: c.post("/api/sections", json={"name": ad}).json()["id"] for ad in adlar}


def test_varsayilan_liste_dogal_siradadir(yonetici: TestClient):
    _kur(yonetici, "10-A", "9-B", "9-A")
    assert [s["name"] for s in yonetici.get("/api/sections").json()] == ["9-A", "9-B", "10-A"]


def test_elle_sira_kaydedilir_ve_donemi_elle_alir(yonetici: TestClient):
    k = _kur(yonetici, "9-A", "9-B", "10-A")
    r = yonetici.put("/api/sections/order", json={"ids": [k["10-A"], k["9-A"], k["9-B"]]})
    assert r.status_code == 200, r.text
    assert [s["name"] for s in r.json()] == ["10-A", "9-A", "9-B"]
    assert [s["name"] for s in yonetici.get("/api/sections").json()] == ["10-A", "9-A", "9-B"]
    donem = next(d for d in yonetici.get("/api/terms").json() if d["is_active"])
    assert donem["section_order"] == "elle"


def test_sirasi_verilmeyen_sube_sona_duser(yonetici: TestClient):
    k = _kur(yonetici, "9-A", "9-B")
    yonetici.put("/api/sections/order", json={"ids": [k["9-B"], k["9-A"]]})
    yonetici.post("/api/sections", json={"name": "8-A"})
    assert [s["name"] for s in yonetici.get("/api/sections").json()] == ["9-B", "9-A", "8-A"]


def test_ada_gore_donunce_elle_sira_yok_sayilir(yonetici: TestClient):
    k = _kur(yonetici, "9-A", "9-B")
    yonetici.put("/api/sections/order", json={"ids": [k["9-B"], k["9-A"]]})
    donem = next(d for d in yonetici.get("/api/terms").json() if d["is_active"])
    r = yonetici.put(f"/api/terms/{donem['id']}", json={"name": donem["name"], "section_order": "ad"})
    assert r.status_code == 200, r.text
    assert [s["name"] for s in yonetici.get("/api/sections").json()] == ["9-A", "9-B"]


def test_baska_donemin_subesi_siralanamaz(yonetici: TestClient):
    k = _kur(yonetici, "9-A")
    yeni = yonetici.post("/api/terms", json={"name": "Öteki"}).json()["id"]
    yonetici.post(f"/api/terms/{yeni}/activate")
    assert yonetici.put("/api/sections/order", json={"ids": [k["9-A"]]}).status_code == 404


def test_izgara_yaniti_sirali_sube_adlarini_tasir(yonetici: TestClient):
    k = _kur(yonetici, "9-A", "9-B")
    yonetici.put("/api/sections/order", json={"ids": [k["9-B"], k["9-A"]]})
    pid = yonetici.post("/api/timetables", json={"name": "Deneme"}).json()["id"]
    assert yonetici.get(f"/api/timetables/{pid}/grid").json()["section_names"] == ["9-B", "9-A"]
