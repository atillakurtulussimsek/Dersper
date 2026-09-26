"""Kayıt kilidi: bir şubenin ya da öğretmenin programı dokunulmazdır.

Hücre kilidi (Assignment.is_locked) tek saati yerinde tutar; kayıt kilidi
ise bir şube ya da öğretmenin BÜTÜN programını dondurur. Planlama sırasında
"9-A bitti, ona dokunma" demenin yoludur:

  * Çözücü o kaydın derslerini modele hiç almaz; yerleşmiş saatleri olduğu
    gibi kalır, yerleşmemiş saatleri de yerleştirilmez. Dolu saatleri öbür
    derslerin öğretmen/şube için meşgul sayılır ki çakışma doğmasın.
  * Elle düzenleme (taşıma, rafa alma, yerleştirme) reddedilir.

Kilit programa aittir (Timetable.locked_section_ids / locked_teacher_ids):
aynı dönemin başka bir programında serbest kalabilir.
"""
from __future__ import annotations

from dataclasses import replace

from app.models import Assignment, CurriculumEntry, Timetable
from app.solver.engine import Lesson


def kilitli_subeler(program: Timetable) -> set[int]:
    return set(program.locked_section_ids or [])


def kilitli_ogretmenler(program: Timetable) -> set[int]:
    return set(program.locked_teacher_ids or [])


def _entry_subeleri(entry: CurriculumEntry) -> set[int]:
    return {entry.section_id} | {x.section_id for x in entry.extra_sections}


def kilitli_mi(
    program: Timetable, entry: CurriculumEntry, merged_entry: CurriculumEntry | None = None,
) -> bool:
    """Bu ders (ve varsa ortak okutulduğu öbür ders) kilitli bir kayda mı ait?"""
    subeler = kilitli_subeler(program)
    ogretmenler = kilitli_ogretmenler(program)
    if not subeler and not ogretmenler:
        return False
    for e in (entry, merged_entry):
        if e is None:
            continue
        if e.teacher_id in ogretmenler or _entry_subeleri(e) & subeler:
            return True
    return False


def kilit_nedeni(
    program: Timetable, entry: CurriculumEntry, merged_entry: CurriculumEntry | None = None,
) -> str | None:
    """Reddetme gerekçesi: "9-A şubesi kilitli" ya da "Ayşe Yılmaz kilitli"."""
    subeler = kilitli_subeler(program)
    ogretmenler = kilitli_ogretmenler(program)
    for e in (entry, merged_entry):
        if e is None:
            continue
        if e.teacher_id in ogretmenler:
            return (f"{e.teacher.full_name} kilitli; programına dokunulmaz. "
                    f"Önce öğretmenin kilidini açın.")
        for sb in [e.section] + [x.section for x in e.extra_sections]:
            if sb.id in subeler:
                return (f"{sb.name} şubesi kilitli; programına dokunulmaz. "
                        f"Önce şubenin kilidini açın.")
    return None


def _dersin_subeleri(lesson: Lesson) -> set[int]:
    return {sid for sid, _ in lesson.sections} or {lesson.section_id}


def kayit_kilidi_uygula(
    lessons: list[Lesson], atamalar: list[Assignment],
    subeler: set[int], ogretmenler: set[int],
) -> tuple[list[Lesson], list[Assignment]]:
    """Çözücü girdisini kilitli kayıtlara göre budar.

    Döner: (modele girecek dersler, olduğu gibi korunacak yerleşimler).

    * Kilitli kayda ait ders modelden çıkar; yerleşimleri korunur.
    * Korunan yerleşimlerin saatleri, aynı öğretmenin ve aynı şubelerin öbür
      dersleri için kapalı sayılır.
    * Birleştirme kuralı: kilitli bir kaydı ilgilendiren kuralın bütün
      sanal ortak dersleri çıkar (kural dondurulur); kilitsiz ebeveynin
      haftalık saati korunan ortak saatler kadar düşer.
    """
    if not subeler and not ogretmenler:
        return lessons, []

    def kilitli(l: Lesson) -> bool:
        return l.teacher_id in ogretmenler or bool(_dersin_subeleri(l) & subeler)

    def atama_kilitli(a: Assignment) -> bool:
        for e in (a.entry, a.merged_entry):
            if e is not None and (e.teacher_id in ogretmenler
                                  or _entry_subeleri(e) & subeler):
                return True
        return False

    korunan = [a for a in atamalar if atama_kilitli(a)]

    # Korunan saatler: öğretmen ve şube başına meşgul period kümesi.
    mesgul_ogretmen: dict[int, set[int]] = {}
    mesgul_sube: dict[int, set[int]] = {}
    ortak_korunan: dict[int, int] = {}      # ebeveyn entry -> korunan ortak saat
    for a in korunan:
        for e in (a.entry, a.merged_entry):
            if e is None:
                continue
            mesgul_ogretmen.setdefault(e.teacher_id, set()).add(a.period_id)
            for sid in _entry_subeleri(e):
                mesgul_sube.setdefault(sid, set()).add(a.period_id)
        if a.merged_entry_id is not None:
            ortak_korunan[a.curriculum_entry_id] = ortak_korunan.get(a.curriculum_entry_id, 0) + 1
            ortak_korunan[a.merged_entry_id] = ortak_korunan.get(a.merged_entry_id, 0) + 1

    # Kilitli kaydı ilgilendiren kurallar bütünüyle dondurulur.
    kilitli_entryler = {l.entry_id for l in lessons if not l.ortak and kilitli(l)}
    donan_kurallar = {
        l.ortak_kural_id for l in lessons
        if l.ortak and (kilitli(l) or set(l.ortak_ebeveynler) & kilitli_entryler)
    }

    kalan: list[Lesson] = []
    for l in lessons:
        if l.ortak:
            if l.ortak_kural_id in donan_kurallar:
                continue
        elif kilitli(l):
            continue
        ek_ogr = mesgul_ogretmen.get(l.teacher_id, set())
        ek_sube: set[int] = set()
        for sid in _dersin_subeleri(l):
            ek_sube |= mesgul_sube.get(sid, set())
        yeni = replace(
            l,
            blocked_period_ids=l.blocked_period_ids | frozenset(ek_ogr),
            section_blocked_period_ids=l.section_blocked_period_ids | frozenset(ek_sube),
            section_blocked_map=tuple(
                (sid, kume | frozenset(mesgul_sube.get(sid, set())))
                for sid, kume in l.section_blocked_map
            ),
        )
        # Kilitsiz ebeveyn: korunan ortak saatler zaten yerleşmiş sayılır.
        dusulecek = ortak_korunan.get(l.entry_id, 0) if not l.ortak else 0
        if dusulecek:
            saat = max(0, l.weekly_hours - dusulecek)
            yeni = replace(yeni, weekly_hours=saat, blocks=_bloklari_kirp(l.blocks, saat))
            if saat == 0:
                continue
        kalan.append(yeni)
    return kalan, korunan


def _bloklari_kirp(bloklar: tuple[int, ...], saat: int) -> tuple[int, ...]:
    """Blok desenini `saat` toplamına indirir; sondan kırpar, deseni korur."""
    kalan = saat
    sonuc: list[int] = []
    for b in bloklar:
        if kalan <= 0:
            break
        sonuc.append(min(b, kalan))
        kalan -= sonuc[-1]
    return tuple(sonuc)
