"""Ders programı üretici — Google OR-Tools CP-SAT.

Model blok tabanlıdır: her müfredat satırı, haftalık saatine göre bloklara
bölünür (örn. 5 saat, blok 2 → [2, 2, 1]). Her blok gün içinde ardışık ders
saatlerine yerleşir.

Sert kısıtlar (v1):
  1. Her müfredat satırı haftalık saatinin tamamını alır.
  2. Bir şube aynı anda tek derste olur.
  3. Bir öğretmen aynı anda tek derste olur.
  4. Öğretmenin ya da şubenin uygun olmadığı saatlere ders konmaz.
  5. Her blok gün içinde ardışık saatlere oturur, günü aşmaz. Blok uzunluklarını
     kullanıcı belirler (örn. 5 saatlik ders "2+2+1").
  6. Aynı ders bir şubede günde `max_per_day` saatten fazla olmaz.
  7. Teneffüslere ders konmaz.
  8. Kilitli yerleşimler yerinde kalır.

Program yerleşmezse model gevşetilir: yerleşemeyen saatler açıkça raporlanır.
"""
from __future__ import annotations

import time as _time
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

# Gevşetilmiş modelde yerleşemeyen her ders saatinin bedeli.
CEZA_YERLESMEYEN = 1000
VARSAYILAN_SURE_SN = 30.0


@dataclass(frozen=True)
class Slot:
    """Haftadaki tek bir ders saati."""
    period_id: int
    day_index: int
    period_index: int
    day_name: str
    period_name: str


@dataclass(frozen=True)
class Lesson:
    """Çözücünün gördüğü haliyle bir müfredat satırı."""
    entry_id: int
    section_id: int
    section_name: str
    teacher_id: int
    teacher_name: str
    subject_name: str
    weekly_hours: int
    # Blok uzunlukları, örn. (2, 2, 1). Toplamı weekly_hours eder.
    blocks: tuple[int, ...]
    max_per_day: int
    # Öğretmenin uygun OLMADIĞI period_id kümesi
    blocked_period_ids: frozenset[int]
    # Şubenin uygun OLMADIĞI period_id kümesi
    section_blocked_period_ids: frozenset[int] = frozenset()

    @property
    def engelli_period_ids(self) -> frozenset[int]:
        """Ne öğretmenin ne de şubenin müsait olduğu saatler."""
        return self.blocked_period_ids | self.section_blocked_period_ids


@dataclass
class SolveInput:
    slots: list[Slot]
    lessons: list[Lesson]
    # entry_id -> yerinde kalması gereken period_id listesi
    locked: dict[int, list[int]] = field(default_factory=dict)
    time_limit_seconds: float = VARSAYILAN_SURE_SN


@dataclass
class SolveOutput:
    ok: bool
    # (entry_id, period_id) çiftleri
    placements: list[tuple[int, int]]
    seconds: float
    # Yerleşemeyen saatler: entry_id -> saat sayısı (sadece gevşetilmiş çözümde)
    unplaced: dict[int, int]
    status_name: str


def _gune_gore(slots: list[Slot]) -> dict[int, list[int]]:
    """day_index -> slot dizinleri (ders saati sırasına göre)."""
    gunler: dict[int, list[int]] = {}
    for i, s in enumerate(slots):
        gunler.setdefault(s.day_index, []).append(i)
    for idx_list in gunler.values():
        idx_list.sort(key=lambda i: slots[i].period_index)
    return gunler


def _ardisik_mi(slots: list[Slot], indices: list[int]) -> bool:
    """Verilen slotlar gün içinde kesintisiz ardışık mı?"""
    nums = [slots[i].period_index for i in indices]
    return all(b - a == 1 for a, b in zip(nums, nums[1:]))


def solve(data: SolveInput) -> SolveOutput:
    """Önce sert modeli dener; çözümsüzse gevşetilmiş modeli çözer."""
    sonuc = _calistir(data, gevsek=False)
    if sonuc.ok:
        return sonuc
    return _calistir(data, gevsek=True)


def _calistir(data: SolveInput, *, gevsek: bool) -> SolveOutput:
    basla = _time.monotonic()
    slots = data.slots
    gunler = _gune_gore(slots)
    slot_by_period = {s.period_id: i for i, s in enumerate(slots)}

    model = cp_model.CpModel()

    # y[(lesson_idx, blok_idx)] -> {baslangic_slot_idx: BoolVar}
    baslangic: dict[tuple[int, int], dict[int, cp_model.IntVar]] = {}
    # x[(lesson_idx, slot_idx)] -> BoolVar (o saatte ders var mı)
    dolu: dict[tuple[int, int], cp_model.IntVar] = {}
    yerlesmeyen: dict[int, cp_model.IntVar] = {}

    for li, lesson in enumerate(data.lessons):
        bloklar = list(lesson.blocks)
        engelli = lesson.engelli_period_ids

        for bi, boy in enumerate(bloklar):
            secenekler: dict[int, cp_model.IntVar] = {}
            for gun_slotlari in gunler.values():
                for konum in range(len(gun_slotlari) - boy + 1):
                    pencere = gun_slotlari[konum:konum + boy]
                    if not _ardisik_mi(slots, pencere):
                        continue
                    if any(slots[i].period_id in engelli for i in pencere):
                        continue
                    v = model.NewBoolVar(f"b_{li}_{bi}_{pencere[0]}")
                    secenekler[pencere[0]] = v
            baslangic[(li, bi)] = secenekler

        # (1) Haftalık saatin tamamı yerleşir. Gevşek modelde eksik kalabilir.
        if gevsek:
            eksik = model.NewIntVar(0, lesson.weekly_hours, f"eksik_{li}")
            yerlesmeyen[li] = eksik
        for bi, boy in enumerate(bloklar):
            secenekler = baslangic[(li, bi)]
            if not secenekler:
                # Bu blok hiçbir yere sığmıyor.
                if not gevsek:
                    model.Add(1 == 0)
                continue
            if gevsek:
                model.Add(sum(secenekler.values()) <= 1)
            else:
                model.AddExactlyOne(secenekler.values())

        if gevsek:
            yerlesen = sum(
                boy * var
                for bi, boy in enumerate(bloklar)
                for var in baslangic[(li, bi)].values()
            )
            model.Add(yerlesmeyen[li] == lesson.weekly_hours - yerlesen)

        # x değişkenleri: blok başlangıçlarından türetilir.
        for si in range(len(slots)):
            kapsayan = []
            for bi, boy in enumerate(bloklar):
                for bas, var in baslangic[(li, bi)].items():
                    if bas <= si < bas + boy:
                        kapsayan.append(var)
            if kapsayan:
                x = model.NewBoolVar(f"x_{li}_{si}")
                model.Add(x == sum(kapsayan))
                dolu[(li, si)] = x

        # (6) Aynı ders bir şubede günde en fazla max_per_day saat.
        for gun_slotlari in gunler.values():
            gunluk = [dolu[(li, si)] for si in gun_slotlari if (li, si) in dolu]
            if len(gunluk) > lesson.max_per_day:
                model.Add(sum(gunluk) <= lesson.max_per_day)

    # (2) Şube çakışması
    _tekil_kaynak(model, data.lessons, dolu, len(slots), lambda l: l.section_id)
    # (3) Öğretmen çakışması
    _tekil_kaynak(model, data.lessons, dolu, len(slots), lambda l: l.teacher_id)

    # (8) Kilitli yerleşimler
    for li, lesson in enumerate(data.lessons):
        for period_id in data.locked.get(lesson.entry_id, []):
            si = slot_by_period.get(period_id)
            if si is not None and (li, si) in dolu:
                model.Add(dolu[(li, si)] == 1)

    if gevsek:
        model.Minimize(sum(CEZA_YERLESMEYEN * v for v in yerlesmeyen.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = data.time_limit_seconds
    solver.parameters.num_workers = 8
    status = solver.Solve(model)
    gecen = _time.monotonic() - basla

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveOutput(
            ok=False, placements=[], seconds=gecen, unplaced={},
            status_name=solver.StatusName(status),
        )

    yerlesim = [
        (data.lessons[li].entry_id, slots[si].period_id)
        for (li, si), var in dolu.items()
        if solver.Value(var)
    ]
    eksikler = {
        data.lessons[li].entry_id: int(solver.Value(v))
        for li, v in yerlesmeyen.items()
        if solver.Value(v) > 0
    }
    return SolveOutput(
        ok=not eksikler,
        placements=yerlesim,
        seconds=gecen,
        unplaced=eksikler,
        status_name=solver.StatusName(status),
    )


def _tekil_kaynak(model, lessons, dolu, slot_sayisi, anahtar) -> None:
    """Aynı kaynağı (şube ya da öğretmen) paylaşan dersler aynı saatte olamaz."""
    gruplar: dict[int, list[int]] = {}
    for li, lesson in enumerate(lessons):
        gruplar.setdefault(anahtar(lesson), []).append(li)

    for uyeler in gruplar.values():
        if len(uyeler) < 2:
            continue
        for si in range(slot_sayisi):
            cakisanlar = [dolu[(li, si)] for li in uyeler if (li, si) in dolu]
            if len(cakisanlar) > 1:
                model.AddAtMostOne(cakisanlar)
