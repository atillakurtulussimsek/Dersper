"""Ders bloğu desenleri.

Bir müfredat satırının haftalık saatinin gün içinde nasıl parçalanacağını
kullanıcı belirler: 5 saatlik bir ders "2+2+1" ya da "1+1+2+1" olabilir.
Desen boşsa saatler tek tek dağıtılır.
"""
from __future__ import annotations

AYRAC = "+"
EN_UZUN_BLOK = 8


class DesenHatasi(ValueError):
    """Desen okunamadı ya da haftalık saate uymuyor."""


def coz(desen: str | None, haftalik_saat: int) -> list[int]:
    """'2+2+1' → [2, 2, 1]. Boş desen tek saatlik bloklara açılır."""
    if not desen or not desen.strip():
        return [1] * haftalik_saat

    parcalar: list[int] = []
    for ham in desen.replace(",", AYRAC).replace(" ", AYRAC).split(AYRAC):
        ham = ham.strip()
        if not ham:
            continue
        if not ham.isdigit():
            raise DesenHatasi(
                f"'{ham}' bir sayı değil. Deseni 2+2+1 gibi yazın."
            )
        sayi = int(ham)
        if sayi < 1:
            raise DesenHatasi("Blok uzunluğu en az 1 olmalı.")
        if sayi > EN_UZUN_BLOK:
            raise DesenHatasi(f"Tek blok en fazla {EN_UZUN_BLOK} saat olabilir.")
        parcalar.append(sayi)

    if not parcalar:
        return [1] * haftalik_saat

    toplam = sum(parcalar)
    if toplam != haftalik_saat:
        raise DesenHatasi(
            f"Blokların toplamı {toplam} saat, haftalık ders saati ise "
            f"{haftalik_saat}. İkisi eşit olmalı."
        )
    return parcalar


def yaz(bloklar: list[int]) -> str:
    """[2, 2, 1] → '2+2+1'"""
    return AYRAC.join(str(b) for b in bloklar)


def duzenle(desen: str | None, haftalik_saat: int) -> str:
    """Deseni doğrular ve tek biçime getirir. Hatalıysa DesenHatasi yükseltir."""
    return yaz(coz(desen, haftalik_saat))


def onerilenler(haftalik_saat: int) -> list[str]:
    """Arayüzde hızlı seçim için birkaç makul desen."""
    if haftalik_saat < 1:
        return []
    if haftalik_saat == 1:
        return ["1"]

    oneriler: list[str] = [yaz([1] * haftalik_saat)]

    # Mümkün olduğunca çift blok, kalan tek saat sona.
    ciftli, kalan = divmod(haftalik_saat, 2)
    oneriler.append(yaz([2] * ciftli + ([1] if kalan else [])))

    # Bir tane çift, gerisi tek.
    if haftalik_saat >= 3:
        oneriler.append(yaz([2] + [1] * (haftalik_saat - 2)))

    # Üçlü blok, uzun derslerde.
    if haftalik_saat >= 4:
        ucluler, art = divmod(haftalik_saat, 3)
        kuyruk = [2] if art == 2 else [1] * art
        oneriler.append(yaz([3] * ucluler + kuyruk))

    benzersiz: list[str] = []
    for o in oneriler:
        if o not in benzersiz:
            benzersiz.append(o)
    return benzersiz
