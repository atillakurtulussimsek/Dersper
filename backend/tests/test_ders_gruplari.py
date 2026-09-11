"""Ders grupları: benzer dersler bir şubede arka arkaya gelmesin."""
from fastapi.testclient import TestClient


def _dersler(c: TestClient) -> dict[str, int]:
    return {ad: c.post("/api/subjects", json={"name": ad}).json()["id"]
            for ad in ("Temel Matematik", "İleri Matematik", "Geometri", "Fizik")}


def test_grup_olusturulur_ve_ders_tek_grupta_olur(yonetici: TestClient):
    d = _dersler(yonetici)
    r = yonetici.post("/api/subject-groups", json={
        "name": "Matematik", "subject_ids": [d["Temel Matematik"], d["İleri Matematik"], d["Geometri"]],
    })
    assert r.status_code == 201, r.text
    assert r.json()["subject_names"] == ["Geometri", "Temel Matematik", "İleri Matematik"]

    r = yonetici.post("/api/subject-groups", json={
        "name": "Sayısal", "subject_ids": [d["Fizik"], d["Geometri"]],
    })
    assert r.status_code == 409 and "Matematik" in r.text

    assert yonetici.post("/api/subject-groups", json={
        "name": "Tek", "subject_ids": [d["Fizik"]],
    }).status_code == 422

    grup = yonetici.get("/api/subject-groups").json()[0]
    assert yonetici.delete(f"/api/subject-groups/{grup['id']}").status_code == 204
    assert yonetici.get("/api/subject-groups").json() == []


def test_grup_uyarisi_elle_bitisik_yerlesimde(yonetici: TestClient):
    from tests.conftest import uret_ve_bekle

    d = _dersler(yonetici)
    o1 = yonetici.post("/api/teachers", json={"full_name": "Ayşe"}).json()["id"]
    o2 = yonetici.post("/api/teachers", json={"full_name": "Mehmet"}).json()["id"]
    s = yonetici.post("/api/sections", json={"name": "9-A"}).json()["id"]
    yonetici.post("/api/subject-groups", json={
        "name": "Matematik", "subject_ids": [d["Temel Matematik"], d["İleri Matematik"]],
    })
    for ders, ogr in ((d["Temel Matematik"], o1), (d["İleri Matematik"], o2)):
        yonetici.post("/api/curriculum", json={
            "section_id": s, "subject_id": ders, "teacher_id": ogr,
            "weekly_hours": 2, "block_pattern": "1+1", "max_per_day": 1,
        })
    pid = yonetici.post("/api/timetables", json={"name": "Grup"}).json()["id"]
    deneme = uret_ve_bekle(yonetici, pid)
    assert deneme["status"] == "basarili", deneme["report"]
    hucreler = yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]
    # Çözücü kurala uydu: aynı gün bitişik saatlerde iki matematik yok.
    gunluk: dict[int, list[int]] = {}
    for h in hucreler:
        gunluk.setdefault(h["day_index"], []).append(h["period_index"])
    for saatler in gunluk.values():
        saatler.sort()
        assert all(b - a > 1 for a, b in zip(saatler, saatler[1:])), gunluk
    assert yonetici.get(f"/api/timetables/{pid}/warnings").json() == []
