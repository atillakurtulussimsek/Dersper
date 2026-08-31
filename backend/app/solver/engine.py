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
  7. Aynı dersin iki bloğu arka arkaya gelmez; aralarında başka bir ders olur.
     (Yoksa "2+2" deseni gün içinde 4 saatlik tek bloğa dönüşürdü.)
  8. Teneffüslere ders konmaz.
  9. Kilitli yerleşimler yerinde kalır.
 10. Öğretmen haftada sınırından fazla gün okulda bulunmaz. Sınır yarım gün
     biriminde verilir (9 = 4,5 gün); günü sabah/öğleden sonra diye bölen şey
     ızgaradaki öğle arasıdır. Hangi günlerin kullanılacağına çözücü karar
     verir — sabit bir günü kapatmak programı gereksiz sıkıştırırdı.
 11. (İsteğe bağlı) Bir öğretmen bir günde tek binada ders verir. Binalar uzak
     olabildiği için gün içinde geçiş zordur; kural açıkken bir binanın
     dersleri bir güne toplanır. Binasız şubeler kuralın dışındadır.

Günlük sınır ve gün sınırı gerektiğinde esnetilebilir (`esnek_gunluk`): bu
kipte aşım yasak değil, cezalıdır ve çözücü toplam cezayı en aza indirir; gün
sınırını bozmak günlük sınırı bozmaktan pahalıdır. Kural 7 esnek kipte de sert
kalır, böylece esnetme "aynı ders gün içinde iki kez, arada başka ders"
biçiminde olur.

Hiçbiri yetmezse model tamamen gevşetilir: yerleşemeyen saatler raporlanır.
"""
from __future__ import annotations

import time as _time
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

# Gevşetilmiş modelde yerleşemeyen her ders saatinin bedeli.
CEZA_YERLESMEYEN = 1000
# Esnek kipte günlük sınırın her bir saatlik aşımının bedeli.
CEZA_GUNLUK_ASIM = 10
# Esnek kipte bir öğretmenin bir günde ikinci binaya geçmesinin bedeli.
# Gün sınırı kadar ağır: ikisi de fiziksel/sözleşmesel bir engeli zorlar.
CEZA_BINA_GECISI = 40
# Esnek kipte öğretmenin gün sınırını her yarım günlük aşmasının bedeli.
# Günlük tekrar sınırından ağır: o pedagojik bir tercih, bu ise öğretmenle
# yapılmış bir anlaşma. Çözücü zorunlu kalmadıkça bu sınırı bozmamalı.
CEZA_GUN_SINIRI = 40
VARSAYILAN_SURE_SN = 30.0


@dataclass(frozen=True)
class Slot:
    """Haftadaki tek bir ders saati."""
    period_id: int
    day_index: int
    period_index: int
    day_name: str
    period_name: str
    # Öğle arasından önce mi? Öğretmenlerin yarım gün sınırı buna dayanır.
    # Sınırı olan öğretmen yoksa değeri hiçbir şeyi etkilemez.
    sabah: bool = True


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
    # Şubenin dersliğinin bulunduğu bina. None = binasız (kural uygulanmaz).
    building_id: int | None = None
    # Öğretmenin uygun OLMADIĞI period_id kümesi
    blocked_period_ids: frozenset[int] = frozenset()
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
    # teacher_id -> haftada okulda bulunabileceği en fazla YARIM GÜN sayısı.
    # 9 = 4,5 gün. Listede olmayan öğretmenin sınırı yoktur.
    ogretmen_yarim_gun: dict[int, int] = field(default_factory=dict)
    time_limit_seconds: float = VARSAYILAN_SURE_SN
    # Her denemede farklı bir arama yolu izlemek için.
    seed: int = 0
    # Açıkken bir öğretmen bir günde tek binada ders verir.
    bina_gecisi_engelle: bool = False
    # Günlük ders tekrar sınırı, öğretmen gün sınırı ve bina kuralı
    # aşılabilsin mi? Aşım cezalandırılır, yasak değildir.
    esnek_gunluk: bool = False


@dataclass
class SolveOutput:
    ok: bool
    # (entry_id, period_id) çiftleri
    placements: list[tuple[int, int]]
    seconds: float
    # Yerleşemeyen saatler: entry_id -> saat sayısı (sadece gevşetilmiş çözümde)
    unplaced: dict[int, int]
    status_name: str
    # Sert model çözümsüz olduğunu KANITLADI mı? Kanıtlandıysa başka tohum
    # denemek sonuç vermez; yalnızca süre yetmediyse yeniden denemek işe yarar.
    proven_infeasible: bool = False
    # Günlük sınırın esnetildiği yerler: (entry_id, day_index, konan, sinir)
    relaxations: list[tuple[int, int, int, int]] = field(default_factory=list)


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
    """Sırayla dener: sert model → (izin verilirse) esnek günlük sınır → gevşek.

    Esnek kip yalnızca `esnek_gunluk` açıkken devreye girer; çağıran taraf bunu
    ancak sert modelle birkaç deneme başarısız olduktan sonra açar.
    """
    sert = _calistir(data, gevsek=False)
    if sert.ok:
        return sert

    if data.esnek_gunluk:
        esnek = _calistir(data, gevsek=False, esnek_gunluk=True)
        if esnek.ok:
            return esnek

    gevsek = _calistir(data, gevsek=True)
    gevsek.proven_infeasible = sert.status_name == "INFEASIBLE"
    return gevsek


def _calistir(
    data: SolveInput, *, gevsek: bool, esnek_gunluk: bool = False
) -> SolveOutput:
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
    # (ders_index, gun_index) -> günlük sınırın aşım miktarı (esnek kipte)
    asimlar: dict[tuple[int, int], cp_model.IntVar] = {}

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
        for gi, gun_slotlari in gunler.items():
            gunluk = [dolu[(li, si)] for si in gun_slotlari if (li, si) in dolu]
            if len(gunluk) <= lesson.max_per_day:
                continue
            if esnek_gunluk:
                asim = model.NewIntVar(0, len(gunluk), f"asim_{li}_{gi}")
                model.Add(asim >= sum(gunluk) - lesson.max_per_day)
                asimlar[(li, gi)] = asim
            else:
                model.Add(sum(gunluk) <= lesson.max_per_day)

        # (7) Aynı dersin blokları arka arkaya gelmesin: gün içinde kesintisiz
        # dizi, en uzun bloğu aşamaz. Yalnızca raporlama için çalıştırılan
        # gevşek modelde uygulanmaz; orada amaç en çok saati yerleştirmektir.
        en_uzun_blok = max(bloklar) if bloklar else 1
        for gun_slotlari in ([] if gevsek else gunler.values()):
            pencere = en_uzun_blok + 1
            for konum in range(len(gun_slotlari) - pencere + 1):
                dilim = gun_slotlari[konum:konum + pencere]
                if not _ardisik_mi(slots, dilim):
                    continue
                hucreler = [dolu[(li, si)] for si in dilim if (li, si) in dolu]
                if len(hucreler) > en_uzun_blok:
                    model.Add(sum(hucreler) <= en_uzun_blok)

    # (2) Şube çakışması
    _tekil_kaynak(model, data.lessons, dolu, len(slots), lambda l: l.section_id)
    # (3) Öğretmen çakışması
    _tekil_kaynak(model, data.lessons, dolu, len(slots), lambda l: l.teacher_id)

    # (10) Öğretmen gün sınırı. Günlük sınır (kural 6) gibi gevşek modelde de
    # sert kalır: orada gevşetilen tek şey "her saat yerleşmeli" kuralıdır.
    # Aksi hâlde son çare model sınırı tamamen yok sayar ve anlaşmayı sessizce
    # bozan bir programı başarılı diye döndürürdü.
    gun_asimlari = _gun_siniri(model, data, dolu, gunler, slots, esnek=esnek_gunluk)

    # (11) Bina kuralı: bir öğretmen bir günde tek binada ders verir.
    bina_asimlari = _bina_kurali(model, data, dolu, gunler, esnek=esnek_gunluk)

    # (8) Kilitli yerleşimler
    for li, lesson in enumerate(data.lessons):
        for period_id in data.locked.get(lesson.entry_id, []):
            si = slot_by_period.get(period_id)
            if si is not None and (li, si) in dolu:
                model.Add(dolu[(li, si)] == 1)

    if gevsek:
        model.Minimize(sum(CEZA_YERLESMEYEN * v for v in yerlesmeyen.values()))
    elif asimlar or gun_asimlari or bina_asimlari:
        # Tek amaç işlevi: çözücü hangi kuralı bozacağını bedele göre seçer,
        # gerekmedikçe hiçbirini bozmaz.
        model.Minimize(
            sum(CEZA_GUNLUK_ASIM * v for v in asimlar.values())
            + sum(CEZA_GUN_SINIRI * v for v in gun_asimlari.values())
            + sum(CEZA_BINA_GECISI * v for v in bina_asimlari.values())
        )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = data.time_limit_seconds
    solver.parameters.num_workers = 8
    solver.parameters.random_seed = data.seed
    status = solver.Solve(model)
    gecen = _time.monotonic() - basla

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return SolveOutput(
            ok=False, placements=[], seconds=gecen, unplaced={},
            status_name=solver.StatusName(status),
        )

    esnetmeler: list[tuple[int, int, int, int]] = []
    for (li, gi), var in asimlar.items():
        asim = int(solver.Value(var))
        if asim <= 0:
            continue
        lesson = data.lessons[li]
        konan = sum(
            1 for si in gunler[gi]
            if (li, si) in dolu and solver.Value(dolu[(li, si)])
        )
        esnetmeler.append((lesson.entry_id, gi, konan, lesson.max_per_day))

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
        relaxations=sorted(esnetmeler),
    )


def _bina_kurali(
    model, data: SolveInput, dolu: dict, gunler: dict[int, list[int]], *, esnek: bool,
) -> dict[tuple[int, int], cp_model.IntVar]:
    """Bir öğretmen bir günde tek binada ders verir.

    Binalar birbirinden uzak olabildiği için gün içinde geçiş yapmak zordur;
    kural açıkken bir binanın dersleri bir güne, öbürününki başka güne
    toplanır. Hangi binanın hangi güne düşeceğine çözücü karar verir.

    Binası olmayan şubelerin dersleri kuralın dışındadır: tek binalı kurumda
    ya da henüz bina atanmamış şubelerde yapay bir çakışma üretmemek için.

    Esnek kipte ikinci bina yasak değil cezalıdır; (öğretmen, gün) başına
    fazladan bina sayısı döner.
    """
    if not data.bina_gecisi_engelle:
        return {}

    # (öğretmen, bina) -> o binadaki ders indeksleri
    ogretmen_bina: dict[tuple[int, int], list[int]] = {}
    for li, lesson in enumerate(data.lessons):
        if lesson.building_id is None:
            continue
        ogretmen_bina.setdefault((lesson.teacher_id, lesson.building_id), []).append(li)

    ogretmenler: dict[int, set[int]] = {}
    for tid, bid in ogretmen_bina:
        ogretmenler.setdefault(tid, set()).add(bid)

    asimlar: dict[tuple[int, int], cp_model.IntVar] = {}
    for tid, binalar in ogretmenler.items():
        # Tek binada ders veren öğretmen zaten geçiş yapmaz.
        if len(binalar) < 2:
            continue
        for gi, gun_slotlari in gunler.items():
            gun_binalari = []
            for bid in sorted(binalar):
                hucreler = [
                    dolu[(li, si)]
                    for li in ogretmen_bina[(tid, bid)]
                    for si in gun_slotlari
                    if (li, si) in dolu
                ]
                if not hucreler:
                    continue
                # "Öğretmen o gün bu binada" — yalnızca aşağı bağlanır;
                # çözücünün bu değişkenleri küçük tutmakta zaten çıkarı var.
                var = model.NewBoolVar(f"bina_{tid}_{gi}_{bid}")
                for h in hucreler:
                    model.AddImplication(h, var)
                gun_binalari.append(var)

            if len(gun_binalari) < 2:
                continue
            if esnek:
                asim = model.NewIntVar(0, len(gun_binalari), f"binaasim_{tid}_{gi}")
                model.Add(asim >= sum(gun_binalari) - 1)
                asimlar[(tid, gi)] = asim
            else:
                model.Add(sum(gun_binalari) <= 1)

    return asimlar


def _gun_siniri(
    model, data: SolveInput, dolu: dict, gunler: dict[int, list[int]],
    slots: list[Slot], *, esnek: bool,
) -> dict[int, cp_model.IntVar]:
    """Öğretmenin haftada okulda bulunacağı süreyi sınırlar.

    Sınır yarım gün birimindedir (9 = 4,5 gün) ve iki kuralı birden gerektirir:

      * Toplam yarım gün ≤ sınır. Yalnız bu olsaydı "4 gün" diyen öğretmen
        3 tam + 2 yarım gün çalışıp 5 gün okula gelirdi — sayı tutar, anlaşma
        tutmaz.
      * Uğradığı ayrı gün sayısı ≤ tavan (yukarı yuvarlanmış sınır). Yalnız bu
        olsaydı 4,5 günün yarımı hiç uygulanmazdı.

    Yarım gün değişkenleri yalnızca aşağı doğru bağlanır (ders varsa yarım gün
    dolu). Ters yön gereksiz: her iki kipte de çözücünün bu değişkenleri küçük
    tutmakta çıkarı var, boş yere doldurmaz.

    Esnek kipte sınır yasak değil cezalıdır; aşım miktarları döner.
    """
    if not data.ogretmen_yarim_gun:
        return {}

    ogretmen_dersleri: dict[int, list[int]] = {}
    for li, lesson in enumerate(data.lessons):
        ogretmen_dersleri.setdefault(lesson.teacher_id, []).append(li)

    gun_sayisi = len(gunler)
    asimlar: dict[int, cp_model.IntVar] = {}

    for tid, sinir in data.ogretmen_yarim_gun.items():
        dersler = ogretmen_dersleri.get(tid)
        if not dersler:
            continue
        gun_tavani = -(-sinir // 2)      # yukarı yuvarlama
        # Haftanın tamamı zaten sınırın altındaysa kısıt hiçbir zaman bağlamaz.
        if gun_tavani >= gun_sayisi and sinir >= 2 * gun_sayisi:
            continue

        yarimlar: list[cp_model.IntVar] = []
        gun_degiskenleri: list[cp_model.IntVar] = []

        for gi, gun_slotlari in gunler.items():
            gun_yarimlari: list[cp_model.IntVar] = []
            for sabahtir in (True, False):
                hucreler = [
                    dolu[(li, si)]
                    for si in gun_slotlari
                    if slots[si].sabah == sabahtir
                    for li in dersler
                    if (li, si) in dolu
                ]
                if not hucreler:
                    continue
                yarim = model.NewBoolVar(
                    f"yarim_{tid}_{gi}_{'s' if sabahtir else 'o'}"
                )
                for h in hucreler:
                    model.AddImplication(h, yarim)
                gun_yarimlari.append(yarim)

            if not gun_yarimlari:
                continue
            yarimlar.extend(gun_yarimlari)
            gun = model.NewBoolVar(f"gun_{tid}_{gi}")
            for y in gun_yarimlari:
                model.AddImplication(y, gun)
            gun_degiskenleri.append(gun)

        if not yarimlar:
            continue

        if esnek:
            asim = model.NewIntVar(0, 2 * gun_sayisi, f"gunasim_{tid}")
            model.Add(asim >= sum(yarimlar) - sinir)
            model.Add(asim >= sum(gun_degiskenleri) - gun_tavani)
            asimlar[tid] = asim
        else:
            model.Add(sum(yarimlar) <= sinir)
            model.Add(sum(gun_degiskenleri) <= gun_tavani)

    return asimlar


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
