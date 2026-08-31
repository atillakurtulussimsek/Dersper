"""Sürüm geçmişi: her değişiklik kaydedilir, hiçbir sürüm silinmez.

Kurulum `test_duzenle` ile aynı: küçük ve elle izlenebilir bir okul.
"""
from fastapi.testclient import TestClient

from tests.conftest import uret_ve_bekle
from tests.test_duzenle import _hucreler, _konum, _okul, _program


def _surumler(c: TestClient, pid: int) -> list[dict]:
    return c.get(f"/api/timetables/{pid}/versions").json()


def _numaralar(c: TestClient, pid: int) -> list[int]:
    return [s["number"] for s in _surumler(c, pid)]


def test_her_degisiklik_surum_birakir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    # 1: Başlangıç (boş), 2: yerleştirme
    assert _numaralar(yonetici, pid) == [2, 1]

    hucre = _hucreler(yonetici, pid)[0]
    yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                   json={"period_id": okul["saatler"][3]["id"]})
    assert _numaralar(yonetici, pid) == [3, 2, 1]

    surum = _surumler(yonetici, pid)[0]
    assert surum["kind"] == "elle"
    assert "Matematik" in surum["label"]
    assert surum["placed"] == 2


def test_surum_numaralari_otomatik_ve_artan(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0), ("a_trk", 2)])
    hucre = next(h for h in _hucreler(yonetici, pid) if h["subject_name"] == "Matematik")
    for hedef in (4, 0, 4):
        yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": okul["saatler"][hedef]["id"]})
        hucre = next(h for h in _hucreler(yonetici, pid)
                     if h["subject_name"] == "Matematik")
    numaralar = _numaralar(yonetici, pid)
    assert numaralar == sorted(numaralar, reverse=True)
    assert numaralar[-1] == 1
    assert len(set(numaralar)) == len(numaralar)


def test_uretim_de_surum_birakir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = yonetici.post("/api/timetables", json={"name": "Üretim"}).json()["id"]
    uret_ve_bekle(yonetici, pid)

    surumler = _surumler(yonetici, pid)
    turler = [s["kind"] for s in surumler]
    assert "uretim" in turler
    uretim = next(s for s in surumler if s["kind"] == "uretim")
    assert "ders saati yerleşti" in uretim["label"]
    # Üretimden önceki hâl de bir dönüş noktası olarak duruyor.
    assert "ilk" in turler
    assert okul


def test_secilen_surume_donulur(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    ilk_yer = _konum(yonetici, pid, "a_mat")

    hucre = _hucreler(yonetici, pid)[0]
    yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                   json={"period_id": okul["saatler"][3]["id"]})
    assert _konum(yonetici, pid, "a_mat") != ilk_yer

    r = yonetici.post(f"/api/timetables/{pid}/versions/2/restore")
    assert r.status_code == 200, r.text
    assert _konum(yonetici, pid, "a_mat") == ilk_yer
    assert r.json()["version"] == 2


def test_geri_donmek_sonraki_surumleri_silmez(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                   json={"period_id": okul["saatler"][3]["id"]})
    once = _numaralar(yonetici, pid)

    yonetici.post(f"/api/timetables/{pid}/versions/2/restore")
    assert _numaralar(yonetici, pid) == once      # hiçbir şey silinmedi

    # v3'e ileri gidilebilir.
    r = yonetici.post(f"/api/timetables/{pid}/redo")
    assert r.status_code == 200
    assert r.json()["version"] == 3


def test_geri_alip_yeni_degisiklik_eski_dali_silmez(yonetici: TestClient):
    """Geri aldıktan sonra başka yöne gitmek eski dalı yok etmez."""
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                   json={"period_id": okul["saatler"][3]["id"]})     # v3
    yonetici.post(f"/api/timetables/{pid}/undo")                     # v2'ye dön

    hucre = _hucreler(yonetici, pid)[0]
    yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                   json={"period_id": okul["saatler"][2]["id"]})     # v4, dal ayrıldı

    numaralar = _numaralar(yonetici, pid)
    assert numaralar == [4, 3, 2, 1]        # v3 duruyor
    # Terk edilen dala listeden dönülebilir.
    r = yonetici.post(f"/api/timetables/{pid}/versions/3/restore")
    assert r.status_code == 200
    assert _konum(yonetici, pid, "a_mat") == [
        okul["saatler"][3]["id"], okul["saatler"][4]["id"]
    ]


def test_ileri_alma_en_son_gidilen_yone_gider(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                   json={"period_id": okul["saatler"][3]["id"]})     # v3
    yonetici.post(f"/api/timetables/{pid}/undo")
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                   json={"period_id": okul["saatler"][2]["id"]})     # v4
    yonetici.post(f"/api/timetables/{pid}/undo")                     # yine v2

    r = yonetici.post(f"/api/timetables/{pid}/redo")
    assert r.json()["version"] == 4          # v3 değil, en yeni dal


def test_kilit_degisikligi_de_surum_birakir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.post(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/lock")

    surum = _surumler(yonetici, pid)[0]
    assert "kilitlendi" in surum["label"]
    # Kilit tek yerleşime uygulanır; blok zaten bir saati kilitliyse taşınamaz.
    assert sum(1 for h in _hucreler(yonetici, pid) if h["is_locked"]) == 1

    yonetici.post(f"/api/timetables/{pid}/undo")
    assert not any(h["is_locked"] for h in _hucreler(yonetici, pid))


def test_silinen_ders_atamasi_surumden_atlanir(yonetici: TestClient):
    """Sürüm yazıldıktan sonra ders ataması silinmişse o satır atlanır."""
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0), ("a_trk", 2)])
    hucre = next(h for h in _hucreler(yonetici, pid) if h["subject_name"] == "Türkçe")
    yonetici.post(
        f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/unplace")

    yonetici.delete(f"/api/curriculum/{okul['atamalar']['a_trk']}")

    # Türkçe'nin ızgarada olduğu sürüme dönülüyor; o satırlar artık uygulanamaz.
    r = yonetici.post(f"/api/timetables/{pid}/versions/3/restore")
    assert r.status_code == 200
    dersler = {h["subject_name"] for h in _hucreler(yonetici, pid)}
    assert dersler == {"Matematik"}


def test_surumler_baska_kuruma_sizmaz(yonetici: TestClient, istemci: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])

    istemci.post("/api/auth/register", json={
        "institution_name": "Öteki", "term_name": "2026",
        "full_name": "Öteki Yönetici", "email": "oteki2@ornek.com",
        "password": "sifre1234",
    })
    jeton = istemci.post("/api/auth/login", json={
        "email": "oteki2@ornek.com", "password": "sifre1234",
    }).json()["access_token"]
    istemci.headers["Authorization"] = f"Bearer {jeton}"

    assert istemci.get(f"/api/timetables/{pid}/versions").status_code == 404
    assert istemci.post(f"/api/timetables/{pid}/versions/1/restore").status_code == 404


def test_olmayan_surume_donulemez(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    assert yonetici.post(f"/api/timetables/{pid}/versions/99/restore").status_code == 404
