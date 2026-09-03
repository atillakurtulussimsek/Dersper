"""Sonsuz mod: kanıtlı çözümsüzlükte bile durdurulana kadar denemeye devam
eder, her farklı denemeyi sürüm olarak yazar, günlük tutar."""
import time

from fastapi.testclient import TestClient


def _cozumsuz_okul(c: TestClient) -> int:
    """Tek gün, 2 saat; 3 saatlik ders: kesin çözümsüz ama gevşek çözüm var."""
    g = c.get("/api/timegrid").json()[0]
    saatler = sorted(g["periods"], key=lambda x: x["index"])[:2]
    c.put("/api/timegrid", json=[{
        "index": g["index"], "name": g["name"], "is_active": True,
        "periods": [{"id": p["id"], "index": p["index"], "name": p["name"],
                     "start_time": None, "end_time": None,
                     "is_break": False, "is_lunch": False} for p in saatler],
    }])
    ders = c.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    ogr = c.post("/api/teachers", json={"full_name": "Tek Öğretmen"}).json()["id"]
    sube = c.post("/api/sections", json={"name": "9-A"}).json()["id"]
    c.post("/api/curriculum", json={"section_id": sube, "subject_id": ders, "teacher_id": ogr,
                                    "weekly_hours": 3, "block_pattern": "1+1+1", "max_per_day": 3})
    return c.post("/api/timetables", json={"name": "Sonsuz"}).json()["id"]


def _bekle(c: TestClient, pid: int, saniye: float):
    son = time.monotonic() + saniye
    while time.monotonic() < son:
        if c.get(f"/api/timetables/{pid}/runs/active").json() is None:
            return
        time.sleep(0.1)


def test_sonsuz_mod_kanitta_durmaz_ve_denemeleri_surume_yazar(yonetici: TestClient):
    pid = _cozumsuz_okul(yonetici)
    r = yonetici.patch(f"/api/timetables/{pid}", json={"endless_mode": True})
    assert r.status_code == 200 and r.json()["endless_mode"] is True, r.text

    run = yonetici.post(f"/api/timetables/{pid}/solve").json()
    # Sonsuz mod: birkaç saniye içinde kanıt gelir ama iş bitmez, denemeler artar.
    time.sleep(6)
    aktif = yonetici.get(f"/api/timetables/{pid}/runs/active").json()
    assert aktif is not None, "sonsuz mod kanıtta durdu"
    assert aktif["proven_infeasible"] is True
    assert aktif["attempts"] >= 3
    assert aktif["log"] and {e["strateji"] for e in aktif["log"]} >= {"otomatik"}
    assert all("strateji_adi" in e and "sure_sn" in e for e in aktif["log"])

    yonetici.post(f"/api/timetables/{pid}/runs/{run['id']}/stop")
    _bekle(yonetici, pid, 20)

    # En iyi gevşek yerleşim ızgarada, denemeler geçmişte.
    assert len(yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]) == 2
    surumler = yonetici.get(f"/api/timetables/{pid}/versions").json()
    assert any(s["label"].startswith("Deneme ") for s in surumler), surumler


def test_normal_modda_cift_kanit_isi_bitirir(yonetici: TestClient):
    pid = _cozumsuz_okul(yonetici)
    yonetici.post(f"/api/timetables/{pid}/solve")
    _bekle(yonetici, pid, 30)
    son = yonetici.get(f"/api/timetables/{pid}/runs").json()[0]
    assert son["status"] == "cozumsuz", son["status"]
    assert son["attempts"] <= 3
    assert son["log"] and son["log"][-1]["kanit"] is True
