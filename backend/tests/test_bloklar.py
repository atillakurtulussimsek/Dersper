"""Blok deseni ayrıştırma testleri."""
import pytest

from app.bloklar import DesenHatasi, coz, duzenle, onerilenler, yaz


def test_desen_cozulur():
    assert coz("2+2+1", 5) == [2, 2, 1]
    assert coz("1+1+2+1", 5) == [1, 1, 2, 1]
    assert coz("4", 4) == [4]


def test_ayraclar_esnek():
    assert coz("2, 2, 1", 5) == [2, 2, 1]
    assert coz("2 2 1", 5) == [2, 2, 1]
    assert coz(" 2 + 2 + 1 ", 5) == [2, 2, 1]


def test_bos_desen_tek_saatlere_acilir():
    assert coz(None, 3) == [1, 1, 1]
    assert coz("", 3) == [1, 1, 1]
    assert coz("   ", 2) == [1, 1]


def test_toplam_tutmazsa_hata():
    with pytest.raises(DesenHatasi, match="eşit olmalı"):
        coz("2+2", 5)
    with pytest.raises(DesenHatasi, match="eşit olmalı"):
        coz("2+2+2", 5)


def test_gecersiz_girdi():
    with pytest.raises(DesenHatasi, match="sayı değil"):
        coz("2+x", 5)
    with pytest.raises(DesenHatasi, match="en az 1"):
        coz("2+0", 2)
    with pytest.raises(DesenHatasi, match="en fazla"):
        coz("9", 9)


def test_yaz_ve_duzenle():
    assert yaz([2, 2, 1]) == "2+2+1"
    assert duzenle("2, 2,1", 5) == "2+2+1"
    assert duzenle(None, 3) == "1+1+1"


def test_onerilenler_haftalik_saati_tutturur():
    for saat in range(1, 13):
        for desen in onerilenler(saat):
            assert sum(coz(desen, saat)) == saat
    assert onerilenler(5)[0] == "1+1+1+1+1"
    assert "2+2+1" in onerilenler(5)
    assert onerilenler(0) == []
