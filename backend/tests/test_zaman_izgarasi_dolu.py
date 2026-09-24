"""Program varken zaman ızgarası: dersi olmayan gün/saat değiştirilebilir,
dersi olan dokunulmaz."""
from fastapi.testclient import TestClient

from tests.test_duzenle import _okul, _program


def _izgara(c: TestClient) -> list[dict]:
    return c.get("/api/timegrid").json()


def _kaydet(c: TestClient, izgara: list[dict]):
    return c.put("/api/timegrid", json=izgara)


def test_dersi_olmayan_gun_program_varken_kapatilir(yonetici: TestClient):
    okul = _okul(yonetici, gun_sayisi=2)
    _program(yonetici, okul, [("a_mat", 0)])            # dersler 1. günde
    izgara = _izgara(yonetici)
    izgara[1]["is_active"] = False
    r = _kaydet(yonetici, izgara)
    assert r.status_code == 200, r.text
    assert r.json()[1]["is_active"] is False


def test_dersi_olan_gun_kapatilamaz(yonetici: TestClient):
    okul = _okul(yonetici, gun_sayisi=2)
    _program(yonetici, okul, [("a_mat", 0)])
    izgara = _izgara(yonetici)
    izgara[0]["is_active"] = False
    r = _kaydet(yonetici, izgara)
    assert r.status_code == 409
    assert "kapatılamaz" in r.text and "2 ders" in r.text
    # Hangi programda, kimin, hangi şubede: kullanıcı başka programa bakıyor olabilir.
    assert "«Elle» programında 2 ders" in r.text
    assert "Ayşe Yılmaz — 9-A Matematik" in r.text
    assert _izgara(yonetici)[0]["is_active"] is True


def test_dersi_olmayan_gun_program_varken_silinir(yonetici: TestClient):
    okul = _okul(yonetici, gun_sayisi=2)
    _program(yonetici, okul, [("a_mat", 0)])
    izgara = _izgara(yonetici)
    r = _kaydet(yonetici, [izgara[0]])
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1


def test_dersi_olan_saat_silinemez_ve_teneffuse_cevrilemez(yonetici: TestClient):
    okul = _okul(yonetici, gun_sayisi=2)
    _program(yonetici, okul, [("a_mat", 0)])            # 1. günün 1-2. saatleri
    izgara = _izgara(yonetici)
    sirali = sorted(izgara[0]["periods"], key=lambda p: p["index"])

    izgara[0]["periods"] = sirali[1:]                   # ilk saati sil
    r = _kaydet(yonetici, izgara)
    assert r.status_code == 409 and "silinemez" in r.text

    izgara = _izgara(yonetici)
    sorted(izgara[0]["periods"], key=lambda p: p["index"])[0]["is_break"] = True
    r = _kaydet(yonetici, izgara)
    assert r.status_code == 409 and "teneffüse" in r.text


def test_dersi_olmayan_saat_program_varken_silinir_ve_ad_degisir(yonetici: TestClient):
    okul = _okul(yonetici, gun_sayisi=2)
    _program(yonetici, okul, [("a_mat", 0)])
    izgara = _izgara(yonetici)
    sirali = sorted(izgara[0]["periods"], key=lambda p: p["index"])
    sirali[0]["name"] = "Sabah 1"
    izgara[0]["periods"] = sirali[:-1]                  # son (boş) saati sil
    r = _kaydet(yonetici, izgara)
    assert r.status_code == 200, r.text
    yeni = sorted(r.json()[0]["periods"], key=lambda p: p["index"])
    assert yeni[0]["name"] == "Sabah 1" and len(yeni) == len(sirali) - 1
    # Yerleşim yerinde duruyor.
    pid = yonetici.get("/api/timetables").json()[0]["id"]
    assert len(yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]) == 2
