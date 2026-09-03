"""Şube sırası — listelerde, şeritlerde, çarşafta ve çıktılarda tek gelenek.

Kurum seçer (bkz. `Term.section_order`):
  * ``ad``   — sınıf seviyesi, sonra ada göre DOĞAL sıra: "9-A" < "10-A".
               Düz alfabetik "10-A"yı "9-A"nın önüne koyar; okul öyle saymaz.
  * ``elle`` — kullanıcının sürükleyip kaydettiği sıra (`Section.sort_order`);
               sırası verilmemiş şubeler sona, kendi aralarında ada göre.

Sıralama Python'da yapılır, SQL'de değil: doğal sıra ve Türkçe küçük harf
karşılaştırması veritabanına göre değişmesin.
"""
from __future__ import annotations

import re
from typing import Iterable, TypeVar

AD = "ad"
ELLE = "elle"

_PARCA = re.compile(r"(\d+)")
_TR = str.maketrans("IİŞĞÜÖÇ", "ıişğüöç")

T = TypeVar("T")


def dogal_anahtar(ad: str) -> tuple:
    """"10-A" -> ("", 10, "-a"): sayılar sayı olarak karşılaştırılır."""
    return tuple(
        int(p) if p.isdigit() else p.translate(_TR).lower()
        for p in _PARCA.split(ad or "")
    )


def sube_sirala(subeler: Iterable[T], yontem: str) -> list[T]:
    """Şubeleri kurumun seçtiği yönteme göre sıralar.

    Nesnelerde `name`, `grade_level`, `sort_order` alanları beklenir.
    """
    liste = list(subeler)
    if yontem == ELLE:
        return sorted(liste, key=lambda s: (
            getattr(s, "sort_order", None) is None,
            getattr(s, "sort_order", None) or 0,
            dogal_anahtar(s.name),
        ))
    return sorted(liste, key=lambda s: (
        s.grade_level is None, s.grade_level or 0, dogal_anahtar(s.name),
    ))


def ad_sirasi(subeler: Iterable, yontem: str) -> dict[str, int]:
    """Şube adı -> sıra; ada göre satır/şerit dizmek isteyenler için."""
    return {s.name: i for i, s in enumerate(sube_sirala(subeler, yontem))}


def sirali_subeler(db, donem) -> list:
    """Dönemin silinmemiş şubeleri, kurumun seçtiği sırayla."""
    from sqlalchemy import select

    from app.models import Section

    subeler = db.scalars(
        select(Section).where(Section.term_id == donem.id, Section.deleted_at.is_(None))
    )
    return sube_sirala(subeler, donem.section_order.value)
