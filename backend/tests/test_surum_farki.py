"""Sürüm farkı: iki sürüm arasında ne değişti?

Fark ders bazında okunur: aynı dersin bir saati gidip başka bir saati geldiyse
TAŞIMAdır; eşleşmeyenler çıkan/eklenen saatlerdir; yerinde durup kilidi
değişen saat ayrıca listelenir.
"""
from fastapi.testclient import TestClient

from tests.test_duzenle import _okul


def _saatler(c: TestClient) -> list[int]:
    """İlk günün ders saatleri, sırayla."""
    g = c.get("/api/timegrid").json()[0]
    return [p["id"] for p in sorted(g["periods"], key=lambda x: x["index"])]


def _program(c: TestClient) -> int:
    return c.post("/api/timetables", json={"name": "Deneme"}).json()["id"]


def _son_surum(c: TestClient, pid: int) -> int:
    return c.get(f"/api/timetables/{pid}/versions").json()[0]["number"]


def _ilk_surum(c: TestClient, pid: int) -> int:
    """"Başlangıç" sürümü; ilk düzenlemeyle birlikte yazılır."""
    return c.get(f"/api/timetables/{pid}/versions").json()[-1]["number"]


def _fark(c: TestClient, pid: int, a: int, b: int) -> dict:
    r = c.get(f"/api/timetables/{pid}/versions/{a}/diff/{b}")
    assert r.status_code == 200, r.text
    return r.json()


def test_ayni_surum_bos_fark_verir(yonetici: TestClient):
    a = _okul(yonetici)
    pid = _program(yonetici)
    s = _saatler(yonetici)
    yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": a["atamalar"]["a_mat"], "period_id": s[0], "uzunluk": 2})
    v = _son_surum(yonetici, pid)
    f = _fark(yonetici, pid, v, v)
    assert f["degisiklikler"] == []
    assert f["ozet"]["degisen_ders"] == 0


def test_yerlestirme_eklendi_olarak_gorunur(yonetici: TestClient):
    a = _okul(yonetici)
    pid = _program(yonetici)
    s = _saatler(yonetici)
    r = yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": a["atamalar"]["a_mat"], "period_id": s[0], "uzunluk": 2})
    assert r.status_code == 200, r.text
    v0, v1 = _ilk_surum(yonetici, pid), _son_surum(yonetici, pid)

    f = _fark(yonetici, pid, v0, v1)
    assert f["ozet"] == {"tasindi": 0, "cikti": 0, "eklendi": 2, "kilit": 0, "degisen_ders": 1}
    d = f["degisiklikler"][0]
    assert d["tur"] == "eklendi" and d["kaynak"] is None
    assert d["sube"] == "9-A" and d["ders"] == "Matematik" and d["ogretmen"] == "Ayşe Yılmaz"
    assert d["hedef"]["saat"]


def test_tasima_tasindi_olarak_eslesir(yonetici: TestClient):
    a = _okul(yonetici)
    pid = _program(yonetici)
    s = _saatler(yonetici)
    yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": a["atamalar"]["a_mat"], "period_id": s[0], "uzunluk": 2})
    v1 = _son_surum(yonetici, pid)
    hucre = next(h for h in yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]
                 if h["period_id"] == s[0])
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": s[3]})
    assert r.status_code == 200, r.text
    v2 = _son_surum(yonetici, pid)

    f = _fark(yonetici, pid, v1, v2)
    assert f["ozet"]["tasindi"] == 2 and f["ozet"]["cikti"] == 0 and f["ozet"]["eklendi"] == 0
    kaynaklar = sorted(d["kaynak"]["period_id"] for d in f["degisiklikler"])
    hedefler = sorted(d["hedef"]["period_id"] for d in f["degisiklikler"])
    assert kaynaklar == [s[0], s[1]] and hedefler == [s[3], s[4]]

    # Ters yönde bakınca taşıma tersine döner.
    g = _fark(yonetici, pid, v2, v1)
    assert sorted(d["kaynak"]["period_id"] for d in g["degisiklikler"]) == [s[3], s[4]]


def test_izgaradan_alma_cikti_olarak_gorunur(yonetici: TestClient):
    a = _okul(yonetici)
    pid = _program(yonetici)
    s = _saatler(yonetici)
    yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": a["atamalar"]["a_mat"], "period_id": s[0], "uzunluk": 2})
    v1 = _son_surum(yonetici, pid)
    hucre = next(h for h in yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]
                 if h["period_id"] == s[0])
    yonetici.post(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/unplace")
    v2 = _son_surum(yonetici, pid)

    f = _fark(yonetici, pid, v1, v2)
    assert f["ozet"]["cikti"] == 2
    assert all(d["tur"] == "cikti" and d["hedef"] is None for d in f["degisiklikler"])


def test_kilit_degisimi_ayrica_listelenir(yonetici: TestClient):
    a = _okul(yonetici)
    pid = _program(yonetici)
    s = _saatler(yonetici)
    r = yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": a["atamalar"]["a_mat"], "period_id": s[0], "uzunluk": 2})
    assert r.status_code == 200, r.text
    v1 = _son_surum(yonetici, pid)
    hucre = yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"][0]
    r = yonetici.post(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/lock")
    assert r.status_code == 200, r.text
    v2 = _son_surum(yonetici, pid)

    f = _fark(yonetici, pid, v1, v2)
    assert f["ozet"]["kilit"] == 1
    assert f["degisiklikler"][0]["tur"] == "kilitlendi"


def test_olmayan_surum_404(yonetici: TestClient):
    a = _okul(yonetici)
    pid = _program(yonetici)
    yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": a["atamalar"]["a_mat"], "period_id": _saatler(yonetici)[0],
        "uzunluk": 2})
    assert yonetici.get(f"/api/timetables/{pid}/versions/1/diff/999").status_code == 404
