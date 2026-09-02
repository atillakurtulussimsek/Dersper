"""Aynı anda olma ölçütü: iki yerleşim ne zaman çakışır?

Bir şube ya da bir öğretmen aynı anda iki yerde olamaz. "Aynı an"ın ne demek
olduğu ise okula göre değişir; kurum dönem ayarından seçer
(bkz. `Term.conflict_basis`):

  * ``ders_saati`` — ızgaranın satırı esastır. Salı 3. ders yalnızca Salı
    3. dersle çakışır; saat bilgisi hiç okunmaz. Varsayılan ve eski davranış.
    Tek bir düzenli ızgarası olan okullar için doğru olan budur: satır zaten
    saatin kendisidir.
  * ``saat`` — gerçek saat aralığı esastır. Aynı gün içinde 09:00–09:40 ile
    09:20–10:00 çakışır, ayrı satırlar olsalar bile.

İkincisi, saatleri üst üste binebilen ızgaralarda anlamlıdır: vardiyalı okullar,
bir bölümü 40 diğer bölümü 30 dakikalık dersler, ya da elle girilirken kayan
saatler. Saati girilmemiş satır ``saat`` ölçütünde de yalnızca kendisiyle
çakışır — bilinmeyen bir aralık hakkında bir şey söylenemez, uydurmak yerine
satır kimliğine düşülür.

Ölçüt tek yerde tanımlıdır; hem çözücü (`app.solver.engine`) hem elle düzenleme
(`app.duzenle`) buradan okur. Yoksa ikisi farklı şeye "çakışma" derdi.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Sequence

# Dönem ayarının alabileceği değerler.
DERS_SAATI = "ders_saati"
SAAT = "saat"


@dataclass(frozen=True)
class Aralik:
    """Bir ders saatinin zaman üzerindeki yeri.

    `baslangic`/`bitis` gün başından beri dakikadır; ikisi de yoksa satırın
    saati tanımsızdır.
    """
    gun_index: int
    baslangic: int | None = None
    bitis: int | None = None

    @property
    def zamanli(self) -> bool:
        return (
            self.baslangic is not None
            and self.bitis is not None
            and self.bitis > self.baslangic
        )


def dakikaya(t: time | None) -> int | None:
    """Saat -> gün başından beri dakika. Boş saat None kalır."""
    return None if t is None else t.hour * 60 + t.minute


def gruplar(araliklar: Sequence[Aralik], olcut: str) -> list[list[int]]:
    """Aynı ana denk gelen ders saatleri.

    Dönen her grup, bir kaynağın (şube/öğretmen) en fazla birine
    yerleşebileceği ders saatlerinin sıra numaralarıdır. Her ders saati en az
    bir grupta bulunur; tek başına olması da bir gruptur (aynı satıra iki ders
    konamaz kuralı oradan gelir).

    `ders_saati` ölçütünde her satır kendi grubudur.
    """
    if olcut != SAAT:
        return [[i] for i in range(len(araliklar))]

    zamanli: dict[int, list[int]] = {}
    sonuc: list[list[int]] = []
    for i, a in enumerate(araliklar):
        if a.zamanli:
            zamanli.setdefault(a.gun_index, []).append(i)
        else:
            # Saati bilinmeyen satır yalnızca kendisiyle çakışır.
            sonuc.append([i])

    # Aralık çizgesinde klikler, aralıklardan birinin başladığı noktalarda
    # oluşur: iki aralık kesişiyorsa geç başlayanın başlangıcı ikisinin de
    # içindedir. Yani bu tarama tüm çakışan çiftleri kapsar.
    for uyeler in zamanli.values():
        gorulen: set[frozenset[int]] = set()
        for nokta in sorted({araliklar[i].baslangic for i in uyeler}):
            klik = frozenset(
                i for i in uyeler
                if araliklar[i].baslangic <= nokta < araliklar[i].bitis  # type: ignore[operator]
            )
            if klik:
                gorulen.add(klik)
        # Her başlangıç noktası bir klik verir ama hepsi en büyük değildir:
        # yalnız başlayan bir aralık, biraz sonra başkasıyla kesişiyorsa iki kez
        # görünür. Kapsanan klikleri atmak modeli gereksiz kısıttan kurtarır.
        for klik in gorulen:
            if not any(klik < buyuk for buyuk in gorulen):
                sonuc.append(sorted(klik))
    # Sıra kümelerden gelir; okunur ve tekrarlanabilir olsun diye sabitlenir.
    sonuc.sort()
    return sonuc


def ortusenler(
    kimlikler: Sequence[int], araliklar: Sequence[Aralik], olcut: str
) -> dict[int, set[int]]:
    """kimlik -> onunla aynı ana denk gelen kimlikler (kendisi dahil)."""
    harita: dict[int, set[int]] = {k: {k} for k in kimlikler}
    for grup in gruplar(araliklar, olcut):
        kume = {kimlikler[i] for i in grup}
        for i in grup:
            harita[kimlikler[i]] |= kume
    return harita
