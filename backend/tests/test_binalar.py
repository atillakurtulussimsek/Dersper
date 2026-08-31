"""Binalar: tanım, şubeye bağlama ve "bir günde tek bina" kuralı."""
from fastapi.testclient import TestClient

from tests.conftest import uret_ve_bekle


def _iki_binali_okul(c: TestClient) -> dict:
    """İki bina, her binada bir şube, ikisine de giren tek öğretmen."""
    a = c.post("/api/buildings", json={"name": "A Binası", "short_code": "A"}).json()
    b = c.post("/api/buildings", json={"name": "B Binası", "short_code": "B"}).json()
    ders = c.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    ogr = c.post("/api/teachers", json={"full_name": "Gezgin Öğretmen"}).json()["id"]
    sube_a = c.post("/api/sections", json={
        "name": "9-A", "building_id": a["id"]}).json()["id"]
    sube_b = c.post("/api/sections", json={
        "name": "9-B", "building_id": b["id"]}).json()["id"]
    for sube in (sube_a, sube_b):
        c.post("/api/curriculum", json={
            "section_id": sube, "subject_id": ders, "teacher_id": ogr,
            "weekly_hours": 4, "max_per_day": 2,
        })
    return {"binalar": {"a": a, "b": b}, "subeler": {"a": sube_a, "b": sube_b},
            "ogretmen": ogr}


def _donem_ayari(c: TestClient, acik: bool) -> None:
    donem = next(d for d in c.get("/api/terms").json() if d["is_active"])
    r = c.put(f"/api/terms/{donem['id']}", json={
        "name": donem["name"], "block_building_switch": acik,
    })
    assert r.status_code == 200, r.text


def test_bina_tanimlanir_ve_subeye_baglanir(yonetici: TestClient):
    bina = yonetici.post("/api/buildings", json={
        "name": "Ek Bina", "short_code": "EK", "notes": "Yolun karşısı",
    })
    assert bina.status_code == 201, bina.text
    bina = bina.json()

    sube = yonetici.post("/api/sections", json={
        "name": "10-A", "building_id": bina["id"],
    }).json()
    assert sube["building_id"] == bina["id"]
    assert yonetici.get("/api/buildings").json()[0]["short_code"] == "EK"


def test_sube_binasiz_kalabilir(yonetici: TestClient):
    """Tek binalı kurumlar bina tanımlamak zorunda değil."""
    sube = yonetici.post("/api/sections", json={"name": "10-B"}).json()
    assert sube["building_id"] is None


def test_baska_donemin_binasi_baglanamaz(yonetici: TestClient):
    bina = yonetici.post("/api/buildings", json={"name": "A"}).json()
    yeni = yonetici.post("/api/terms", json={"name": "Öteki"}).json()["id"]
    yonetici.post(f"/api/terms/{yeni}/activate")

    r = yonetici.post("/api/sections", json={"name": "9-A", "building_id": bina["id"]})
    assert r.status_code == 404


def test_bina_silinince_subeler_binasiz_kalir(yonetici: TestClient):
    bina = yonetici.post("/api/buildings", json={"name": "Yıkılan"}).json()
    sube = yonetici.post("/api/sections", json={
        "name": "9-A", "building_id": bina["id"]}).json()

    assert yonetici.delete(f"/api/buildings/{bina['id']}").status_code == 204
    kalan = yonetici.get("/api/sections").json()
    assert next(s for s in kalan if s["id"] == sube["id"])["building_id"] is None
    assert yonetici.get("/api/buildings").json() == []


def test_bina_kurali_gunleri_ayirir(yonetici: TestClient):
    """Kural açıkken öğretmenin bir günü tek binaya ait olur."""
    okul = _iki_binali_okul(yonetici)
    _donem_ayari(yonetici, True)

    pid = yonetici.post("/api/timetables", json={"name": "Bina"}).json()["id"]
    deneme = uret_ve_bekle(yonetici, pid)
    assert deneme["status"] == "basarili", deneme["report"]

    hucreler = yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]
    sube_bina = {okul["subeler"]["a"]: "A", okul["subeler"]["b"]: "B"}
    gunler: dict[int, set[str]] = {}
    for h in hucreler:
        gunler.setdefault(h["day_index"], set()).add(sube_bina[h["section_id"]])
    for gun, binalar in gunler.items():
        assert len(binalar) == 1, f"{gun}. günde iki bina: {binalar}"


def test_kural_kapaliyken_binalar_ayni_gune_gelebilir(yonetici: TestClient):
    """Varsayılan kapalı: bina bir kısıt değil."""
    _iki_binali_okul(yonetici)
    _donem_ayari(yonetici, False)

    pid = yonetici.post("/api/timetables", json={"name": "Serbest"}).json()["id"]
    deneme = uret_ve_bekle(yonetici, pid)
    assert deneme["status"] == "basarili", deneme["report"]
    assert len(yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]) == 8


def test_bina_gecisi_uyarisi_kural_kapaliyken_cikmaz(yonetici: TestClient):
    okul = _iki_binali_okul(yonetici)
    _donem_ayari(yonetici, False)
    pid = yonetici.post("/api/timetables", json={"name": "Uyarısız"}).json()["id"]
    uret_ve_bekle(yonetici, pid)

    uyarilar = yonetici.get(f"/api/timetables/{pid}/warnings").json()
    assert not [u for u in uyarilar if u["tur"] == "bina_gecisi"]
    assert okul


def test_bina_gecisi_uyarisi_asimda_cikar(yonetici: TestClient):
    """Kural açık ama tek güne sıkışan yük: program üretilir, aşım uyarılır."""
    a = yonetici.post("/api/buildings", json={"name": "A Binası"}).json()
    b = yonetici.post("/api/buildings", json={"name": "B Binası"}).json()
    ders = yonetici.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    ogr = yonetici.post("/api/teachers", json={"full_name": "Sıkışık"}).json()["id"]

    # Izgarayı tek güne indir: iki bina aynı güne düşmek zorunda kalır.
    gunler = yonetici.get("/api/timegrid").json()
    yonetici.put("/api/timegrid", json=[{
        "index": gunler[0]["index"], "name": gunler[0]["name"], "is_active": True,
        "periods": [
            {"id": p["id"], "index": p["index"], "name": p["name"],
             "start_time": None, "end_time": None, "is_break": False,
             "is_lunch": False}
            for p in sorted(gunler[0]["periods"], key=lambda x: x["index"])
        ],
    }])
    for ad, bina in (("9-A", a), ("9-B", b)):
        sube = yonetici.post("/api/sections", json={
            "name": ad, "building_id": bina["id"]}).json()["id"]
        yonetici.post("/api/curriculum", json={
            "section_id": sube, "subject_id": ders, "teacher_id": ogr,
            "weekly_hours": 4, "block_pattern": "2+2", "max_per_day": 4,
        })
    _donem_ayari(yonetici, True)

    pid = yonetici.post("/api/timetables", json={"name": "Sıkışık"}).json()["id"]
    uret_ve_bekle(yonetici, pid, saniye=120.0)

    uyarilar = yonetici.get(f"/api/timetables/{pid}/warnings").json()
    bina_uyarisi = [u for u in uyarilar if u["tur"] == "bina_gecisi"]
    assert bina_uyarisi, uyarilar
    assert bina_uyarisi[0]["ogretmen"] == "Sıkışık"
    assert "A Binası" in bina_uyarisi[0]["detay"]


def test_binasiz_sube_kurali_tetiklemez(yonetici: TestClient):
    """Binası olmayan şube, binalı şubeyle aynı güne girebilir."""
    a = yonetici.post("/api/buildings", json={"name": "A Binası"}).json()
    ders = yonetici.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    ogr = yonetici.post("/api/teachers", json={"full_name": "Karma"}).json()["id"]
    gunler = yonetici.get("/api/timegrid").json()
    yonetici.put("/api/timegrid", json=[{
        "index": gunler[0]["index"], "name": gunler[0]["name"], "is_active": True,
        "periods": [
            {"id": p["id"], "index": p["index"], "name": p["name"],
             "start_time": None, "end_time": None, "is_break": False,
             "is_lunch": False}
            for p in sorted(gunler[0]["periods"], key=lambda x: x["index"])
        ],
    }])
    for ad, bina_id in (("9-A", a["id"]), ("9-B", None)):
        sube = yonetici.post("/api/sections", json={
            "name": ad, "building_id": bina_id}).json()["id"]
        yonetici.post("/api/curriculum", json={
            "section_id": sube, "subject_id": ders, "teacher_id": ogr,
            "weekly_hours": 4, "block_pattern": "2+2", "max_per_day": 4,
        })
    _donem_ayari(yonetici, True)

    pid = yonetici.post("/api/timetables", json={"name": "Karma"}).json()["id"]
    deneme = uret_ve_bekle(yonetici, pid)
    assert deneme["status"] == "basarili", deneme["report"]
    assert len(yonetici.get(f"/api/timetables/{pid}/grid").json()["cells"]) == 8


def test_binalar_baska_doneme_aktarilir(yonetici: TestClient):
    yonetici.post("/api/buildings", json={"name": "A Binası", "short_code": "A"})
    ilk = next(d["id"] for d in yonetici.get("/api/terms").json() if d["is_active"])
    yeni = yonetici.post("/api/terms", json={"name": "Sonraki"}).json()["id"]
    yonetici.post(f"/api/terms/{yeni}/activate")

    aday = yonetici.get(f"/api/buildings/import/{ilk}").json()
    yonetici.post("/api/buildings/import", json={
        "term_id": ilk, "ids": [aday[0]["id"]]})
    assert yonetici.get("/api/buildings").json()[0]["name"] == "A Binası"


def test_sube_aktariminda_bina_ada_gore_eslenir(yonetici: TestClient):
    """Bina kimlikleri döneme özgü; eşleme ada göre yapılır."""
    bina = yonetici.post("/api/buildings", json={"name": "A Binası"}).json()
    yonetici.post("/api/sections", json={"name": "9-A", "building_id": bina["id"]})
    ilk = next(d["id"] for d in yonetici.get("/api/terms").json() if d["is_active"])

    yeni = yonetici.post("/api/terms", json={"name": "Sonraki"}).json()["id"]
    yonetici.post(f"/api/terms/{yeni}/activate")
    yeni_bina = yonetici.post("/api/buildings", json={"name": "A Binası"}).json()

    aday = yonetici.get(f"/api/sections/import/{ilk}").json()
    yonetici.post("/api/sections/import", json={"term_id": ilk, "ids": [aday[0]["id"]]})
    tasinan = yonetici.get("/api/sections").json()[0]
    assert tasinan["building_id"] == yeni_bina["id"]


def test_bina_yoksa_aktarilan_sube_binasiz_gelir(yonetici: TestClient):
    bina = yonetici.post("/api/buildings", json={"name": "A Binası"}).json()
    yonetici.post("/api/sections", json={"name": "9-A", "building_id": bina["id"]})
    ilk = next(d["id"] for d in yonetici.get("/api/terms").json() if d["is_active"])

    yeni = yonetici.post("/api/terms", json={"name": "Sonraki"}).json()["id"]
    yonetici.post(f"/api/terms/{yeni}/activate")

    aday = yonetici.get(f"/api/sections/import/{ilk}").json()
    yonetici.post("/api/sections/import", json={"term_id": ilk, "ids": [aday[0]["id"]]})
    assert yonetici.get("/api/sections").json()[0]["building_id"] is None


def test_binalar_baska_kuruma_sizmaz(yonetici: TestClient, istemci: TestClient):
    yonetici.post("/api/buildings", json={"name": "Gizli Bina"})

    istemci.post("/api/auth/register", json={
        "institution_name": "Öteki", "term_name": "2026",
        "full_name": "Öteki Yönetici", "email": "oteki3@ornek.com",
        "password": "sifre1234",
    })
    jeton = istemci.post("/api/auth/login", json={
        "email": "oteki3@ornek.com", "password": "sifre1234"}).json()["access_token"]
    istemci.headers["Authorization"] = f"Bearer {jeton}"
    assert istemci.get("/api/buildings").json() == []
