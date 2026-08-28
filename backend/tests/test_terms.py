"""Dönemler, dönem yalıtımı, geçmiş dönemden aktarma ve yumuşak silme."""
from fastapi.testclient import TestClient


def _donem_ac(c: TestClient, ad: str) -> int:
    """Yeni dönem açar ve aktif dönem yapar."""
    return c.post("/api/terms", json={"name": ad}).json()["id"]


def _kucuk_okul(c: TestClient, ek: str = "") -> dict:
    d = c.post("/api/subjects", json={"name": f"Matematik{ek}", "short_code": "MAT"}).json()["id"]
    o = c.post("/api/teachers", json={"full_name": f"Ayşe Yılmaz{ek}"}).json()["id"]
    s = c.post("/api/sections", json={"name": f"5-A{ek}", "grade_level": 5}).json()["id"]
    c.post("/api/curriculum", json={
        "section_id": s, "subject_id": d, "teacher_id": o, "weekly_hours": 4,
    })
    return {"ders": d, "ogretmen": o, "sube": s}


# --- Dönem yaşam döngüsü ---

def test_kurulum_ilk_donemi_acar(yonetici: TestClient):
    donemler = yonetici.get("/api/terms").json()
    assert len(donemler) == 1
    assert donemler[0]["is_active"] is True
    # Varsayılan zaman ızgarası bu döneme bağlı gelir.
    assert donemler[0]["counts"]["ders_saati"] == 7


def test_yeni_donem_bos_baslar_ve_aktif_olur(yonetici: TestClient):
    _kucuk_okul(yonetici)
    assert len(yonetici.get("/api/teachers").json()) == 1

    yeni = yonetici.post("/api/terms", json={"name": "2027-2028 Güz"}).json()
    assert yeni["is_active"] is True
    assert yeni["counts"] == {
        "ogretmen": 0, "ders": 0, "sube": 0, "program": 0,
        "ders_saati": 7, "mufredat": 0,     # ızgara hazır gelir
    }

    for yol in ("/api/teachers", "/api/subjects", "/api/sections",
                "/api/curriculum", "/api/timetables"):
        assert yonetici.get(yol).json() == [], yol


def test_yeni_donem_kullanilabilir_izgarayla_gelir(yonetici: TestClient):
    """Izgara olmadan müsaitlik ve yerleştirme yapılamaz; hazır gelmeli."""
    yonetici.post("/api/terms", json={"name": "2027-2028 Güz"})

    izgara = yonetici.get("/api/timegrid").json()
    assert len(izgara) == 7
    aktif = [g for g in izgara if g["is_active"]]
    assert [g["name"] for g in aktif] == [
        "Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma",
    ]
    assert all(len(g["periods"]) == 8 for g in aktif)

    # Izgara düzenlenebilir durumda: gün kapatılıp ders saati eklenebilir.
    izgara[0]["periods"].append({
        "index": 8, "name": "9. ders", "start_time": None, "end_time": None,
        "is_break": False,
    })
    r = yonetici.put("/api/timegrid", json=izgara)
    assert r.status_code == 200
    assert len(r.json()[0]["periods"]) == 9


def test_donemler_arasi_gecis_veriyi_korur(yonetici: TestClient):
    ilk = yonetici.get("/api/terms").json()[0]["id"]
    _kucuk_okul(yonetici)

    ikinci = _donem_ac(yonetici, "İkinci Dönem")
    _kucuk_okul(yonetici, ek=" B")
    assert [t["full_name"] for t in yonetici.get("/api/teachers").json()] == ["Ayşe Yılmaz B"]

    yonetici.post(f"/api/terms/{ilk}/activate")
    assert [t["full_name"] for t in yonetici.get("/api/teachers").json()] == ["Ayşe Yılmaz"]

    yonetici.post(f"/api/terms/{ikinci}/activate")
    assert [t["full_name"] for t in yonetici.get("/api/teachers").json()] == ["Ayşe Yılmaz B"]


def test_ayni_sube_adi_farkli_donemlerde_kullanilabilir(yonetici: TestClient):
    yonetici.post("/api/sections", json={"name": "5-A"})
    assert yonetici.post("/api/sections", json={"name": "5-A"}).status_code == 409

    _donem_ac(yonetici, "İkinci Dönem")
    assert yonetici.post("/api/sections", json={"name": "5-A"}).status_code == 201


def test_baska_donemin_kaydina_erisilemez(yonetici: TestClient):
    v = _kucuk_okul(yonetici)
    _donem_ac(yonetici, "İkinci Dönem")

    assert yonetici.put(f"/api/teachers/{v['ogretmen']}", json={
        "full_name": "Kaçak", "is_active": True,
    }).status_code == 404
    assert yonetici.delete(f"/api/subjects/{v['ders']}").status_code == 404
    assert yonetici.get(f"/api/sections/{v['sube']}/availability").status_code == 404


def test_son_donem_silinemez(yonetici: TestClient):
    donem = yonetici.get("/api/terms").json()[0]["id"]
    r = yonetici.delete(f"/api/terms/{donem}")
    assert r.status_code == 409
    assert "Son dönem" in r.text


def test_donem_silinince_gizlenir_ve_geri_alinabilir(yonetici: TestClient):
    ilk = yonetici.get("/api/terms").json()[0]["id"]
    _kucuk_okul(yonetici)
    ikinci = _donem_ac(yonetici, "İkinci Dönem")

    kalan = yonetici.delete(f"/api/terms/{ikinci}").json()
    assert [t["id"] for t in kalan] == [ilk]
    assert kalan[0]["is_active"] is True          # aktif dönem ilkine döner

    silinmis = yonetici.get("/api/terms/deleted").json()
    assert [t["id"] for t in silinmis] == [ikinci]

    yonetici.post(f"/api/terms/{ikinci}/restore")
    assert {t["id"] for t in yonetici.get("/api/terms").json()} == {ilk, ikinci}


def test_silinen_donemin_verisi_durur(yonetici: TestClient):
    ilk = yonetici.get("/api/terms").json()[0]["id"]
    ikinci = _donem_ac(yonetici, "İkinci Dönem")
    _kucuk_okul(yonetici)

    yonetici.delete(f"/api/terms/{ikinci}")
    yonetici.post(f"/api/terms/{ikinci}/restore")
    yonetici.post(f"/api/terms/{ikinci}/activate")

    assert len(yonetici.get("/api/teachers").json()) == 1
    assert len(yonetici.get("/api/curriculum").json()) == 1
    assert ilk != ikinci


# --- Yumuşak silme ---

def test_silinen_ogretmen_listede_gorunmez_ama_yeniden_eklenebilir(yonetici: TestClient):
    o = yonetici.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    assert yonetici.delete(f"/api/teachers/{o}").status_code == 204
    assert yonetici.get("/api/teachers").json() == []

    # Yumuşak silme, aynı adın yeniden kullanılmasını engellemez.
    yeni = yonetici.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"})
    assert yeni.status_code == 201
    assert yeni.json()["id"] != o


def test_silinen_sube_adi_yeniden_kullanilabilir(yonetici: TestClient):
    s = yonetici.post("/api/sections", json={"name": "5-A"}).json()["id"]
    yonetici.delete(f"/api/sections/{s}")
    assert yonetici.post("/api/sections", json={"name": "5-A"}).status_code == 201


def test_mufredatta_kullanilan_ogretmen_silinemez(yonetici: TestClient):
    v = _kucuk_okul(yonetici)
    r = yonetici.delete(f"/api/teachers/{v['ogretmen']}")
    assert r.status_code == 409
    assert "müfredatta dersi var" in r.text


def test_sube_silinince_mufredati_da_gizlenir(yonetici: TestClient):
    v = _kucuk_okul(yonetici)
    assert len(yonetici.get("/api/curriculum").json()) == 1
    yonetici.delete(f"/api/sections/{v['sube']}")
    assert yonetici.get("/api/curriculum").json() == []
    # Öğretmen artık kullanılmadığı için silinebilir hale gelir.
    assert yonetici.delete(f"/api/teachers/{v['ogretmen']}").status_code == 204


def test_silinen_program_listeden_kalkar_ve_yayindan_duser(yonetici: TestClient):
    _kucuk_okul(yonetici)
    pid = yonetici.post("/api/timetables", json={"name": "Deneme"}).json()["id"]
    yonetici.post(f"/api/timetables/{pid}/solve?time_limit_seconds=20")
    jeton = yonetici.post(f"/api/timetables/{pid}/publish").json()["public_token"]

    yonetici.delete(f"/api/timetables/{pid}")
    assert yonetici.get("/api/timetables").json() == []
    assert yonetici.get(f"/api/timetables/{pid}/grid").status_code == 404
    assert yonetici.get(f"/api/public/timetables/{jeton}").status_code == 404


# --- Geçmiş dönemden aktarma ---

def test_ogretmenler_gecmis_donemden_aktarilir(yonetici: TestClient):
    eski = yonetici.get("/api/terms").json()[0]["id"]
    for ad in ("Ayşe Yılmaz", "Mehmet Kaya", "Zeynep Demir"):
        yonetici.post("/api/teachers", json={"full_name": ad, "branch": "Matematik"})

    _donem_ac(yonetici, "Yeni Dönem")
    adaylar = yonetici.get(f"/api/teachers/import/{eski}").json()
    assert len(adaylar) == 3

    secilen = [a["id"] for a in adaylar if a["full_name"] != "Zeynep Demir"]
    r = yonetici.post("/api/teachers/import",
                      json={"term_id": eski, "ids": secilen}).json()
    assert r["imported"] == 2
    assert r["skipped"] == []

    yeni = yonetici.get("/api/teachers").json()
    assert {t["full_name"] for t in yeni} == {"Ayşe Yılmaz", "Mehmet Kaya"}
    assert all(t["branch"] == "Matematik" for t in yeni)      # alanlar korunur
    assert {t["id"] for t in yeni} & {a["id"] for a in adaylar} == set()  # yeni kayıtlar


def test_aktarim_ayni_adi_atlar(yonetici: TestClient):
    eski = yonetici.get("/api/terms").json()[0]["id"]
    yonetici.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"})
    kaynak = yonetici.get("/api/teachers").json()[0]["id"]

    _donem_ac(yonetici, "Yeni Dönem")
    yonetici.post("/api/teachers", json={"full_name": "ayşe yılmaz"})
    r = yonetici.post("/api/teachers/import",
                      json={"term_id": eski, "ids": [kaynak]}).json()
    assert r["imported"] == 0
    assert "zaten var" in r["skipped"][0]


def test_zaman_izgarasi_aktarilir(yonetici: TestClient):
    eski = yonetici.get("/api/terms").json()[0]["id"]
    # Kaynak dönemde ızgarayı özelleştir: cuma kapalı.
    kaynak_izgara = yonetici.get("/api/timegrid").json()
    kaynak_izgara[4]["is_active"] = False
    yonetici.put("/api/timegrid", json=kaynak_izgara)

    _donem_ac(yonetici, "Yeni Dönem")
    assert len([g for g in yonetici.get("/api/timegrid").json() if g["is_active"]]) == 5

    yonetici.post(f"/api/timegrid/import/{eski}")
    assert len([g for g in yonetici.get("/api/timegrid").json() if g["is_active"]]) == 4
    yeni = yonetici.get("/api/timegrid").json()
    assert len(yeni) == 7
    assert len(yeni[0]["periods"]) == 8


def test_mufredat_aktarimi_adlara_gore_eslesir(yonetici: TestClient):
    eski = yonetici.get("/api/terms").json()[0]["id"]
    _kucuk_okul(yonetici)
    kaynak_mufredat = yonetici.get("/api/curriculum").json()

    _donem_ac(yonetici, "Yeni Dönem")
    # Karşılıkları henüz yok: satır atlanır.
    r = yonetici.post("/api/curriculum/import", json={
        "term_id": eski, "ids": [m["id"] for m in kaynak_mufredat],
    }).json()
    assert r["imported"] == 0
    assert "tanımlı değil" in r["skipped"][0]

    # Tanımlar aktarılınca müfredat da yerine oturur.
    for tur in ("teachers", "subjects", "sections"):
        adaylar = yonetici.get(f"/api/{tur}/import/{eski}").json()
        yonetici.post(f"/api/{tur}/import",
                      json={"term_id": eski, "ids": [a["id"] for a in adaylar]})

    r = yonetici.post("/api/curriculum/import", json={
        "term_id": eski, "ids": [m["id"] for m in kaynak_mufredat],
    }).json()
    assert r["imported"] == 1

    yeni = yonetici.get("/api/curriculum").json()
    assert yeni[0]["weekly_hours"] == 4
    assert yeni[0]["subject"]["name"] == "Matematik"
    assert yeni[0]["teacher"]["full_name"] == "Ayşe Yılmaz"


def test_kendi_doneminden_aktarim_reddedilir(yonetici: TestClient):
    donem = yonetici.get("/api/terms").json()[0]["id"]
    o = yonetici.post("/api/teachers", json={"full_name": "Ayşe"}).json()["id"]
    assert yonetici.get(f"/api/teachers/import/{donem}").status_code == 422
    assert yonetici.post("/api/teachers/import",
                         json={"term_id": donem, "ids": [o]}).status_code == 422


def test_program_uretimi_yalnizca_kendi_donemini_gorur(yonetici: TestClient):
    _kucuk_okul(yonetici)
    _donem_ac(yonetici, "Yeni Dönem")

    pid = yonetici.post("/api/timetables", json={"name": "Boş Dönem"}).json()["id"]
    deneme = yonetici.post(f"/api/timetables/{pid}/solve?time_limit_seconds=15").json()
    assert deneme["status"] == "hata"
    # Izgara hazır gelir; eksik olan tanımlardır.
    kodlar = {b["kod"] for b in deneme["report"]["bulgular"]}
    assert kodlar == {"mufredat_bos"}
