"""Çekirdek bulunamadığında yerleşemeyen derslerden türeyen sıkışıklık ipuçları."""
from app.solver.diagnose import sikisiklik_onerileri
from tests.test_engine import ders, izgara


def test_en_sikisik_kaynak_once_gelir():
    slots = izgara()  # 5 gün × 8 saat = 40 slot
    kapali = frozenset(s.period_id for s in slots[:30])  # öğretmene yalnız 10 saat açık
    dolu = ders(1, 1, 10, "Matematik", 8, kapali=kapali)
    rahat = ders(2, 2, 11, "Türkçe", 2)
    sonuc = sikisiklik_onerileri(slots, [dolu, rahat], {1: 2, 2: 1})
    assert sonuc[0]["tur"] == "ogretmen"
    assert "Öğretmen 10" in sonuc[0]["metin"]
    assert sonuc[0]["oran"] == 80          # 8 saat yük / 10 açık saat
    assert "müsaitlik" in sonuc[0]["oneri"]


def test_yerlesmeyen_yoksa_bos():
    assert sikisiklik_onerileri(izgara(), [ders(1, 1, 10, "Matematik", 2)], {}) == []


def test_ayni_kaynak_bir_kez_listelenir():
    slots = izgara()
    a = ders(1, 1, 10, "Matematik", 3)
    b = ders(2, 1, 10, "Fizik", 3)        # aynı öğretmen, aynı şube
    sonuc = sikisiklik_onerileri(slots, [a, b], {1: 1, 2: 1})
    assert [x["tur"] for x in sonuc].count("ogretmen") == 1
    assert [x["tur"] for x in sonuc].count("sube") == 1
