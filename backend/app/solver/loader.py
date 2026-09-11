"""Veritabanındaki tanımları çözücünün anladığı yapıya çevirir."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import bloklar
from app import cakisma
from app.models import (
    SectionMergeRule, SubjectGroup, SubjectGroupMember,
    Availability, CurriculumEntry, CurriculumEntrySection, Day, Section,
    SectionAvailability, Teacher,
    TeacherAvailability, Term,
)
from app.solver.engine import Lesson, Slot, sube_ciftleri


def sabah_mi(saatler: list, ders_saati) -> bool:
    """Bir ders saati öğle arasından önce mi?

    Günde öğle arası tanımlıysa sınır odur. Tanımlı değilse gün ders saati
    sayısına göre ortadan ikiye bölünür ve tek sayıda saat varsa fazlalık
    sabaha yazılır — okul günü tipik olarak sabah ağırlıklıdır. Bölme noktası
    o durumda bir varsayımdır; arayüz bunu kullanıcıya söyler.

    `saatler` günün TÜM saatleridir (teneffüsler dahil); öğle arasının yerini
    ancak böyle bilebiliriz.
    """
    ogle = next((p for p in saatler if p.is_lunch), None)
    if ogle is not None:
        return ders_saati.index < ogle.index

    dersler = [p for p in saatler if not p.is_break]
    if not dersler:
        return True
    sinir = -(-len(dersler) // 2)        # yukarı yuvarlama
    sirasi = [p.id for p in dersler].index(ders_saati.id)
    return sirasi < sinir


def slotlari_yukle(db: Session, donem: Term) -> list[Slot]:
    """Dönemin aktif günlerindeki, teneffüs olmayan ders saatleri."""
    gunler = db.scalars(
        select(Day)
        .options(selectinload(Day.periods))
        .where(Day.term_id == donem.id, Day.is_active.is_(True))
        .order_by(Day.index)
    )
    slots: list[Slot] = []
    for gun in gunler:
        saatler = sorted(gun.periods, key=lambda x: x.index)
        for p in saatler:
            if p.is_break:
                continue
            slots.append(Slot(
                period_id=p.id,
                day_index=gun.index,
                period_index=p.index,
                day_name=gun.name,
                period_name=p.name,
                sabah=sabah_mi(saatler, p),
                baslangic=cakisma.dakikaya(p.start_time),
                bitis=cakisma.dakikaya(p.end_time),
            ))
    return slots


def ders_gruplarini_yukle(db: Session, donem: Term) -> dict[int, tuple[int, str]]:
    """subject_id -> (grup kimliği, grup adı). Gruptaki dersler bir şubede
    arka arkaya gelmez (bkz. engine kural 7b)."""
    return {
        m.subject_id: (m.group_id, g.name)
        for g in db.scalars(select(SubjectGroup).where(SubjectGroup.term_id == donem.id))
        for m in g.members
    }


def gun_sinirlarini_yukle(db: Session, donem: Term) -> dict[int, int]:
    """teacher_id -> haftalık yarım gün sınırı. Sınırsız öğretmenler listede yok."""
    return {
        t.id: t.max_half_days
        for t in db.scalars(
            select(Teacher).where(
                Teacher.term_id == donem.id,
                Teacher.deleted_at.is_(None),
                Teacher.is_active.is_(True),
                Teacher.max_half_days.is_not(None),
            )
        )
    }


def dersleri_yukle(
    db: Session, donem: Term, section_ids: list[int] | None = None,
    slots: list[Slot] | None = None, ek_bulgular: list[dict] | None = None,
) -> list[Lesson]:
    """Dönemin dersleri. `section_ids` verilirse yalnızca o şubelerinkiler.

    `slots` verilirse kapalı saatler ızgaradaki hücrelerle sınırlanır:
    teneffüs, pasif gün ya da kısaltılmış gün gibi ızgarada olmayan hücrelerin
    "uygun değil" kayıtları sayılmaz. Yoksa kapasite hesabı bu hayalet
    hücreleri de kapalı sayar ve şube gerçekte sığarken "sığmıyor" der.
    """
    gecerli = {s.period_id for s in slots} if slots is not None else None

    def sayilir(period_id: int) -> bool:
        return gecerli is None or period_id in gecerli

    ogretmen_kapali: dict[int, set[int]] = defaultdict(set)
    for row in db.scalars(
        select(TeacherAvailability).where(
            TeacherAvailability.state == Availability.UYGUN_DEGIL
        )
    ):
        if sayilir(row.period_id):
            ogretmen_kapali[row.teacher_id].add(row.period_id)

    sube_kapali: dict[int, set[int]] = defaultdict(set)
    for row in db.scalars(
        select(SectionAvailability).where(
            SectionAvailability.state == Availability.UYGUN_DEGIL
        )
    ):
        if sayilir(row.period_id):
            sube_kapali[row.section_id].add(row.period_id)

    sorgu = (
        select(CurriculumEntry)
        .join(Section, Section.id == CurriculumEntry.section_id)
        .where(Section.term_id == donem.id, CurriculumEntry.deleted_at.is_(None))
    )
    entries = db.scalars(
        sorgu.options(
            selectinload(CurriculumEntry.section),
            selectinload(CurriculumEntry.subject),
            selectinload(CurriculumEntry.teacher),
            selectinload(CurriculumEntry.extra_sections)
            .selectinload(CurriculumEntrySection.section),
        )
    )
    kapsam = None if section_ids is None else set(section_ids)
    dersler: list[Lesson] = []
    for e in entries:
        subeler = [e.section] + [x.section for x in e.extra_sections]
        # Birleşik derste şubelerden biri kapsam dışıysa ders yine alınır:
        # dersin kaybolması, kapsamdaki şubenin saatinin eksik kalması demek
        # olurdu. Kapsam dışı şubenin kendi dersleri modelde olmadığı için
        # yanlış bir çakışma da doğmaz.
        if kapsam is not None and not any(sb.id in kapsam for sb in subeler):
            continue
        if not e.subject.is_active or not e.teacher.is_active:
            continue
        if e.subject.is_deleted or e.teacher.is_deleted:
            continue
        if any(not sb.is_active or sb.is_deleted for sb in subeler):
            continue

        # Birleşik ders tek bir yerde işlenir; şubeler farklı binalardaysa o
        # yer belirsizdir, bina kuralı bu derse uygulanmaz.
        binalar = {sb.building_id for sb in subeler}
        dersler.append(Lesson(
            entry_id=e.id,
            section_id=e.section_id,
            section_name=e.section.name,
            sections=tuple((sb.id, sb.name) for sb in subeler),
            teacher_id=e.teacher_id,
            teacher_name=e.teacher.full_name,
            subject_name=e.subject.name,
            weekly_hours=e.weekly_hours,
            blocks=tuple(bloklar.coz(e.block_pattern, e.weekly_hours)),
            max_per_day=e.max_per_day,
            subject_id=e.subject_id,
            building_id=binalar.pop() if len(binalar) == 1 else None,
            blocked_period_ids=frozenset(ogretmen_kapali.get(e.teacher_id, set())),
            # Şubelerden herhangi biri kapalıysa birleşik ders o saate konamaz.
            section_blocked_period_ids=frozenset().union(
                *(sube_kapali.get(sb.id, set()) for sb in subeler)
            ),
            section_blocked_map=tuple(
                (sb.id, frozenset(sube_kapali.get(sb.id, set()))) for sb in subeler
            ),
        ))
    ortaklar, bulgular = birlesme_kurallari(db, donem, dersler, kapsam)
    if ek_bulgular is not None:
        ek_bulgular.extend(bulgular)
    return dersler + ortaklar


def birlesme_kurallari(
    db: Session, donem: Term, dersler: list[Lesson], kapsam: set[int] | None = None,
) -> tuple[list[Lesson], list[dict]]:
    """Dönemin birleştirme kurallarından sanal ORTAK dersleri türetir.

    Her kural için iki şubede aynı öğretmenin verdiği aynı ders eşlenir; her
    eşleşme bir ortak ders olur (bkz. engine.Lesson.ortak). Çözücü hangi
    eşleşmeden kaç saat kullanacağını seçer; toplam kuralın saatine eşitlenir.

    İkinci dönüş: kuralın hiç eşleşmesi yoksa ya da eşleşmeler kuralın saatini
    karşılamıyorsa üretim başlamadan söylenecek engel bulguları.
    """
    kurallar = db.scalars(
        select(SectionMergeRule)
        .options(selectinload(SectionMergeRule.section_a),
                 selectinload(SectionMergeRule.section_b))
        .where(SectionMergeRule.term_id == donem.id)
        .order_by(SectionMergeRule.id)
    ).all()
    if not kurallar:
        return [], []

    tekli: dict[tuple[int, int, int], Lesson] = {}
    for l in dersler:
        if len(sube_ciftleri(l)) == 1:
            tekli[(l.section_id, l.teacher_id, l.subject_id)] = l

    ortaklar: list[Lesson] = []
    bulgular: list[dict] = []
    for k in kurallar:
        if kapsam is not None and (k.section_a.id not in kapsam or k.section_b.id not in kapsam):
            continue
        ad = f"{k.section_a.name} + {k.section_b.name}"
        gunler = frozenset(int(i) for i in (k.day_indexes or []))
        ciftler = [
            (a, tekli[(k.section_b_id, tid, sid)])
            for (sid_, tid, sid), a in tekli.items()
            if sid_ == k.section_a_id and (k.section_b_id, tid, sid) in tekli
        ]
        en_fazla = sum(min(a.weekly_hours, b.weekly_hours) for a, b in ciftler)
        if not ciftler or en_fazla < k.hours:
            neden = ("aynı öğretmenin verdiği ortak bir ders yok" if not ciftler
                     else f"eşleşen derslerden en çok {en_fazla} saat ortak okutulabilir")
            bulgular.append({
                "kod": "birlestirme_kurali",
                "baslik": f"{ad} birleştirme kuralı uygulanamıyor",
                "detay": f"Kural haftada {k.hours} saat ortak ders istiyor, ama {neden}.",
                "oneri": (f"Kuralın saatini düşürün ya da iki şubeye aynı öğretmenle "
                          f"aynı dersi atayın."),
                "onem": "engel",
                "sube": ad,
            })
            continue
        for a, b in sorted(ciftler, key=lambda ab: ab[0].subject_name):
            en_az = min(a.weekly_hours, b.weekly_hours)
            ortaklar.append(Lesson(
                entry_id=-(len(ortaklar) + 1),
                section_id=a.section_id, section_name=a.section_name,
                sections=((a.section_id, a.section_name), (b.section_id, b.section_name)),
                teacher_id=a.teacher_id, teacher_name=a.teacher_name,
                subject_name=a.subject_name, subject_id=a.subject_id,
                weekly_hours=en_az, blocks=(1,) * en_az,
                max_per_day=min(a.max_per_day, b.max_per_day),
                building_id=a.building_id if a.building_id == b.building_id else None,
                blocked_period_ids=a.blocked_period_ids,
                section_blocked_period_ids=(a.section_blocked_period_ids
                                            | b.section_blocked_period_ids),
                section_blocked_map=a.section_blocked_map + b.section_blocked_map,
                ortak_kural_id=k.id, ortak_ebeveynler=(a.entry_id, b.entry_id),
                kural_saat=k.hours, kural_adi=ad, izinli_gunler=gunler,
            ))
    return ortaklar, bulgular
