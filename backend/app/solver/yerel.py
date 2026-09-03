"""Yerel arama (benzetimli tavlama) — sonsuz modun beşinci motoru.

CP-SAT bir kısıt kümesinin çözümsüz olduğunu kanıtladığında hiçbir motor tam
yerleşim bulamaz; ama "en az eksikli" programı aramak başka bir iştir ve
oraya farklı bir köşeden girmek işe yarar. Bu motor tam bunun için: mevcut
en iyi yerleşimden başlar, blokları taşıyıp takas ederek eksik saati ve
esnetilebilir kural cezalarını düşürmeye çalışır. Kanıt üretmez; bulduğu
şeyi döner.

Kurallar CP-SAT modeliyle aynı ayrımda:
  sert   — çakışma (kurumun ölçütüyle), müsaitlik, blok gün içinde ardışık,
           günlük sınır (max_per_day), aynı dersin blokları bitişik olmaz,
           kilitli saatler.
  cezalı — yerleşmeyen saat (1000), öğretmen gün sınırı (40), bina geçişi (40).
Boşluk tercihi bu motorda yoktur; CP-SAT turları onu gözetir.

Hiçbir dış paket kullanmaz; yalnız standart kütüphane.
"""
from __future__ import annotations

import math
import random
import time as _time
from collections import defaultdict

from app import cakisma
from app.solver.engine import (
    CEZA_BINA_GECISI, CEZA_GUN_SINIRI, CEZA_YERLESMEYEN, Lesson, Slot,
    SolveInput, SolveOutput, subeleri,
)

STATUS = "YEREL"


class _Durum:
    """Arama durumu: blok yerleşimleri ve doluluk sayaçları."""

    def __init__(self, data: SolveInput, rng: random.Random):
        self.data = data
        self.rng = rng
        self.slots = data.slots
        n = len(self.slots)

        # Gün içi ardışıklık: sonraki[si] aynı günde bir sonraki ders saati.
        gun_sirasi: dict[int, list[int]] = defaultdict(list)
        for si, s in enumerate(self.slots):
            gun_sirasi[s.day_index].append(si)
        self.sonraki: list[int | None] = [None] * n
        self.gun: list[int] = [s.day_index for s in self.slots]
        for sis in gun_sirasi.values():
            sis.sort(key=lambda i: self.slots[i].period_index)
            for a, b in zip(sis, sis[1:]):
                if self.slots[b].period_index == self.slots[a].period_index + 1:
                    self.sonraki[a] = b

        # Aynı ana denk gelen saatler (kurumun çakışma ölçütü).
        self.es_zaman: list[set[int]] = [{si} for si in range(n)]
        for grup in cakisma.gruplar(
            [cakisma.Aralik(s.day_index, s.baslangic, s.bitis) for s in self.slots],
            data.cakisma_olcutu,
        ):
            for si in grup:
                self.es_zaman[si].update(grup)

        # Blok uzunluğuna göre olası başlangıçlar ve her başlangıcın kapladığı saatler.
        self.zincir: dict[tuple[int, int], tuple[int, ...]] = {}
        for si in range(n):
            z = [si]
            for _ in range(1, 8):
                nx = self.sonraki[z[-1]]
                if nx is None:
                    break
                z.append(nx)
            for L in range(1, len(z) + 1):
                self.zincir[(si, L)] = tuple(z[:L])

        # Bloklar: (ders, blok no) -> uzunluk; kilitli saatler sabit bloklar.
        period_to_si = {s.period_id: i for i, s in enumerate(self.slots)}
        self.bloklar: list[tuple[int, int]] = []          # (li, L)
        self.sabit: dict[int, tuple[int, ...]] = {}       # blok idx -> saatler
        self.izin: list[set[int]] = []                    # li -> konabilir saatler
        for li, l in enumerate(data.lessons):
            yasak = set(l.blocked_period_ids) | set(l.section_blocked_period_ids)
            self.izin.append({si for si, s in enumerate(self.slots) if s.period_id not in yasak})
            kilitli = sorted(
                (period_to_si[p] for p in data.locked.get(l.entry_id, []) if p in period_to_si),
                key=lambda i: (self.gun[i], self.slots[i].period_index),
            )
            # Kilitli saatlerin ardışık koşuları sabit blok olur.
            kosular: list[list[int]] = []
            for si in kilitli:
                if kosular and self.sonraki[kosular[-1][-1]] == si:
                    kosular[-1].append(si)
                else:
                    kosular.append([si])
            kalan = l.weekly_hours - len(kilitli)
            for k in kosular:
                self.sabit[len(self.bloklar)] = tuple(k)
                self.bloklar.append((li, len(k)))
            # Kalan saatler dersin deseninden, en büyük bloklardan kırpılarak.
            desen = sorted(l.blocks, reverse=True)
            eksilt = l.weekly_hours - kalan
            serbest: list[int] = []
            for b in desen:
                al = min(b, eksilt)
                eksilt -= al
                if b - al > 0:
                    serbest.append(b - al)
            for L in serbest:
                self.bloklar.append((li, L))

        self.yer: list[tuple[int, ...] | None] = [None] * len(self.bloklar)
        self.ogretmen_dolu: dict[tuple[int, int], int] = defaultdict(int)
        self.sube_dolu: dict[tuple[int, int], int] = defaultdict(int)
        self.ders_gun: dict[tuple[int, int], int] = defaultdict(int)   # (li, gün) -> saat
        for bi, saatler in self.sabit.items():
            self._koy(bi, saatler)

    # --- doluluk ---

    def _koy(self, bi: int, saatler: tuple[int, ...]) -> None:
        li, _ = self.bloklar[bi]
        l = self.data.lessons[li]
        self.yer[bi] = saatler
        for si in saatler:
            self.ogretmen_dolu[(l.teacher_id, si)] += 1
            for sid in subeleri(l):
                self.sube_dolu[(sid, si)] += 1
        self.ders_gun[(li, self.gun[saatler[0]])] += len(saatler)

    def _kaldir(self, bi: int) -> None:
        saatler = self.yer[bi]
        if saatler is None:
            return
        li, _ = self.bloklar[bi]
        l = self.data.lessons[li]
        self.yer[bi] = None
        for si in saatler:
            self.ogretmen_dolu[(l.teacher_id, si)] -= 1
            for sid in subeleri(l):
                self.sube_dolu[(sid, si)] -= 1
        self.ders_gun[(li, self.gun[saatler[0]])] -= len(saatler)

    def uygun_mu(self, bi: int, saatler: tuple[int, ...]) -> bool:
        """Blok bu saatlere konabilir mi? (blok şu an dışarıda olmalı)"""
        li, _ = self.bloklar[bi]
        l = self.data.lessons[li]
        gun = self.gun[saatler[0]]
        if self.ders_gun[(li, gun)] + len(saatler) > l.max_per_day:
            return False
        for si in saatler:
            if si not in self.izin[li]:
                return False
            for e in self.es_zaman[si]:
                if self.ogretmen_dolu[(l.teacher_id, e)]:
                    return False
                for sid in subeleri(l):
                    if self.sube_dolu[(sid, e)]:
                        return False
        # Aynı dersin başka bloğuyla bitişik olmasın.
        onceki = {si for si in range(len(self.slots)) if self.sonraki[si] in saatler}
        sonraki = {self.sonraki[saatler[-1]]} - {None}
        for obi, oyer in enumerate(self.yer):
            if obi == bi or oyer is None or self.bloklar[obi][0] != li:
                continue
            if set(oyer) & (onceki | sonraki):
                return False
        return True

    # --- ceza ---

    def ceza(self) -> int:
        d = self.data
        toplam = 0
        for bi, yer in enumerate(self.yer):
            if yer is None:
                toplam += CEZA_YERLESMEYEN * self.bloklar[bi][1]
        # Öğretmen gün sınırı ve bina geçişi.
        yarim: dict[int, set[tuple[int, bool]]] = defaultdict(set)
        bina: dict[tuple[int, int], set[int]] = defaultdict(set)
        for bi, yer in enumerate(self.yer):
            if yer is None:
                continue
            l = d.lessons[self.bloklar[bi][0]]
            for si in yer:
                s = self.slots[si]
                yarim[l.teacher_id].add((s.day_index, s.sabah))
                if d.bina_gecisi_engelle and l.building_id is not None:
                    bina[(l.teacher_id, s.day_index)].add(l.building_id)
        for tid, sinir in d.ogretmen_yarim_gun.items():
            kullanilan = yarim.get(tid, set())
            gun_tavani = -(-sinir // 2)
            asim = max(0, len(kullanilan) - sinir) + max(0, len({g for g, _ in kullanilan}) - gun_tavani)
            toplam += CEZA_GUN_SINIRI * asim
        for binalar in bina.values():
            toplam += CEZA_BINA_GECISI * max(0, len(binalar) - 1)
        return toplam

    # --- hamleler ---

    def adaylar(self, bi: int) -> list[tuple[int, ...]]:
        L = self.bloklar[bi][1]
        return [z for (si, uz), z in self.zincir.items() if uz == L]

    def yerlesimler(self) -> list[tuple[int, int]]:
        cikti = []
        for bi, yer in enumerate(self.yer):
            if yer is None:
                continue
            entry = self.data.lessons[self.bloklar[bi][0]].entry_id
            cikti.extend((entry, self.slots[si].period_id) for si in yer)
        return sorted(cikti)

    def eksikler(self) -> dict[int, int]:
        e: dict[int, int] = defaultdict(int)
        for bi, yer in enumerate(self.yer):
            if yer is None:
                e[self.data.lessons[self.bloklar[bi][0]].entry_id] += self.bloklar[bi][1]
        return dict(e)


def _ipucundan_basla(durum: _Durum) -> None:
    """Önceki en iyi yerleşimi (varsa) bloklara eşleyerek başlangıç kurar."""
    d = durum.data
    if not d.ipucu:
        return
    period_to_si = {s.period_id: i for i, s in enumerate(durum.slots)}
    entry_li = {l.entry_id: i for i, l in enumerate(d.lessons)}
    saatler_by_li: dict[int, list[int]] = defaultdict(list)
    for entry_id, pid in d.ipucu:
        if entry_id in entry_li and pid in period_to_si:
            saatler_by_li[entry_li[entry_id]].append(period_to_si[pid])
    for bi, (li, L) in enumerate(durum.bloklar):
        if durum.yer[bi] is not None:
            continue
        adaylar = set(saatler_by_li.get(li, []))
        for si in sorted(adaylar):
            z = durum.zincir.get((si, L))
            if z and set(z) <= adaylar and durum.uygun_mu(bi, z):
                durum._koy(bi, z)
                for x in z:
                    adaylar.discard(x)
                break


def _acgozlu(durum: _Durum) -> None:
    """Dışarıda kalan blokları ilk uygun yere koy (uzun bloklar önce)."""
    sira = sorted(range(len(durum.bloklar)), key=lambda bi: -durum.bloklar[bi][1])
    for bi in sira:
        if durum.yer[bi] is not None:
            continue
        adaylar = durum.adaylar(bi)
        durum.rng.shuffle(adaylar)
        for z in adaylar:
            if durum.uygun_mu(bi, z):
                durum._koy(bi, z)
                break


def coz(data: SolveInput) -> SolveOutput:
    """Tavlama. `time_limit_seconds` kadar arar, en iyi durumu döner."""
    basla = _time.monotonic()
    rng = random.Random(data.seed)
    durum = _Durum(data, rng)
    _ipucundan_basla(durum)
    _acgozlu(durum)

    ceza = durum.ceza()
    en_iyi = (ceza, durum.yerlesimler(), durum.eksikler())
    serbest = [bi for bi in range(len(durum.bloklar)) if bi not in durum.sabit]
    if not serbest:
        return _cikti(en_iyi, basla)

    sure = max(0.5, data.time_limit_seconds)
    adim = 0
    while True:
        adim += 1
        if adim % 100 == 0:
            gecen = _time.monotonic() - basla
            if gecen >= sure:
                break
            # Sıcaklık: başta 40'lık cezalar (gün sınırı, bina) rahatça
            # kabul edilir, sonda yalnız iyileşmeler.
            T = 60.0 * (1.0 - gecen / sure) + 0.5
        else:
            T = None
        if T is None:
            T = 60.0 * (1.0 - (_time.monotonic() - basla) / sure) + 0.5

        bi = rng.choice(serbest)
        eski_yer = durum.yer[bi]
        hamle = rng.random()
        if eski_yer is not None and hamle < 0.25:
            # Takas: eşit uzunlukta başka bir blokla yer değiştir.
            L = durum.bloklar[bi][1]
            esler = [o for o in serbest if o != bi and durum.bloklar[o][1] == L
                     and durum.yer[o] is not None and durum.bloklar[o][0] != durum.bloklar[bi][0]]
            if not esler:
                continue
            obi = rng.choice(esler)
            oyer = durum.yer[obi]
            durum._kaldir(bi)
            durum._kaldir(obi)
            olur = durum.uygun_mu(bi, oyer)
            if olur:
                durum._koy(bi, oyer)
                olur = durum.uygun_mu(obi, eski_yer)
            if olur:
                durum._koy(obi, eski_yer)
                yeni = durum.ceza()
                if yeni <= ceza or rng.random() < math.exp(-(yeni - ceza) / T):
                    ceza = yeni
                    if ceza < en_iyi[0]:
                        en_iyi = (ceza, durum.yerlesimler(), durum.eksikler())
                    continue
                durum._kaldir(bi)
                durum._kaldir(obi)
            elif durum.yer[bi] is not None:
                durum._kaldir(bi)
            durum._koy(bi, eski_yer)
            durum._koy(obi, oyer)
            continue

        # Taşı ya da yerleştir: birkaç rastgele aday dene.
        if eski_yer is not None:
            durum._kaldir(bi)
        adaylar = durum.adaylar(bi)
        yeni_yer = None
        for _ in range(min(25, len(adaylar))):
            z = rng.choice(adaylar)
            if z != eski_yer and durum.uygun_mu(bi, z):
                yeni_yer = z
                break
        if yeni_yer is None:
            # Nadiren: bloğu dışarıda bırakmayı dene (yer açar).
            if eski_yer is not None and rng.random() < 0.02:
                yeni = durum.ceza()
                if rng.random() < math.exp(-(yeni - ceza) / T):
                    ceza = yeni
                    continue
            if eski_yer is not None:
                durum._koy(bi, eski_yer)
            continue
        durum._koy(bi, yeni_yer)
        yeni = durum.ceza()
        if yeni <= ceza or rng.random() < math.exp(-(yeni - ceza) / T):
            ceza = yeni
            if ceza < en_iyi[0]:
                en_iyi = (ceza, durum.yerlesimler(), durum.eksikler())
                if ceza == 0:
                    break
        else:
            durum._kaldir(bi)
            if eski_yer is not None:
                durum._koy(bi, eski_yer)

    return _cikti(en_iyi, basla)


def _cikti(en_iyi, basla: float) -> SolveOutput:
    ceza, yerlesim, eksik = en_iyi
    return SolveOutput(
        ok=not eksik, placements=yerlesim, seconds=_time.monotonic() - basla,
        unplaced=eksik, status_name=STATUS,
    )
