"""Çok kurumluluk: kayıt, kurum yalıtımı ve kullanıcı yönetimi."""
import pytest
from fastapi.testclient import TestClient


# --- Kayıt ---

def test_ilk_kayit_kurum_kullanici_ve_donem_olusturur(istemci: TestClient):
    durum = istemci.get("/api/auth/status").json()
    assert durum == {"has_institutions": False, "registration_open": True}

    r = istemci.post("/api/auth/register", json={
        "institution_name": "Atatürk Ortaokulu", "institution_type": "k12",
        "full_name": "Atilla Şimşek", "email": "a@ornek.com", "password": "parola1234",
    })
    assert r.status_code == 201
    istemci.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    assert istemci.get("/api/institution").json()["name"] == "Atatürk Ortaokulu"
    donemler = istemci.get("/api/terms").json()
    assert len(donemler) == 1 and donemler[0]["is_active"] is True
    # Yeni kurum kullanılabilir bir ızgarayla gelir.
    assert donemler[0]["counts"]["ders_saati"] == 7
    assert istemci.get("/api/auth/status").json()["has_institutions"] is True


def test_ikinci_kurum_kendi_verisiyle_acilir(yonetici: TestClient, ikinci_kurum: TestClient):
    yonetici.post("/api/teachers", json={"full_name": "Birinci Kurum Öğretmeni"})
    ikinci_kurum.post("/api/teachers", json={"full_name": "İkinci Kurum Öğretmeni"})

    assert [t["full_name"] for t in yonetici.get("/api/teachers").json()] == [
        "Birinci Kurum Öğretmeni"
    ]
    assert [t["full_name"] for t in ikinci_kurum.get("/api/teachers").json()] == [
        "İkinci Kurum Öğretmeni"
    ]
    assert (yonetici.get("/api/institution").json()["id"]
            != ikinci_kurum.get("/api/institution").json()["id"])


def test_kayit_env_ile_kapatilabilir(istemci: TestClient, monkeypatch):
    """Kapalıyken bile sistemde hiç kurum yoksa ilk kayda izin verilir."""
    from app.config import settings

    monkeypatch.setattr(settings, "allow_registration", False)
    assert istemci.get("/api/auth/status").json() == {
        "has_institutions": False, "registration_open": True,
    }
    ilk = istemci.post("/api/auth/register", json={
        "institution_name": "Tek Kurum", "institution_type": "k12",
        "full_name": "Yönetici", "email": "ilk@ornek.com", "password": "parola1234",
    })
    assert ilk.status_code == 201

    # Kurum oluştuktan sonra kayıt kapanır.
    assert istemci.get("/api/auth/status").json()["registration_open"] is False
    ikinci = istemci.post("/api/auth/register", json={
        "institution_name": "İkinci Kurum", "institution_type": "k12",
        "full_name": "Başkası", "email": "ikinci@ornek.com", "password": "parola1234",
    })
    assert ikinci.status_code == 403
    assert "kaydı kapalı" in ikinci.text


# --- Kurum yalıtımı ---

def _kucuk_okul(c: TestClient) -> dict:
    d = c.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    o = c.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    s = c.post("/api/sections", json={"name": "5-A"}).json()["id"]
    e = c.post("/api/curriculum", json={
        "section_id": s, "subject_id": d, "teacher_id": o, "weekly_hours": 4,
    }).json()["id"]
    return {"ders": d, "ogretmen": o, "sube": s, "atama": e}


@pytest.mark.parametrize("yol,yontem", [
    ("/api/teachers/{ogretmen}", "put"),
    ("/api/subjects/{ders}", "delete"),
    ("/api/sections/{sube}", "delete"),
    ("/api/sections/{sube}/availability", "get"),
    ("/api/curriculum/{atama}", "delete"),
])
def test_baska_kurumun_kaydina_erisilemez(
    yonetici: TestClient, ikinci_kurum: TestClient, yol: str, yontem: str
):
    v = _kucuk_okul(yonetici)
    adres = yol.format(**v)
    govde = {"full_name": "Kaçak", "is_active": True}
    r = getattr(ikinci_kurum, yontem)(
        adres, **({"json": govde} if yontem == "put" else {})
    )
    assert r.status_code == 404, f"{yontem.upper()} {adres} → {r.status_code}"


def test_baska_kurumun_donemi_okunamaz(yonetici: TestClient, ikinci_kurum: TestClient):
    donem = yonetici.get("/api/terms").json()[0]["id"]

    assert ikinci_kurum.post(f"/api/terms/{donem}/activate").status_code == 404
    assert ikinci_kurum.delete(f"/api/terms/{donem}").status_code == 404
    # Aktarım uçları da başka kurumun dönemini görmez.
    assert ikinci_kurum.get(f"/api/teachers/import/{donem}").status_code == 404
    assert ikinci_kurum.get(f"/api/timegrid/import/{donem}").status_code == 404
    assert ikinci_kurum.post("/api/teachers/import", json={
        "term_id": donem, "ids": [1],
    }).status_code == 404


def test_baska_kurumun_programi_okunamaz(yonetici: TestClient, ikinci_kurum: TestClient):
    _kucuk_okul(yonetici)
    pid = yonetici.post("/api/timetables", json={"name": "Gizli"}).json()["id"]

    assert ikinci_kurum.get("/api/timetables").json() == []
    assert ikinci_kurum.get(f"/api/timetables/{pid}/grid").status_code == 404
    assert ikinci_kurum.delete(f"/api/timetables/{pid}").status_code == 404
    assert ikinci_kurum.get(f"/api/timetables/{pid}/export/html").status_code == 404


def test_yapay_zeka_ayari_kuruma_ozel(yonetici: TestClient, ikinci_kurum: TestClient):
    yonetici.put("/api/ai/settings", json={
        "enabled": True, "base_url": "http://bir.local/v1",
        "model": "model-bir", "api_key": "sk-bir",
    })
    assert yonetici.get("/api/ai/settings").json()["model"] == "model-bir"
    # İkinci kurum kendi boş ayarını görür.
    diger = ikinci_kurum.get("/api/ai/settings").json()
    assert diger["has_api_key"] is False
    assert diger["base_url"] is None


def test_yayin_kurumu_jetondan_cikarilir(yonetici: TestClient):
    _kucuk_okul(yonetici)
    pid = yonetici.post("/api/timetables", json={"name": "Yayın"}).json()["id"]
    yonetici.post(f"/api/timetables/{pid}/solve?time_limit_seconds=20")
    jeton = yonetici.post(f"/api/timetables/{pid}/publish").json()["public_token"]

    yonetici.headers.pop("Authorization")
    kurum = yonetici.get(f"/api/public/timetables/{jeton}/institution").json()
    assert kurum["name"] == "Test Ortaokulu"
    izgara = yonetici.get(f"/api/public/timetables/{jeton}/timegrid").json()
    assert [g["name"] for g in izgara if g["is_active"]][0] == "Pazartesi"


# --- Kullanıcı yönetimi ---

def test_kuruma_kullanici_eklenir(yonetici: TestClient):
    assert len(yonetici.get("/api/users").json()) == 1

    r = yonetici.post("/api/users", json={
        "full_name": "Yeni Kullanıcı", "email": "yeni@ornek.com",
        "password": "parola1234",
    })
    assert r.status_code == 201
    assert len(yonetici.get("/api/users").json()) == 2

    # Yeni kullanıcı giriş yapıp aynı kurumu görür.
    jeton = yonetici.post("/api/auth/login", json={
        "email": "yeni@ornek.com", "password": "parola1234",
    }).json()["access_token"]
    yonetici.headers["Authorization"] = f"Bearer {jeton}"
    assert yonetici.get("/api/institution").json()["name"] == "Test Ortaokulu"


def test_eposta_sistem_genelinde_essiz(yonetici: TestClient, ikinci_kurum: TestClient):
    r = ikinci_kurum.post("/api/users", json={
        "full_name": "Çakışan", "email": "yonetici@ornek.com", "password": "parola1234",
    })
    assert r.status_code == 409
    assert "bir kuruma" in r.text


def test_baska_kurumun_kullanicisi_gorunmez(
    yonetici: TestClient, ikinci_kurum: TestClient
):
    yonetici.post("/api/users", json={
        "full_name": "Birinci Kurum Üyesi", "email": "uye1@ornek.com",
        "password": "parola1234",
    })
    adlar = [u["full_name"] for u in ikinci_kurum.get("/api/users").json()]
    assert adlar == ["Diğer Yönetici"]

    hedef = yonetici.get("/api/users").json()[0]["id"]
    assert ikinci_kurum.put(f"/api/users/{hedef}", json={
        "full_name": "Ele geçirildi", "is_active": True,
    }).status_code == 404


def test_kullanici_kapatilabilir_ama_kendini_kapatamaz(yonetici: TestClient):
    ben = yonetici.get("/api/auth/me").json()["id"]
    assert yonetici.put(f"/api/users/{ben}", json={
        "full_name": "Test Yönetici", "is_active": False,
    }).status_code == 409

    baskasi = yonetici.post("/api/users", json={
        "full_name": "Geçici", "email": "gecici@ornek.com", "password": "parola1234",
    }).json()["id"]
    assert yonetici.put(f"/api/users/{baskasi}", json={
        "full_name": "Geçici", "is_active": False,
    }).status_code == 200

    # Kapatılan hesapla giriş yapılamaz.
    r = yonetici.post("/api/auth/login", json={
        "email": "gecici@ornek.com", "password": "parola1234",
    })
    assert r.status_code == 403


def test_parola_degistirilebilir(yonetici: TestClient):
    uid = yonetici.post("/api/users", json={
        "full_name": "Parola Testi", "email": "parola@ornek.com",
        "password": "eskiparola1",
    }).json()["id"]
    yonetici.put(f"/api/users/{uid}", json={
        "full_name": "Parola Testi", "is_active": True, "password": "yeniparola1",
    })
    assert yonetici.post("/api/auth/login", json={
        "email": "parola@ornek.com", "password": "eskiparola1",
    }).status_code == 401
    assert yonetici.post("/api/auth/login", json={
        "email": "parola@ornek.com", "password": "yeniparola1",
    }).status_code == 200
