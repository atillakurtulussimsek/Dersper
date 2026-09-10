"""Akış tabanlı kapasite kontrolü: dersler gerçekten hangi saatlere sığar?

Basit sayım ("35 saat yük, 70 açık saat") yanıltır: öğretmenin dersleri
sabahçı ve akşamcı şubelerde toplanmışsa hepsi aynı dar pencereye sıkışır.
Burada her ders, öğretmenin de şubenin de açık olduğu saatlere bir akış ağıyla
bağlanır; en büyük akış, yerleşebilecek en çok saat sayısıdır. Yük bundan
fazlaysa program KESİNLİKLE kurulamaz — blok, günlük sınır gibi kurallara
bakılmadan bile. Hall koşulunu bozan en dar ders kümesi de bulunur; kullanıcıya
"şu dersler şu kadar saate sığmıyor" diye adıyla söylenir.

Ağ küçüktür (en çok birkaç yüz ders × yüz saat); Edmonds–Karp yeter.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from app.solver.engine import Lesson, Slot, sube_ciftleri


@dataclass(frozen=True)
class Darbogaz:
    """Sığmayan ders kümesi: toplam saati, sığabileceği en çok saat, dersler.

    `indirim`: birleştirme kurallarının bu kümeden düşebileceği en çok saat.
    """
    gereken: int
    sigan: int
    dersler: tuple[Lesson, ...]
    indirim: int = 0

    @property
    def fazla(self) -> int:
        return self.gereken - self.indirim - self.sigan


def _en_buyuk_akis(kap: dict, kaynak, hedef) -> int:
    akis = 0
    while True:
        ebeveyn = {kaynak: None}
        kuyruk = deque([kaynak])
        while kuyruk and hedef not in ebeveyn:
            u = kuyruk.popleft()
            for v, c in kap[u].items():
                if c > 0 and v not in ebeveyn:
                    ebeveyn[v] = u
                    kuyruk.append(v)
        if hedef not in ebeveyn:
            return akis
        v, darlik = hedef, float("inf")
        while ebeveyn[v] is not None:
            u = ebeveyn[v]
            darlik = min(darlik, kap[u][v])
            v = u
        v = hedef
        while ebeveyn[v] is not None:
            u = ebeveyn[v]
            kap[u][v] -= darlik
            kap[v][u] += darlik
            v = u
        akis += darlik


def darbogaz(slots: list[Slot], dersler: list[Lesson], indirim: int = 0) -> Darbogaz | None:
    """Verilen dersler (aynı öğretmen ya da aynı şube) birlikte sığıyor mu?

    Sığmıyorsa Hall koşulunu bozan kümeyi döner: artık ağda kaynaktan
    ulaşılabilen dersler, ulaşılabilen saatlerden daha çok saat ister.
    `indirim` kadar saat (birleştirme kuralı) gerekenden düşülür.
    """
    dersler = [l for l in dersler if not l.ortak]
    if not dersler:
        return None
    kap: dict = defaultdict(lambda: defaultdict(int))
    for i, l in enumerate(dersler):
        kap["k"][("d", i)] += l.weekly_hours
        for s in slots:
            if s.period_id in l.engelli_period_ids:
                continue
            kap[("d", i)][("s", s.period_id)] += 1
            kap[("s", s.period_id)]["h"] = 1
    gereken = sum(l.weekly_hours for l in dersler)
    sigan = _en_buyuk_akis(kap, "k", "h")
    if sigan >= gereken - indirim:
        return None

    # Artık ağda kaynaktan ulaşılabilen dersler = darboğaz kümesi.
    ulasilan = {"k"}
    kuyruk = deque(["k"])
    while kuyruk:
        u = kuyruk.popleft()
        for v, c in kap[u].items():
            if c > 0 and v not in ulasilan:
                ulasilan.add(v)
                kuyruk.append(v)
    kume = [dersler[i] for i in range(len(dersler)) if ("d", i) in ulasilan]
    kume_gereken = sum(l.weekly_hours for l in kume)
    kume_sigan = sum(1 for v in ulasilan if isinstance(v, tuple) and v[0] == "s")
    kume.sort(key=lambda l: -l.weekly_hours)
    if kume_gereken - indirim <= kume_sigan:
        # Darboğaz kümesi indirimle sığıyor; tüm kümeyle bildir.
        return Darbogaz(gereken=gereken, sigan=sigan, dersler=tuple(dersler),
                        indirim=indirim)
    return Darbogaz(gereken=kume_gereken, sigan=kume_sigan, dersler=tuple(kume),
                    indirim=indirim)


def _ders_listesi(dersler: tuple[Lesson, ...], sube_adiyla: bool) -> str:
    parcalar = []
    for l in dersler:
        ad = f"{' + '.join(a for _, a in sube_ciftleri(l))} {l.subject_name}" \
            if sube_adiyla else f"{l.subject_name} ({l.teacher_name})"
        parcalar.append(f"{ad} {l.weekly_hours} saat")
    return ", ".join(parcalar)


def ogretmen_bulgulari(slots: list[Slot], lessons: list[Lesson],
                       atla: set[int] = frozenset(),
                       indirim: dict[int, int] | None = None) -> list[dict]:
    """Her öğretmen için akış kontrolü. `atla`: zaten bildirilen öğretmenler.
    `indirim`: birleştirme kurallarının öğretmenden düşebileceği saat."""
    gruplar: dict[int, list[Lesson]] = defaultdict(list)
    for l in lessons:
        if not l.ortak:
            gruplar[l.teacher_id].append(l)
    bulgular = []
    for tid, dersler in gruplar.items():
        if tid in atla:
            continue
        d = darbogaz(slots, dersler, (indirim or {}).get(tid, 0))
        if d is None:
            continue
        ad = dersler[0].teacher_name
        subeler = sorted({a for l in d.dersler for _, a in sube_ciftleri(l)})
        indirim_notu = (f" Birleştirme kuralı en çok {d.indirim} saat düşürebilir."
                        if d.indirim else "")
        bulgular.append({
            "kod": "ogretmen_akis",
            "baslik": f"{ad} öğretmenin dersleri şubelerin açık saatlerine sığmıyor",
            "detay": (f"{_ders_listesi(d.dersler, True)}: toplam {d.gereken} saat. "
                      f"Bu şubelerin {ad} öğretmenin de müsait olduğu açık saatleri "
                      f"birlikte en çok {d.sigan} saat alıyor.{indirim_notu} "
                      f"{d.fazla} saat fazla."),
            "oneri": (f"Bu derslerden en az {d.fazla} saatini başka öğretmene verin "
                      f"ya da {', '.join(subeler)} şubelerinin müsaitliğinde "
                      f"{ad} için {d.fazla} ortak saat daha açın."),
            "onem": "engel",
            "ogretmen": ad,
            "gereken": d.gereken,
            "mevcut": d.sigan,
        })
    return bulgular


def sube_bulgulari(slots: list[Slot], lessons: list[Lesson],
                   atla: set[int] = frozenset()) -> list[dict]:
    """Her şube için akış kontrolü: dersleri öğretmenlerinin müsaitliğiyle sığıyor mu?"""
    gruplar: dict[int, list[Lesson]] = defaultdict(list)
    adlar: dict[int, str] = {}
    for l in lessons:
        if l.ortak:
            continue
        for si, ad in sube_ciftleri(l):
            gruplar[si].append(l)
            adlar[si] = ad
    bulgular = []
    for sid, dersler in gruplar.items():
        if sid in atla:
            continue
        d = darbogaz(slots, dersler)
        if d is None:
            continue
        ad = adlar[sid]
        ogretmenler = sorted({l.teacher_name for l in d.dersler})
        bulgular.append({
            "kod": "sube_akis",
            "baslik": f"{ad} şubesinin dersleri öğretmenlerin müsait saatlerine sığmıyor",
            "detay": (f"{_ders_listesi(d.dersler, False)}: toplam {d.gereken} saat. "
                      f"Şubenin açık olduğu ve bu öğretmenlerin müsait olduğu saatler "
                      f"birlikte en çok {d.sigan}. {d.fazla} saat fazla."),
            "oneri": (f"{', '.join(ogretmenler)} için {ad} şubesinin açık olduğu "
                      f"saatlerde en az {d.fazla} saat müsaitlik açın ya da bu "
                      f"derslerden {d.fazla} saatini başka öğretmene verin."),
            "onem": "engel",
            "sube": ad,
            "gereken": d.gereken,
            "mevcut": d.sigan,
        })
    return bulgular
