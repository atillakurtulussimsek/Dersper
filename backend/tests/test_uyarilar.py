"""Günlük sınırın esnetilmesi ve program uyarıları."""
from fastapi.testclient import TestClient

from tests.conftest import uret_ve_bekle


def _dar_okul(c: TestClient) -> dict:
    """Tek gün açık, 8 ders saati; 6 saatlik ders günlük sınırı aşmadan sığmaz."""
    izgara = c.get("/api/timegrid").json()
    for g in izgara:
        g["is_active"] = g["index"] == 0
    c.put("/api/timegrid", json=izgara)

    d = c.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    o = c.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    s = c.post("/api/sections", json={"name": "5-A"}).json()["id"]
    c.post("/api/curriculum", json={
        "section_id": s, "subject_id": d, "teacher_id": o,
        "weekly_hours": 4, "max_per_day": 2,
    })
    return {"pid": c.post("/api/timetables", json={"name": "Dar"}).json()["id"]}


def test_gunluk_sinir_esnetilerek_program_tamamlanir(yonetici: TestClient):
    v = _dar_okul(yonetici)
    kayit = uret_ve_bekle(yonetici, v["pid"])

    assert kayit["status"] == "basarili"
    hucreler = yonetici.get(f"/api/timetables/{v['pid']}/grid").json()["cells"]
    assert len(hucreler) == 4          # tüm saatler yerleşti


def test_esnetme_uyari_olarak_bildirilir(yonetici: TestClient):
    v = _dar_okul(yonetici)
    uret_ve_bekle(yonetici, v["pid"])

    uyarilar = yonetici.get(f"/api/timetables/{v['pid']}/warnings").json()
    asim = [u for u in uyarilar if u["tur"] == "gunluk_asim"]
    assert len(asim) == 1
    assert asim[0]["konan"] == 4
    assert asim[0]["sinir"] == 2
    assert asim[0]["sube"] == "5-A"
    assert asim[0]["ders"] == "Matematik"
    assert asim[0]["ignored"] is False
    assert "sınır esnetildi" in asim[0]["detay"]


def test_esnetilen_saatler_arka_arkaya_gelmez(yonetici: TestClient):
    """Aynı ders gün içinde birden çok kez konurken araya başka saat girmeli."""
    v = _dar_okul(yonetici)
    uret_ve_bekle(yonetici, v["pid"])

    hucreler = yonetici.get(f"/api/timetables/{v['pid']}/grid").json()["cells"]
    saatler = sorted(h["period_index"] for h in hucreler)
    assert all(b - a > 1 for a, b in zip(saatler, saatler[1:])), saatler

    # Bitişiklik uyarısı da çıkmamalı.
    uyarilar = yonetici.get(f"/api/timetables/{v['pid']}/warnings").json()
    assert [u for u in uyarilar if u["tur"] == "bitisik"] == []


def test_sorunsuz_programda_uyari_olmaz(yonetici: TestClient):
    d = yonetici.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    o = yonetici.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    s = yonetici.post("/api/sections", json={"name": "5-A"}).json()["id"]
    yonetici.post("/api/curriculum", json={
        "section_id": s, "subject_id": d, "teacher_id": o,
        "weekly_hours": 5, "max_per_day": 2,
    })
    pid = yonetici.post("/api/timetables", json={"name": "Rahat"}).json()["id"]
    uret_ve_bekle(yonetici, pid)
    assert yonetici.get(f"/api/timetables/{pid}/warnings").json() == []


def test_uyari_gizlenir_ve_geri_getirilir(yonetici: TestClient):
    v = _dar_okul(yonetici)
    uret_ve_bekle(yonetici, v["pid"])

    uyari = yonetici.get(f"/api/timetables/{v['pid']}/warnings").json()[0]
    sonra = yonetici.post(f"/api/timetables/{v['pid']}/warnings/ignore",
                          json={"key": uyari["key"]}).json()
    assert next(u for u in sonra if u["key"] == uyari["key"])["ignored"] is True

    # Kalıcı: yeniden sorulduğunda da gizli.
    tekrar = yonetici.get(f"/api/timetables/{v['pid']}/warnings").json()
    assert next(u for u in tekrar if u["key"] == uyari["key"])["ignored"] is True

    geri = yonetici.delete(
        f"/api/timetables/{v['pid']}/warnings/ignore/{uyari['key']}").json()
    assert next(u for u in geri if u["key"] == uyari["key"])["ignored"] is False


def test_gizleme_yalnizca_o_programi_etkiler(yonetici: TestClient):
    v = _dar_okul(yonetici)
    uret_ve_bekle(yonetici, v["pid"])
    uyari = yonetici.get(f"/api/timetables/{v['pid']}/warnings").json()[0]
    yonetici.post(f"/api/timetables/{v['pid']}/warnings/ignore", json={"key": uyari["key"]})

    ikinci = yonetici.post("/api/timetables", json={"name": "İkinci"}).json()["id"]
    uret_ve_bekle(yonetici, ikinci)
    ikinci_uyarilar = yonetici.get(f"/api/timetables/{ikinci}/warnings").json()
    assert ikinci_uyarilar and all(u["ignored"] is False for u in ikinci_uyarilar)


def test_elle_tasima_bitisiklik_uyarisi_dogurur(yonetici: TestClient):
    """Çözücü bitişik koymaz; kullanıcı elle taşırsa uyarı çıkar."""
    d = yonetici.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    o = yonetici.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    s = yonetici.post("/api/sections", json={"name": "5-A"}).json()["id"]
    yonetici.post("/api/curriculum", json={
        "section_id": s, "subject_id": d, "teacher_id": o,
        "weekly_hours": 2, "max_per_day": 2,
    })
    pid = yonetici.post("/api/timetables", json={"name": "Elle"}).json()["id"]
    uret_ve_bekle(yonetici, pid)
    assert yonetici.get(f"/api/timetables/{pid}/warnings").json() == []

    izgara = yonetici.get("/api/timegrid").json()
    hucreler = yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]
    ilk = hucreler[0]
    gun = next(g for g in izgara if g["index"] == ilk["day_index"])
    komsu = next(p for p in gun["periods"] if p["index"] == ilk["period_index"] + 1)

    tasinan = next(h for h in hucreler if h["assignment_id"] != ilk["assignment_id"])
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{tasinan['assignment_id']}",
                       json={"period_id": komsu["id"]})
    assert r.status_code == 200

    uyarilar = yonetici.get(f"/api/timetables/{pid}/warnings").json()
    bitisik = [u for u in uyarilar if u["tur"] == "bitisik"]
    assert len(bitisik) == 1
    assert "arka arkaya" in bitisik[0]["baslik"]


def test_blok_ders_bitisiklik_uyarisi_vermez(yonetici: TestClient):
    """2 saatlik blok zaten ardışıktır; uyarı sayılmamalı."""
    d = yonetici.post("/api/subjects", json={"name": "Fen"}).json()["id"]
    o = yonetici.post("/api/teachers", json={"full_name": "Fatma Şahin"}).json()["id"]
    s = yonetici.post("/api/sections", json={"name": "5-A"}).json()["id"]
    yonetici.post("/api/curriculum", json={
        "section_id": s, "subject_id": d, "teacher_id": o,
        "weekly_hours": 2, "block_pattern": "2", "max_per_day": 2,
    })
    pid = yonetici.post("/api/timetables", json={"name": "Blok"}).json()["id"]
    uret_ve_bekle(yonetici, pid)
    assert yonetici.get(f"/api/timetables/{pid}/warnings").json() == []
