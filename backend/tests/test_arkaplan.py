"""Arka planda süren program üretimi: ilerleme, durdurma, yeniden başlatma."""
import time

from fastapi.testclient import TestClient

from app.solver.arkaplan import yarim_kalanlari_isaretle
from tests.conftest import cozumsuz_calistir, uret_ve_bekle


def _cozulebilir_okul(c: TestClient) -> int:
    d = c.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    o = c.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    s = c.post("/api/sections", json={"name": "5-A"}).json()["id"]
    c.post("/api/curriculum", json={
        "section_id": s, "subject_id": d, "teacher_id": o, "weekly_hours": 6,
    })
    return c.post("/api/timetables", json={"name": "Arka plan"}).json()["id"]


def _cozumsuz_okul(c: TestClient) -> int:
    """Tek öğretmen iki şubede 50 saat: ızgarada 40 saat var, kanıtlanabilir şekilde sığmaz."""
    d = c.post("/api/subjects", json={"name": "Aşırı Yük"}).json()["id"]
    o = c.post("/api/teachers", json={"full_name": "Yorgun Öğretmen"}).json()["id"]
    for ad in ("12-Y", "12-Z"):
        s = c.post("/api/sections", json={"name": ad}).json()["id"]
        c.post("/api/curriculum", json={
            "section_id": s, "subject_id": d, "teacher_id": o,
            "weekly_hours": 25, "max_per_day": 8,
        })
    return c.post("/api/timetables", json={"name": "Çözümsüz"}).json()["id"]


def test_uretim_hemen_doner_ve_arka_planda_surer(yonetici: TestClient):
    pid = _cozulebilir_okul(yonetici)
    r = yonetici.post(f"/api/timetables/{pid}/solve")
    assert r.status_code == 202
    assert r.json()["status"] in ("bekliyor", "calisiyor")

    son = time.monotonic() + 60
    while time.monotonic() < son:
        if yonetici.get(f"/api/timetables/{pid}/runs/active").json() is None:
            break
        time.sleep(0.05)

    kayit = yonetici.get(f"/api/timetables/{pid}/runs").json()[0]
    assert kayit["status"] == "basarili"
    assert kayit["attempts"] >= 1
    assert kayit["best_placed"] == kayit["required"] == 6
    assert len(yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]) == 6


def test_ayni_anda_iki_uretim_baslatilamaz(yonetici: TestClient):
    pid = _cozumsuz_okul(yonetici)
    ilk = yonetici.post(f"/api/timetables/{pid}/solve")
    assert ilk.status_code == 202

    ikinci = yonetici.post(f"/api/timetables/{pid}/solve")
    assert ikinci.status_code == 409
    assert "zaten bir üretim çalışıyor" in ikinci.text

    yonetici.post(f"/api/timetables/{pid}/runs/{ilk.json()['id']}/stop")


def test_calisan_uretim_izlenebilir(yonetici: TestClient):
    pid = _cozumsuz_okul(yonetici)
    run_id = yonetici.post(f"/api/timetables/{pid}/solve").json()["id"]

    son = time.monotonic() + 30
    aktif = None
    while time.monotonic() < son:
        aktif = yonetici.get(f"/api/timetables/{pid}/runs/active").json()
        if aktif and aktif["attempts"] >= 1:
            break
        time.sleep(0.05)

    assert aktif is not None
    assert aktif["status"] == "calisiyor"
    assert aktif["attempts"] >= 1
    assert aktif["required"] == 50          # istenen toplam ders saati
    assert 0 < aktif["best_placed"] < 50    # en iyi deneme kısmen yerleştirdi
    assert aktif["report"] is not None

    yonetici.post(f"/api/timetables/{pid}/runs/{run_id}/stop")


def test_cozumsuzluk_kanitlandiginda_isaretlenir_ama_durmaz(yonetici: TestClient):
    pid = _cozumsuz_okul(yonetici)
    kayit = cozumsuz_calistir(yonetici, pid)
    assert kayit["proven_infeasible"] is True
    assert kayit["status"] == "durduruldu"   # kendiliğinden değil, testin durdurmasıyla


def test_durdurunca_en_iyi_yerlesim_kaydedilir(yonetici: TestClient):
    pid = _cozumsuz_okul(yonetici)
    kayit = cozumsuz_calistir(yonetici, pid)

    assert kayit["status"] == "durduruldu"
    assert kayit["stop_requested"] is True
    hucreler = yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]
    assert len(hucreler) == kayit["best_placed"] > 0


def test_denemeler_ilerledikce_artar(yonetici: TestClient):
    pid = _cozumsuz_okul(yonetici)
    run_id = yonetici.post(f"/api/timetables/{pid}/solve").json()["id"]

    ilk = 0
    son = time.monotonic() + 30
    while time.monotonic() < son:
        aktif = yonetici.get(f"/api/timetables/{pid}/runs/active").json()
        if aktif and aktif["attempts"] >= 2:
            ilk = aktif["attempts"]
            break
        time.sleep(0.05)

    yonetici.post(f"/api/timetables/{pid}/runs/{run_id}/stop")
    assert ilk >= 2, "arka arkaya deneme yapılmadı"


def test_gecmis_calistirmalar_listelenir(yonetici: TestClient):
    pid = _cozulebilir_okul(yonetici)
    uret_ve_bekle(yonetici, pid)
    uret_ve_bekle(yonetici, pid)

    gecmis = yonetici.get(f"/api/timetables/{pid}/runs").json()
    assert len(gecmis) == 2
    assert all(d["status"] == "basarili" for d in gecmis)
    # En yeni başta
    assert gecmis[0]["started_at"] >= gecmis[1]["started_at"]


def test_yeniden_baslatma_yarim_kalanlari_kapatir(yonetici: TestClient):
    pid = _cozumsuz_okul(yonetici)
    run_id = yonetici.post(f"/api/timetables/{pid}/solve").json()["id"]
    time.sleep(0.3)

    # Uygulama yeniden başlamış gibi davran.
    yarim_kalanlari_isaretle()
    kayit = next(d for d in yonetici.get(f"/api/timetables/{pid}/runs").json()
                 if d["id"] == run_id)
    assert kayit["status"] == "durduruldu"
    assert yonetici.get(f"/api/timetables/{pid}/runs/active").json() is None

    # Yeni üretim başlatılabilir olmalı.
    yeni = yonetici.post(f"/api/timetables/{pid}/solve")
    assert yeni.status_code == 202
    yonetici.post(f"/api/timetables/{pid}/runs/{yeni.json()['id']}/stop")


def test_bilinmeyen_calistirma_durdurulamaz(yonetici: TestClient):
    pid = _cozulebilir_okul(yonetici)
    assert yonetici.post(f"/api/timetables/{pid}/runs/9999/stop").status_code == 404
