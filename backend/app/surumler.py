"""Ders programının sürüm geçmişi.

Programda yapılan her değişiklik — çözücü üretimi de, elle düzenleme de —
arka planda yeni bir sürüm yazar. Sürümler EKLENİR, hiç silinmez.

Geçmiş bir ağaçtır, düz bir liste değil. Geri alıp başka bir yöne gidince eski
dal olduğu yerde durur ve listeden geri yüklenebilir; silinmez. Her sürüm
ebeveynini bilir:

  * geri al  → ebeveyne git
  * ileri al → en yeni çocuğa git
  * geri yükle → herhangi bir sürüme atla (sonrası yine durur)

Programın hangi sürümde durduğu `Timetable.current_version_id` imlecinde
tutulur; ayrı bir adım yığını yoktur, tek geçmiş vardır.
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Assignment, CurriculumEntry, Period, Timetable, TimetableVersion, VersionKind,
)


def anlik_goruntu(db: Session, timetable_id: int) -> list[list]:
    """Programın o anki yerleşimleri: [[müfredat satırı, ders saati, kilitli], ...]

    Sıralı üretilir; aynı içerik her zaman aynı listeyi verir, böylece iki
    sürümü karşılaştırmak anlamlıdır.
    """
    satirlar = db.execute(
        select(Assignment.curriculum_entry_id, Assignment.period_id, Assignment.is_locked)
        .where(Assignment.timetable_id == timetable_id)
        .order_by(Assignment.period_id, Assignment.curriculum_entry_id)
    ).all()
    return [[e, p, bool(k)] for e, p, k in satirlar]


def surum_yaz(
    db: Session, program: Timetable, kind: VersionKind, label: str
) -> TimetableVersion:
    """Programın ŞU ANKİ hâlini yeni bir sürüm olarak yazar ve imleci ona taşır.

    Değişiklik uygulandıktan SONRA çağrılır: sürüm, değişikliğin sonucudur.
    Ebeveyni o anki imleçtir; geri aldıktan sonra yapılan değişiklik böylece
    eski dalı silmeden yeni bir dal açar.
    """
    # Bekleyen değişiklikler önce yazılmalı: sürüm, değişikliğin SONUCUDUR.
    # Otomatik boşaltmaya güvenmek, anlık görüntünün bir adım geride
    # kalmasına yol açabiliyor.
    db.flush()
    yerlesimler = anlik_goruntu(db, program.id)
    sonraki = (db.scalar(
        select(func.max(TimetableVersion.number))
        .where(TimetableVersion.timetable_id == program.id)
    ) or 0) + 1

    surum = TimetableVersion(
        timetable_id=program.id,
        number=sonraki,
        parent_id=program.current_version_id,
        kind=kind,
        label=label[:200],
        placements=yerlesimler,
        placed=len(yerlesimler),
    )
    db.add(surum)
    db.flush()
    program.current_version_id = surum.id
    return surum


def _gecerli_yerlesimler(
    db: Session, program: Timetable, yerlesimler: list[list]
) -> tuple[list[list], int]:
    """Sürümdeki yerleşimlerden hâlâ uygulanabilir olanlar.

    Sürüm yazıldıktan sonra ders ataması silinmiş ya da zaman ızgarası
    değişmiş olabilir. Böyle satırlar atlanır; kaç tanesinin atlandığı
    çağırana bildirilir ki kullanıcıya söylenebilsin.
    """
    entry_ids = {e for e, _, _ in yerlesimler}
    period_ids = {p for _, p, _ in yerlesimler}
    yasayan_entry = set(db.scalars(
        select(CurriculumEntry.id).where(
            CurriculumEntry.id.in_(entry_ids), CurriculumEntry.deleted_at.is_(None)
        )
    )) if entry_ids else set()
    yasayan_period = set(db.scalars(
        select(Period.id).where(Period.id.in_(period_ids))
    )) if period_ids else set()

    tutulan = [
        satir for satir in yerlesimler
        if satir[0] in yasayan_entry and satir[1] in yasayan_period
    ]
    return tutulan, len(yerlesimler) - len(tutulan)


def surumu_uygula(db: Session, program: Timetable, surum: TimetableVersion) -> int:
    """Sürümün yerleşimlerini programa yazar ve imleci ona taşır.

    Atlanan satır sayısını döner (silinmiş ders ataması ya da kaldırılmış
    ders saati yüzünden).
    """
    tutulan, atlanan = _gecerli_yerlesimler(db, program, surum.placements or [])

    for a in db.scalars(select(Assignment).where(Assignment.timetable_id == program.id)):
        db.delete(a)
    db.flush()
    for entry_id, period_id, kilitli in tutulan:
        db.add(Assignment(
            timetable_id=program.id,
            curriculum_entry_id=entry_id,
            period_id=period_id,
            is_locked=bool(kilitli),
        ))
    program.current_version_id = surum.id
    db.commit()
    return atlanan


def _surum(db: Session, program: Timetable, surum_id: int | None) -> TimetableVersion | None:
    if surum_id is None:
        return None
    surum = db.get(TimetableVersion, surum_id)
    if surum is None or surum.timetable_id != program.id:
        return None
    return surum


def gecerli_surum(db: Session, program: Timetable) -> TimetableVersion | None:
    return _surum(db, program, program.current_version_id)


def onceki_surum(db: Session, program: Timetable) -> TimetableVersion | None:
    """Geri alınacak sürüm: imlecin ebeveyni."""
    simdiki = gecerli_surum(db, program)
    return None if simdiki is None else _surum(db, program, simdiki.parent_id)


def sonraki_surum(db: Session, program: Timetable) -> TimetableVersion | None:
    """İleri alınacak sürüm: imlecin EN YENİ çocuğu.

    Geri alıp yeni bir değişiklik yapılmışsa o dal en yenidir; ileri alma
    kullanıcının en son gittiği yöne gider.
    """
    if program.current_version_id is None:
        return None
    return db.scalar(
        select(TimetableVersion)
        .where(TimetableVersion.timetable_id == program.id,
               TimetableVersion.parent_id == program.current_version_id)
        .order_by(TimetableVersion.number.desc())
        .limit(1)
    )


def geri_al(db: Session, program: Timetable) -> int:
    hedef = onceki_surum(db, program)
    if hedef is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Geri alınacak bir değişiklik yok.")
    return surumu_uygula(db, program, hedef)


def ileri_al(db: Session, program: Timetable) -> int:
    hedef = sonraki_surum(db, program)
    if hedef is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "İleri alınacak bir değişiklik yok.")
    return surumu_uygula(db, program, hedef)


def geri_yukle(db: Session, program: Timetable, number: int) -> int:
    """Listeden seçilen bir sürüme döner. Sonraki sürümler silinmez."""
    hedef = db.scalar(
        select(TimetableVersion)
        .where(TimetableVersion.timetable_id == program.id,
               TimetableVersion.number == number)
    )
    if hedef is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sürüm bulunamadı.")
    if hedef.id == program.current_version_id:
        return 0
    return surumu_uygula(db, program, hedef)


def baslangici_guvence_al(db: Session, program: Timetable) -> None:
    """Programın hiç sürümü yoksa o anki hâlini başlangıç sürümü yapar.

    Yeni program boş açılır; sürümleme öncesinden kalan programlar ise dolu
    olabilir. İkisinde de ilk değişiklikten önce bir geri dönüş noktası
    bulunmalı, yoksa ilk düzenleme geri alınamaz.
    """
    if program.current_version_id is not None:
        return
    var_mi = db.scalar(
        select(TimetableVersion.id)
        .where(TimetableVersion.timetable_id == program.id).limit(1)
    )
    if var_mi is not None:
        return
    surum_yaz(db, program, VersionKind.ILK, "Başlangıç")
