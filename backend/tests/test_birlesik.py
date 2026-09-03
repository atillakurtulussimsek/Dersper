"""Birleşik dersler: bir müfredat satırı birden fazla şubeye ait olabilir.

Beden eğitimi, din kültürü ve seçmeliler sık sık böyle okutulur: tek öğretmen,
tek saat, birkaç şube. Satırda birden fazla şube seçilmişse ders birleşiktir;
ayrı işlenen dersler kendi satırlarında kalır.
"""
from fastapi.testclient import TestClient

from app.solver.engine import Slot, SolveInput, solve, sube_etiketi, subeleri
from tests.conftest import uret_ve_bekle
from tests.test_engine import ders


def _okul(c: TestClient) -> dict:
    ogr = c.post("/api/teachers", json={"full_name": "Mehmet Demir"}).json()["id"]
    bed = c.post("/api/subjects", json={"name": "Beden Eğitimi"}).json()["id"]
    a = c.post("/api/sections", json={"name": "9-A"}).json()["id"]
    b = c.post("/api/sections", json={"name": "9-B"}).json()["id"]
    return {"ogretmen": ogr, "ders": bed, "a": a, "b": b}


# --- Tanımlama ---

def test_birlesik_ders_tanimlanir(yonetici: TestClient):
    o = _okul(yonetici)
    r = yonetici.post("/api/curriculum", json={
        "section_id": o["a"], "extra_section_ids": [o["b"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"],
        "weekly_hours": 2, "block_pattern": "2", "max_per_day": 2,
    })
    assert r.status_code == 201, r.text
    assert [s["name"] for s in r.json()["sections"]] == ["9-A", "9-B"]


def test_birlesik_ders_her_iki_subenin_listesinde_gorunur(yonetici: TestClient):
    o = _okul(yonetici)
    yonetici.post("/api/curriculum", json={
        "section_id": o["a"], "extra_section_ids": [o["b"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"], "weekly_hours": 2,
    })
    for sid in (o["a"], o["b"]):
        liste = yonetici.get(f"/api/curriculum?section_id={sid}").json()
        assert len(liste) == 1, sid
        assert len(liste[0]["sections"]) == 2


def test_ayni_sube_iki_kez_secilemez(yonetici: TestClient):
    o = _okul(yonetici)
    r = yonetici.post("/api/curriculum", json={
        "section_id": o["a"], "extra_section_ids": [o["b"], o["b"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"], "weekly_hours": 2,
    })
    assert r.status_code == 422, r.text


def test_asil_sube_ek_olarak_yazilirsa_yok_sayilir(yonetici: TestClient):
    """Arayüz seçili şubeleri olduğu gibi gönderebilsin diye."""
    o = _okul(yonetici)
    r = yonetici.post("/api/curriculum", json={
        "section_id": o["a"], "extra_section_ids": [o["a"], o["b"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"], "weekly_hours": 2,
    })
    assert r.status_code == 201, r.text
    assert len(r.json()["sections"]) == 2


def test_baska_donemin_subesi_birlestirilemez(yonetici: TestClient):
    o = _okul(yonetici)
    yeni = yonetici.post("/api/terms", json={"name": "Öteki"}).json()["id"]
    yonetici.post(f"/api/terms/{yeni}/activate")
    yabanci = yonetici.post("/api/sections", json={"name": "Yabancı"}).json()["id"]

    # Aktif dönem artık "Öteki"; o["a"] öbür döneme ait, ek şube olamaz.
    r = yonetici.post("/api/curriculum", json={
        "section_id": yabanci, "extra_section_ids": [o["a"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"], "weekly_hours": 2,
    })
    assert r.status_code == 404, r.text


# --- Kısmi birleşme ---

def test_ayni_ders_hem_birlesik_hem_ayri_tanimlanabilir(yonetici: TestClient):
    """2 saat 9-A+9-B birlikte, 1 saat 9-A tek — ikisi de meşrudur."""
    o = _okul(yonetici)
    birlesik = yonetici.post("/api/curriculum", json={
        "section_id": o["a"], "extra_section_ids": [o["b"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"], "weekly_hours": 2,
    })
    assert birlesik.status_code == 201, birlesik.text

    ayri = yonetici.post("/api/curriculum", json={
        "section_id": o["a"], "subject_id": o["ders"],
        "teacher_id": o["ogretmen"], "weekly_hours": 1,
    })
    assert ayri.status_code == 201, ayri.text

    liste = yonetici.get(f"/api/curriculum?section_id={o['a']}").json()
    assert sum(e["weekly_hours"] for e in liste) == 3


def test_ayni_sube_bilesimi_iki_kez_tanimlanamaz(yonetici: TestClient):
    o = _okul(yonetici)
    govde = {
        "section_id": o["a"], "extra_section_ids": [o["b"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"], "weekly_hours": 2,
    }
    assert yonetici.post("/api/curriculum", json=govde).status_code == 201
    assert yonetici.post("/api/curriculum", json=govde).status_code == 409


# --- Çözücü ---

def _slotlar(sayi: int = 4) -> list[Slot]:
    return [
        Slot(period_id=i + 1, day_index=0, period_index=i,
             day_name="Pazartesi", period_name=f"{i + 1}. ders")
        for i in range(sayi)
    ]


def test_birlesik_ders_tum_subeleri_ayni_anda_tutar():
    """9-A+9-B ortak beden dersi ile 9-B'nin kendi dersi çakışır."""
    ortak = ders(1, 1, 10, "Beden", 4, gunluk=4)
    ortak = type(ortak)(**{**ortak.__dict__, "sections": ((1, "9-A"), (2, "9-B"))})
    kendi = ders(2, 2, 11, "Matematik", 2, gunluk=2)

    assert subeleri(ortak) == {1, 2}
    assert sube_etiketi(ortak) == "9-A + 9-B"

    # 4 saatlik ızgarada 4 + 2 = 6 saat, 9-B ikisini de görüyor: sığmaz.
    sonuc = solve(SolveInput(slots=_slotlar(4), lessons=[ortak, kendi],
                             time_limit_seconds=5))
    assert not sonuc.ok


def test_birlesik_ders_ayri_subelerle_cakismaz():
    """Birleşmeye dahil olmayan şube aynı saati kullanabilir."""
    ortak = ders(1, 1, 10, "Beden", 4, gunluk=4)
    ortak = type(ortak)(**{**ortak.__dict__, "sections": ((1, "9-A"), (2, "9-B"))})
    uzak = ders(2, 3, 11, "Matematik", 4, gunluk=4)

    sonuc = solve(SolveInput(slots=_slotlar(4), lessons=[ortak, uzak],
                             time_limit_seconds=5))
    assert sonuc.ok
    assert len(sonuc.placements) == 8


# --- Uçtan uca ---

def test_birlesik_ders_uretilir_ve_her_subenin_izgarasinda_gorunur(yonetici: TestClient):
    o = _okul(yonetici)
    yonetici.post("/api/curriculum", json={
        "section_id": o["a"], "extra_section_ids": [o["b"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"],
        "weekly_hours": 2, "block_pattern": "2", "max_per_day": 2,
    })
    pid = yonetici.post("/api/timetables", json={"name": "Deneme"}).json()["id"]
    uret_ve_bekle(yonetici, pid)

    hucreler = yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]
    assert len(hucreler) == 2, hucreler
    for h in hucreler:
        assert sorted(h["section_names"]) == ["9-A", "9-B"]


def test_birlesik_ders_kopyalanmaz(yonetici: TestClient):
    o = _okul(yonetici)
    e = yonetici.post("/api/curriculum", json={
        "section_id": o["a"], "extra_section_ids": [o["b"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"], "weekly_hours": 2,
    }).json()
    c = yonetici.post("/api/sections", json={"name": "9-C"}).json()["id"]

    r = yonetici.post("/api/curriculum/copy", json={
        "entry_ids": [e["id"]], "section_ids": [c],
    })
    assert r.status_code == 201, r.text
    assert r.json()["created"] == []
    assert "birleşik" in r.json()["skipped"][0]


def test_birlesik_dersin_saatine_baska_sube_dersi_elle_konamaz(yonetici: TestClient):
    """Elle düzenleme de birleşmeyi bilir; gerekçe çakışan şubeyi söyler."""
    o = _okul(yonetici)
    ortak = yonetici.post("/api/curriculum", json={
        "section_id": o["a"], "extra_section_ids": [o["b"]],
        "subject_id": o["ders"], "teacher_id": o["ogretmen"], "weekly_hours": 1,
    }).json()["id"]
    mat = yonetici.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    ayse = yonetici.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    bnin = yonetici.post("/api/curriculum", json={
        "section_id": o["b"], "subject_id": mat, "teacher_id": ayse, "weekly_hours": 1,
    }).json()["id"]

    pid = yonetici.post("/api/timetables", json={"name": "Deneme"}).json()["id"]
    saat = sorted(
        yonetici.get("/api/timegrid").json()[0]["periods"], key=lambda p: p["index"]
    )[0]["id"]

    ilk = yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": ortak, "period_id": saat, "uzunluk": 1,
    })
    assert ilk.status_code == 200, ilk.text

    ikinci = yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": bnin, "period_id": saat, "uzunluk": 1,
    })
    assert ikinci.status_code == 409, ikinci.text
    assert "9-B" in ikinci.json()["detail"], ikinci.json()
