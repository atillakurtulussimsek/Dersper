"""Kayıt kilidi: şube / öğretmen programı dondurulur (bkz. app.kilit)."""
from fastapi.testclient import TestClient

from tests.conftest import uret_ve_bekle
from tests.test_duzenle import _hucreler, _konum, _okul, _program


def _kilitle(c: TestClient, pid: int, tur: str, kimlik: int, kilitli: bool = True):
    return c.post(f"/api/timetables/{pid}/record-lock",
                  json={"tur": tur, "kimlik": kimlik, "kilitli": kilitli})


def test_kilitli_subenin_dersi_tasinamaz_ve_rafa_alinamaz(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    r = _kilitle(yonetici, pid, "sube", okul["subeler"]["a"])
    assert r.status_code == 200, r.text
    assert r.json()["timetable"]["locked_section_ids"] == [okul["subeler"]["a"]]
    assert all(h["record_locked"] for h in r.json()["cells"])

    hucre = _hucreler(yonetici, pid)[0]
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": okul["saatler"][3]["id"]})
    assert r.status_code == 409 and "9-A şubesi kilitli" in r.text
    r = yonetici.post(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/unplace")
    assert r.status_code == 409
    # Bekleyen dersi de yerleştirilemez (a_trk aynı şubede).
    r = yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": okul["atamalar"]["a_trk"],
        "period_id": okul["saatler"][3]["id"], "uzunluk": 2})
    assert r.status_code == 409 and "kilitli" in r.text

    # Kilit açılınca serbest.
    assert _kilitle(yonetici, pid, "sube", okul["subeler"]["a"], False).status_code == 200
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": okul["saatler"][3]["id"]})
    assert r.status_code == 200, r.text


def test_kilitli_ogretmenin_dersi_tasinamaz(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("b_mat", 0)])           # Ayşe, 9-B
    assert _kilitle(yonetici, pid, "ogretmen", okul["ogretmenler"]["ayse"]).status_code == 200
    hucre = _hucreler(yonetici, pid)[0]
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": okul["saatler"][3]["id"]})
    assert r.status_code == 409 and "Ayşe Yılmaz kilitli" in r.text
    surumler = yonetici.get(f"/api/timetables/{pid}/versions").json()
    assert "Ayşe Yılmaz kilitlendi" in surumler[0]["label"]


def test_uretim_kilitli_subeye_dokunmaz(yonetici: TestClient):
    """9-A'nın 2 saati elle konmuş, 2 saati (Türkçe) rafta. Kilitlenince üretim
    9-A'yı olduğu gibi bırakır: Matematik yerinde, Türkçe yerleşmez; 9-B
    yerleşir ve Ayşe'nin 9-A'daki saatleriyle çakışmaz."""
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 4)])           # 9-A Mat: 4-5. saatler
    assert _kilitle(yonetici, pid, "sube", okul["subeler"]["a"]).status_code == 200
    once = _konum(yonetici, pid, "a_mat")

    uret_ve_bekle(yonetici, pid)
    assert _konum(yonetici, pid, "a_mat") == once
    assert _konum(yonetici, pid, "a_trk") == []              # kilitli: yerleşmedi
    b = _konum(yonetici, pid, "b_mat")
    assert len(b) == 1 and b[0] not in once                 # Ayşe çakışmadı
    hucreler = _hucreler(yonetici, pid)
    assert {h["record_locked"] for h in hucreler if h["section_name"] == "9-A"} == {True}
    assert {h["record_locked"] for h in hucreler if h["section_name"] == "9-B"} == {False}


def test_uretim_kilitli_ogretmene_dokunmaz(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("b_mat", 2)])           # Ayşe 9-B, 3. saat
    assert _kilitle(yonetici, pid, "ogretmen", okul["ogretmenler"]["ayse"]).status_code == 200
    uret_ve_bekle(yonetici, pid)
    assert _konum(yonetici, pid, "b_mat") == [okul["saatler"][2]["id"]]
    assert _konum(yonetici, pid, "a_mat") == []              # Ayşe'nin öbür dersi de donuk
    assert len(_konum(yonetici, pid, "a_trk")) == 2          # Mehmet serbest
