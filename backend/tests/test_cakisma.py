"""Çakışma ölçütü: ızgaranın satırı mı, gerçek saat aralığı mı?

Kurum seçer (bkz. `app.cakisma`, `Term.conflict_basis`). Varsayılan eski
davranıştır: satır esastır. "saat" seçildiğinde, saatleri üst üste binen ayrı
satırlar da çakışma sayılır.
"""
from fastapi.testclient import TestClient

from app.cakisma import DERS_SAATI, SAAT, Aralik, dakikaya, gruplar, ortusenler
from app.solver.engine import Slot, SolveInput, solve
from tests.conftest import uret_ve_bekle
from tests.test_engine import ders


# --- Ölçütün kendisi ---

def test_ders_saati_olcutunde_her_satir_kendi_grubudur():
    a = [Aralik(0, 540, 580), Aralik(0, 560, 600)]
    assert gruplar(a, DERS_SAATI) == [[0], [1]]


def test_saat_olcutunde_ortusen_satirlar_birlesir():
    # 09:00-09:40 ile 09:20-10:00 kesişir; 10:10-10:50 ayrıdır.
    a = [Aralik(0, 540, 580), Aralik(0, 560, 600), Aralik(0, 610, 650)]
    assert gruplar(a, SAAT) == [[0, 1], [2]]


def test_bitisik_satirlar_cakismaz():
    """09:00-09:40 ile 09:40-10:20 uç uçadır, üst üste değil."""
    a = [Aralik(0, 540, 580), Aralik(0, 580, 620)]
    assert gruplar(a, SAAT) == [[0], [1]]


def test_farkli_gunler_hicbir_zaman_birlesmez():
    a = [Aralik(0, 540, 580), Aralik(1, 540, 580)]
    assert gruplar(a, SAAT) == [[0], [1]]


def test_saati_girilmemis_satir_yalnizca_kendisiyle_cakisir():
    """Bilinmeyen aralık hakkında bir şey söylenemez; satır kimliğine düşülür."""
    a = [Aralik(0), Aralik(0, 540, 580), Aralik(0, 560, 600)]
    assert gruplar(a, SAAT) == [[0], [1, 2]]


def test_kapsanan_klikler_atilir():
    """Yalnız başlayıp sonra kesişen aralık iki kez kısıtlanmamalı."""
    a = [Aralik(0, 540, 600), Aralik(0, 550, 570), Aralik(0, 560, 620)]
    assert gruplar(a, SAAT) == [[0, 1, 2]]


def test_ortusenler_haritasi_kendini_de_icerir():
    a = [Aralik(0, 540, 580), Aralik(0, 560, 600), Aralik(0, 610, 650)]
    assert ortusenler([7, 8, 9], a, SAAT) == {7: {7, 8}, 8: {7, 8}, 9: {9}}


def test_dakikaya_bos_saati_gecirir():
    from datetime import time

    assert dakikaya(None) is None
    assert dakikaya(time(9, 20)) == 560


# --- Uçtan uca ---

def _olcutu_ayarla(c: TestClient, olcut: str) -> None:
    donem = next(d for d in c.get("/api/terms").json() if d["is_active"])
    r = c.put(f"/api/terms/{donem['id']}", json={
        "name": donem["name"], "conflict_basis": olcut,
    })
    assert r.status_code == 200, r.text


def _ortusen_izgarali_okul(c: TestClient) -> int:
    """Tek gün, saatleri üst üste binen iki ders saati, iki şubeye giren tek
    öğretmen. Satır ölçütünde ikisi de aynı güne sığar, saat ölçütünde sığmaz.
    """
    gunler = c.get("/api/timegrid").json()
    g = gunler[0]
    saatler = sorted(g["periods"], key=lambda x: x["index"])[:2]
    c.put("/api/timegrid", json=[{
        "index": g["index"], "name": g["name"], "is_active": True,
        "periods": [
            {"id": saatler[0]["id"], "index": saatler[0]["index"], "name": "1. ders",
             "start_time": "09:00:00", "end_time": "09:40:00",
             "is_break": False, "is_lunch": False},
            {"id": saatler[1]["id"], "index": saatler[1]["index"], "name": "2. ders",
             "start_time": "09:20:00", "end_time": "10:00:00",
             "is_break": False, "is_lunch": False},
        ],
    }])

    ders = c.post("/api/subjects", json={"name": "Matematik"}).json()["id"]
    ogr = c.post("/api/teachers", json={"full_name": "Tek Öğretmen"}).json()["id"]
    for ad in ("9-A", "9-B"):
        sube = c.post("/api/sections", json={"name": ad}).json()["id"]
        c.post("/api/curriculum", json={
            "section_id": sube, "subject_id": ders, "teacher_id": ogr,
            "weekly_hours": 1, "block_pattern": "1", "max_per_day": 1,
        })
    return c.post("/api/timetables", json={"name": "Deneme"}).json()["id"]


def test_varsayilan_olcut_satirdir(yonetici: TestClient):
    donem = next(d for d in yonetici.get("/api/terms").json() if d["is_active"])
    assert donem["conflict_basis"] == DERS_SAATI


def _kesisen_slotlar() -> list[Slot]:
    """Tek gün, saatleri kesişen iki ders saati: 09:00-09:40 ve 09:20-10:00."""
    return [
        Slot(period_id=1, day_index=0, period_index=0, day_name="Pazartesi",
             period_name="1. ders", baslangic=540, bitis=580),
        Slot(period_id=2, day_index=0, period_index=1, day_name="Pazartesi",
             period_name="2. ders", baslangic=560, bitis=600),
    ]


def _tek_ogretmen_iki_sube() -> list:
    return [ders(1, 1, 10, "Matematik", 1), ders(2, 2, 10, "Matematik", 1)]


def test_cozucu_satir_olcutunde_kesisen_saatlere_yerlestirir():
    """Eski davranış: satırlar ayrı olduğu için öğretmen ikisine de girer."""
    sonuc = solve(SolveInput(
        slots=_kesisen_slotlar(), lessons=_tek_ogretmen_iki_sube(),
        time_limit_seconds=5,
    ))
    assert sonuc.ok
    assert len(sonuc.placements) == 2


def test_cozucu_saat_olcutunde_kesisen_saatlere_yerlestirmez():
    """Aynı veri, ölçüt saat: tek öğretmen iki kesişen aralıkta olamaz."""
    sonuc = solve(SolveInput(
        slots=_kesisen_slotlar(), lessons=_tek_ogretmen_iki_sube(),
        time_limit_seconds=5, cakisma_olcutu=SAAT,
    ))
    assert not sonuc.ok
    assert sonuc.proven_infeasible
    # Gevşek model yine de birini yerleştirip ötekini raporlar.
    assert sum(sonuc.unplaced.values()) == 1


def test_saat_olcutu_ayni_dersin_iki_blogunu_da_ayirir():
    """Kaynağın tek dersi olsa bile kesişen satırlar taranmalı."""
    sonuc = solve(SolveInput(
        slots=_kesisen_slotlar(),
        lessons=[ders(1, 1, 10, "Matematik", 2, desen="1+1", gunluk=2)],
        time_limit_seconds=5, cakisma_olcutu=SAAT,
    ))
    assert not sonuc.ok


def test_saat_olcutu_bitisik_saatleri_ayirmaz():
    """Uç uça saatler (09:00-09:40, 09:40-10:20) çakışma değildir."""
    slots = [
        Slot(period_id=1, day_index=0, period_index=0, day_name="Pazartesi",
             period_name="1. ders", baslangic=540, bitis=580),
        Slot(period_id=2, day_index=0, period_index=1, day_name="Pazartesi",
             period_name="2. ders", baslangic=580, bitis=620),
    ]
    sonuc = solve(SolveInput(
        slots=slots, lessons=_tek_ogretmen_iki_sube(),
        time_limit_seconds=5, cakisma_olcutu=SAAT,
    ))
    assert sonuc.ok
    assert len(sonuc.placements) == 2


def test_satir_olcutunde_ortusen_saatler_cakisma_sayilmaz(yonetici: TestClient):
    """Uçtan uca: eski davranışta iki ders aynı güne sığar."""
    pid = _ortusen_izgarali_okul(yonetici)
    uret_ve_bekle(yonetici, pid)

    izgara = yonetici.get(f"/api/timetables/{pid}/grid").json()
    assert len(izgara["cells"]) == 2
    assert len({h["period_id"] for h in izgara["cells"]}) == 2


def test_saat_olcutu_elle_tasimayi_da_engeller(yonetici: TestClient):
    """Elle düzenleme çözücüyle aynı ölçüdü kullanır; gerekçe satırı söyler."""
    _olcutu_ayarla(yonetici, SAAT)
    pid = _ortusen_izgarali_okul(yonetici)

    # Bir dersi 1. saate koy, ötekini kesişen 2. saate koymayı dene.
    gunler = yonetici.get("/api/timegrid").json()
    saatler = sorted(gunler[0]["periods"], key=lambda x: x["index"])
    satirlar = yonetici.get("/api/curriculum").json()

    ilk = yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": satirlar[0]["id"],
        "period_id": saatler[0]["id"], "uzunluk": 1,
    })
    assert ilk.status_code == 200, ilk.text

    ikinci = yonetici.post(f"/api/timetables/{pid}/place", json={
        "curriculum_entry_id": satirlar[1]["id"],
        "period_id": saatler[1]["id"], "uzunluk": 1,
    })
    assert ikinci.status_code == 409, ikinci.text
    gerekce = ikinci.json()["detail"]
    assert "Tek Öğretmen" in gerekce
    assert "1. ders" in gerekce, gerekce


def test_satir_olcutunde_ayni_tasima_serbesttir(yonetici: TestClient):
    """Aynı hamle, varsayılan ölçütte kabul edilir."""
    pid = _ortusen_izgarali_okul(yonetici)
    gunler = yonetici.get("/api/timegrid").json()
    saatler = sorted(gunler[0]["periods"], key=lambda x: x["index"])
    satirlar = yonetici.get("/api/curriculum").json()

    for satir, saat in zip(satirlar, saatler):
        r = yonetici.post(f"/api/timetables/{pid}/place", json={
            "curriculum_entry_id": satir["id"],
            "period_id": saat["id"], "uzunluk": 1,
        })
        assert r.status_code == 200, r.text
