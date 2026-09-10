"""Yapay zeka açıklaması: kısaltılmış özet gider, denenmiş çözümler ayrılır."""
from app.ai.client import SISTEM_MESAJI, rapor_ozeti


def _rapor() -> dict:
    return {
        "durum": "INFEASIBLE", "sure_sn": 12.5,
        "ozet": {"ders_saati_sayisi": 40, "yerlesmeyen_toplam": 3},
        "bulgular": [
            {"kod": "sube_kapasite", "onem": "engel", "baslik": "7/A sığmıyor", "detay": "16 > 8"},
            {"kod": "yerlesemedi", "onem": "uyari", "baslik": "7/A · Fen", "detay": "..."},
        ],
        "yerlesmeyenler": [{"sube": "7/A", "ders": "Fen", "ogretmen": "Ali", "istenen_saat": 4, "yerlesmeyen_saat": 3}],
        "sikisiklik": [{"tur": "ogretmen", "metin": "Ali: 30 yük, 30 açık (%100)", "oneri": "yükü aktarın", "oran": 100}],
        "celiskiler": [
            {"tur": "ogretmen", "metin": "Ali (öğretmen): pay yok", "oneri": "Ali için bir dersini başka öğretmene verin", "tek_basina_yeterli": True},
            {"tur": "ogretmen", "metin": "Ayşe (öğretmen): pay az", "oneri": "Ayşe için saat açın", "tek_basina_yeterli": False},
            {"tur": "sube", "metin": "7/A: Salı 3 dolamaz", "oneri": "7/A'yı kapatın", "tek_basina_yeterli": None},
        ],
    }


def test_ozet_denenmisleri_ayirir():
    o = rapor_ozeti(_rapor())
    assert [m["yapilacak"] for m in o["denenmis_cozumler"]] == ["Ali için bir dersini başka öğretmene verin"]
    assert o["yetmeyenler"] == ["Ayşe (öğretmen): pay az"]
    assert [m["sorun"] for m in o["denenmemis_ipuclari"]] == ["7/A: Salı 3 dolamaz", "Ali: 30 yük, 30 açık (%100)"]
    assert [e["baslik"] for e in o["kesin_engeller"]] == ["7/A sığmıyor"]
    assert o["yerlesmeyen_toplam_saat"] == 3


def test_ozet_gurultuyu_atar():
    o = rapor_ozeti(_rapor())
    assert "sure_sn" not in o and "durum" not in o and "ozet" not in o


def test_istem_kisa_ve_denenmis_vurgulu():
    assert "arka planda denendi" in SISTEM_MESAJI
    assert "denenmedi" in SISTEM_MESAJI
    assert "120 kelime" in SISTEM_MESAJI


def test_acikla_ozeti_gonderir(monkeypatch):
    from app.ai import client as ai

    gorulen = {}

    class Yanit:
        class _C:
            class message: content = "  Kısa metin.  "
        choices = [_C()]

    class Sahte:
        def __init__(self, api_key, base_url):
            self.chat = self
            self.completions = self

        def create(self, **kw):
            gorulen.update(kw)
            return Yanit()

    monkeypatch.setattr(ai, "_istemci", lambda k, u: Sahte(k, u))
    monkeypatch.setattr(ai, "istemci_olustur", lambda ayar: (Sahte("k", None), "m"))
    metin = ai.cozumsuzluk_acikla(None, _rapor())
    assert metin == "Kısa metin."
    kullanici = gorulen["messages"][1]["content"]
    assert "denenmis_cozumler" in kullanici
    assert "sure_sn" not in kullanici
    assert gorulen["max_tokens"] <= 400
