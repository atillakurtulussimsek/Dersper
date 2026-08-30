"""Elle düzenleme: taşıma, yer değiştirme, ızgaradan alma, geri alma.

Kurulum küçük ve elle kontrol edilebilir tutuldu: bir gün, birkaç saat, iki
şube. Çözücüyü çalıştırmak yerine yerleşimler doğrudan yazılır, böylece hangi
hücrenin nerede olduğu kesin bilinir.
"""
from fastapi.testclient import TestClient


def _okul(c: TestClient, gun_sayisi: int = 2, ders_sayisi: int = 6) -> dict:
    """Sade bir ızgara ve iki şube kurar, ders atamalarını döner."""
    gunler = c.get("/api/timegrid").json()
    yeni = []
    for i, g in enumerate(gunler[:gun_sayisi]):
        yeni.append({
            "index": g["index"], "name": g["name"], "is_active": True,
            "periods": [
                {"id": p["id"], "index": p["index"], "name": p["name"],
                 "start_time": None, "end_time": None,
                 "is_break": False, "is_lunch": False}
                for p in sorted(g["periods"], key=lambda x: x["index"])[:ders_sayisi]
            ],
        })
    assert c.put("/api/timegrid", json=yeni).status_code == 200

    mat = c.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    trk = c.post("/api/subjects", json={"name": "Türkçe"}).json()["id"]
    ayse = c.post("/api/teachers", json={"full_name": "Ayşe Yılmaz"}).json()["id"]
    mehmet = c.post("/api/teachers", json={"full_name": "Mehmet Demir"}).json()["id"]
    a_sube = c.post("/api/sections", json={"name": "9-A"}).json()["id"]
    b_sube = c.post("/api/sections", json={"name": "9-B"}).json()["id"]

    atamalar = {
        "a_mat": c.post("/api/curriculum", json={
            "section_id": a_sube, "subject_id": mat, "teacher_id": ayse,
            "weekly_hours": 2, "block_pattern": "2", "max_per_day": 2}).json()["id"],
        "a_trk": c.post("/api/curriculum", json={
            "section_id": a_sube, "subject_id": trk, "teacher_id": mehmet,
            "weekly_hours": 2, "block_pattern": "2", "max_per_day": 2}).json()["id"],
        "b_mat": c.post("/api/curriculum", json={
            "section_id": b_sube, "subject_id": mat, "teacher_id": ayse,
            "weekly_hours": 1, "block_pattern": "1", "max_per_day": 1}).json()["id"],
    }
    saatler = [p for g in c.get("/api/timegrid").json() if g["is_active"]
               for p in sorted(g["periods"], key=lambda x: x["index"])]
    return {"atamalar": atamalar, "saatler": saatler, "ogretmenler": {"ayse": ayse},
            "subeler": {"a": a_sube, "b": b_sube}}


def _program(c: TestClient, okul: dict, yerlesim: list[tuple[str, int]]) -> int:
    """Program oluşturur ve verilen (ders, saat sırası) yerleşimlerini koyar."""
    pid = c.post("/api/timetables", json={"name": "Elle"}).json()["id"]
    for ad, sira in yerlesim:
        r = c.post(f"/api/timetables/{pid}/place", json={
            "curriculum_entry_id": okul["atamalar"][ad],
            "period_id": okul["saatler"][sira]["id"],
            "uzunluk": 1 if ad == "b_mat" else 2,
        })
        assert r.status_code == 200, r.text
    return pid


def _hucreler(c: TestClient, pid: int) -> list[dict]:
    return c.get(f"/api/timetables/{pid}/grid").json()["cells"]


def _konum(c: TestClient, pid: int, ders: str) -> list[int]:
    """Bir dersin yerleştiği ders saati kimlikleri, sıralı."""
    ad = {"a_mat": ("9-A", "Matematik"), "a_trk": ("9-A", "Türkçe"),
          "b_mat": ("9-B", "Matematik")}[ders]
    return sorted(h["period_id"] for h in _hucreler(c, pid)
                  if (h["section_name"], h["subject_name"]) == ad)


# --- Blok bütün taşınır ---

def test_blok_butun_tasinir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])       # 0-1. saatler
    hucre = _hucreler(yonetici, pid)[0]

    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": okul["saatler"][3]["id"]})
    assert r.status_code == 200, r.text
    assert _konum(yonetici, pid, "a_mat") == [
        okul["saatler"][3]["id"], okul["saatler"][4]["id"]
    ]


def test_blok_gun_sonuna_sigmazsa_reddedilir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]

    # 2 saatlik blok günün son saatine (5) konamaz.
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": okul["saatler"][5]["id"]})
    assert r.status_code == 422
    assert "sığmıyor" in r.text


# --- Yer değiştirme ---

def test_esit_bloklar_yer_degistirir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0), ("a_trk", 2)])
    mat_once = _konum(yonetici, pid, "a_mat")
    trk_once = _konum(yonetici, pid, "a_trk")

    mat_hucre = next(h for h in _hucreler(yonetici, pid)
                     if h["subject_name"] == "Matematik")
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{mat_hucre['assignment_id']}",
                       json={"period_id": trk_once[0]})
    assert r.status_code == 200, r.text
    assert _konum(yonetici, pid, "a_mat") == trk_once
    assert _konum(yonetici, pid, "a_trk") == mat_once


def test_farkli_uzunlukta_bloklar_yer_degistirmez(yonetici: TestClient):
    okul = _okul(yonetici)
    # 9-A Matematik 2 saat (0-1), 9-B Matematik 1 saat (2) — öğretmen aynı.
    pid = _program(yonetici, okul, [("a_mat", 0), ("b_mat", 2)])
    mat = next(h for h in _hucreler(yonetici, pid) if h["section_name"] == "9-A")

    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{mat['assignment_id']}",
                       json={"period_id": okul["saatler"][2]["id"]})
    assert r.status_code == 409
    assert "eşit uzunlukta" in r.text


def test_yer_degistirme_karsi_tarafi_da_denetler(yonetici: TestClient):
    """Karşı ders taşınan bloğun yerine konamıyorsa değişim yapılmaz."""
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0), ("a_trk", 2)])
    # Türkçe öğretmenini 9-A Matematik'in bulunduğu saatlere kapat.
    trk_ogretmen = next(h["teacher_id"] for h in _hucreler(yonetici, pid)
                        if h["subject_name"] == "Türkçe")
    yonetici.put(f"/api/teachers/{trk_ogretmen}/availability", json={
        "cells": [{"period_id": okul["saatler"][0]["id"], "state": "uygun_degil"}]
    })

    mat = next(h for h in _hucreler(yonetici, pid) if h["subject_name"] == "Matematik")
    trk_yeri = _konum(yonetici, pid, "a_trk")
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{mat['assignment_id']}",
                       json={"period_id": trk_yeri[0]})
    assert r.status_code == 409
    assert "Yer değiştirilemiyor" in r.text
    # Hiçbir şey kıpırdamamalı.
    assert _konum(yonetici, pid, "a_trk") == trk_yeri


# --- Müsaitlik ve kilit denetimleri ---

def test_musait_olmayan_saate_elle_konamaz(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    yonetici.put(f"/api/teachers/{okul['ogretmenler']['ayse']}/availability", json={
        "cells": [{"period_id": okul["saatler"][3]["id"], "state": "uygun_degil"},
                  {"period_id": okul["saatler"][4]["id"], "state": "uygun_degil"}]
    })
    hucre = _hucreler(yonetici, pid)[0]
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": okul["saatler"][3]["id"]})
    assert r.status_code == 409
    assert "müsait değil" in r.text


def test_kapali_subeye_elle_konamaz(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    yonetici.put(f"/api/sections/{okul['subeler']['a']}/availability", json={
        "cells": [{"period_id": okul["saatler"][3]["id"], "state": "uygun_degil"}]
    })
    hucre = _hucreler(yonetici, pid)[0]
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": okul["saatler"][3]["id"]})
    assert r.status_code == 409
    assert "kapalı" in r.text


def test_kilitli_ders_tasinmaz(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.post(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/lock")

    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": okul["saatler"][3]["id"]})
    assert r.status_code == 409
    assert "Kilitli" in r.text


def test_baska_donemin_saatine_tasinmaz(yonetici: TestClient):
    """Kurum yalıtımı: hedef ders saati aktif döneme ait olmalı."""
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]

    ilk_donem = next(d["id"] for d in yonetici.get("/api/terms").json() if d["is_active"])
    yeni_donem = yonetici.post("/api/terms", json={"name": "Öteki"}).json()["id"]
    yonetici.post(f"/api/terms/{yeni_donem}/activate")
    yabanci = yonetici.get("/api/timegrid").json()[0]["periods"][0]["id"]
    yonetici.post(f"/api/terms/{ilk_donem}/activate")

    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                       json={"period_id": yabanci})
    assert r.status_code == 404


# --- Izgaradan alma ve geri koyma ---

def test_izgaradan_alinan_ders_bekleyenlere_duser(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]

    r = yonetici.post(
        f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/unplace")
    assert r.status_code == 200, r.text
    assert _konum(yonetici, pid, "a_mat") == []

    bekleyen = yonetici.get(f"/api/timetables/{pid}/pending").json()
    mat = [b for b in bekleyen if b["section_name"] == "9-A"
           and b["subject_name"] == "Matematik"]
    assert [b["uzunluk"] for b in mat] == [2]


def test_bekleyen_blok_geri_konur(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.post(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/unplace")

    r = yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": okul["atamalar"]["a_mat"],
        "period_id": okul["saatler"][3]["id"],
        "uzunluk": 2,
    })
    assert r.status_code == 200, r.text
    assert _konum(yonetici, pid, "a_mat") == [
        okul["saatler"][3]["id"], okul["saatler"][4]["id"]
    ]
    assert not [b for b in yonetici.get(f"/api/timetables/{pid}/pending").json()
                if b["section_name"] == "9-A" and b["subject_name"] == "Matematik"]


def test_bekleyende_olmayan_blok_konamaz(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    r = yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": okul["atamalar"]["a_mat"],
        "period_id": okul["saatler"][3]["id"],
        "uzunluk": 2,
    })
    assert r.status_code == 409
    assert "bekleyen blok yok" in r.text


def test_kilitli_ders_izgaradan_alinmaz(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.post(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/lock")
    r = yonetici.post(
        f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/unplace")
    assert r.status_code == 409


# --- Hedef değerlendirme ---

def test_hedefler_gecerli_yerleri_isaretler(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0), ("a_trk", 2)])
    mat = next(h for h in _hucreler(yonetici, pid) if h["subject_name"] == "Matematik")

    hedefler = yonetici.get(
        f"/api/timetables/{pid}/targets?assignment_id={mat['assignment_id']}").json()
    esles = {h["period_id"]: h for h in hedefler}

    # Kendi yeri uygun (bloğun kendisi yok sayılır).
    assert esles[okul["saatler"][0]["id"]]["uygun"] is True
    # Günün son saati: 2 saatlik blok sığmaz.
    assert esles[okul["saatler"][5]["id"]]["uygun"] is False
    assert "sığmıyor" in esles[okul["saatler"][5]["id"]]["neden"]
    # Türkçe'nin durduğu yer dolu ama aynı şube — neden yazılmalı.
    assert esles[okul["saatler"][2]["id"]]["uygun"] is False
    assert "9-A" in esles[okul["saatler"][2]["id"]]["neden"]


def test_hedefler_bekleyen_blok_icin_de_sorulur(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [])
    hedefler = yonetici.get(
        f"/api/timetables/{pid}/targets"
        f"?curriculum_entry_id={okul['atamalar']['a_mat']}&uzunluk=2").json()
    assert sum(1 for h in hedefler if h["uygun"]) > 0


# --- Geri alma ---

def test_tasima_geri_alinir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    once = _konum(yonetici, pid, "a_mat")
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                   json={"period_id": okul["saatler"][3]["id"]})
    assert _konum(yonetici, pid, "a_mat") != once

    r = yonetici.post(f"/api/timetables/{pid}/undo")
    assert r.status_code == 200, r.text
    assert _konum(yonetici, pid, "a_mat") == once
    assert r.json()["can_redo"] is True

    yonetici.post(f"/api/timetables/{pid}/redo")
    assert _konum(yonetici, pid, "a_mat") == [
        okul["saatler"][3]["id"], okul["saatler"][4]["id"]
    ]


def test_izgaradan_alma_geri_alinir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    once = _konum(yonetici, pid, "a_mat")
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.post(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}/unplace")
    assert _konum(yonetici, pid, "a_mat") == []

    yonetici.post(f"/api/timetables/{pid}/undo")
    assert _konum(yonetici, pid, "a_mat") == once


def test_yer_degistirme_geri_alinir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0), ("a_trk", 2)])
    mat_once, trk_once = _konum(yonetici, pid, "a_mat"), _konum(yonetici, pid, "a_trk")
    mat = next(h for h in _hucreler(yonetici, pid) if h["subject_name"] == "Matematik")
    yonetici.patch(f"/api/timetables/{pid}/assignments/{mat['assignment_id']}",
                   json={"period_id": trk_once[0]})

    yonetici.post(f"/api/timetables/{pid}/undo")
    assert _konum(yonetici, pid, "a_mat") == mat_once
    assert _konum(yonetici, pid, "a_trk") == trk_once


def test_geri_alinacak_sey_yoksa_reddedilir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = yonetici.post("/api/timetables", json={"name": "Boş"}).json()["id"]
    assert yonetici.post(f"/api/timetables/{pid}/undo").status_code == 409
    assert yonetici.post(f"/api/timetables/{pid}/redo").status_code == 409
    assert okul  # kurulum kullanıldı


def test_yeni_degisiklik_ileri_almayi_koparir(yonetici: TestClient):
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0)])
    hucre = _hucreler(yonetici, pid)[0]
    yonetici.patch(f"/api/timetables/{pid}/assignments/{hucre['assignment_id']}",
                   json={"period_id": okul["saatler"][3]["id"]})
    yonetici.post(f"/api/timetables/{pid}/undo")

    yeni = _hucreler(yonetici, pid)[0]
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{yeni['assignment_id']}",
                       json={"period_id": okul["saatler"][2]["id"]})
    assert r.json()["can_redo"] is False
    assert yonetici.post(f"/api/timetables/{pid}/redo").status_code == 409


def test_baska_subenin_dersi_yer_degistirmeyi_engellemez(yonetici: TestClient):
    """Ders saati okulun tamamına ait: aynı saatte başka şubelerin dersleri
    olması, iki dersin yer değiştirmesine engel değildir."""
    okul = _okul(yonetici)
    pid = _program(yonetici, okul, [("a_mat", 0), ("a_trk", 2), ("b_mat", 4)])
    mat_once = _konum(yonetici, pid, "a_mat")
    trk_once = _konum(yonetici, pid, "a_trk")
    b_once = _konum(yonetici, pid, "b_mat")

    mat = next(h for h in _hucreler(yonetici, pid)
               if h["section_name"] == "9-A" and h["subject_name"] == "Matematik")
    r = yonetici.patch(f"/api/timetables/{pid}/assignments/{mat['assignment_id']}",
                       json={"period_id": trk_once[0]})
    assert r.status_code == 200, r.text
    assert _konum(yonetici, pid, "a_mat") == trk_once
    assert _konum(yonetici, pid, "a_trk") == mat_once
    # Karışmayan şube yerinde kalır.
    assert _konum(yonetici, pid, "b_mat") == b_once
