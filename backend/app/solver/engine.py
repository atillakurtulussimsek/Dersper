"""Ders programı üretici — Google OR-Tools CP-SAT.

Model blok tabanlıdır: her müfredat satırı, haftalık saatine göre bloklara
bölünür (örn. 5 saat, blok 2 → [2, 2, 1]). Her blok gün içinde ardışık ders
saatlerine yerleşir.

Sert kısıtlar (v1):
  1. Her müfredat satırı haftalık saatinin tamamını alır.
  2. Bir şube aynı anda tek derste olur. Birleşik ders (bir satırda birden
     fazla şube) tüm şubelerini aynı anda meşgul eder.
  3. Bir öğretmen aynı anda tek derste olur.
     "Aynı an"ın ölçütünü kurum seçer: ızgaranın satırı mı, gerçek saat
     aralığı mı (bkz. `app.cakisma` ve `Term.conflict_basis`).
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

Bunların üstünde bir de TERCİH vardır (kural değil): `bosluk_politikasi`.
"siki" öğretmenin gün içindeki boşluklarını en aza indirir, "bosluklu" tam
tersine boşluğu ödüllendirir, "ideal" hiç bakmaz. Ağırlığı kural cezalarının
çok altındadır — program kurulabilirlik uğruna tercihten vazgeçer, tersi olmaz.
"ideal" seçiliyken modele hiçbir amaç eklenmez; problem eskisi gibi saf
sağlanabilirlik problemi kalır ve aynı hızda çözülür.

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

from app import cakisma

# Gevşetilmiş modelde yerleşemeyen her ders saatinin bedeli.
CEZA_YERLESMEYEN = 1000
# Esnek kipte günlük sınırın her bir saatlik aşımının bedeli.
CEZA_GUNLUK_ASIM = 10
# Boşluk tercihinin ağırlığı. Kural ihlallerinin çok altında: boşluk bir
# TERCİHTİR, kural değil. Program kurulabilirlik uğruna boşluk tercihinden
# vazgeçilir, tersi olmaz.
AGIRLIK_BOSLUK = 1
# Esnek kipte bir öğretmenin bir günde ikinci binaya geçmesinin bedeli.
# Gün sınırı kadar ağır: ikisi de fiziksel/sözleşmesel bir engeli zorlar.
CEZA_BINA_GECISI = 40
# Esnek kipte öğretmenin gün sınırını her yarım günlük aşmasının bedeli.
# Günlük tekrar sınırından ağır: o pedagojik bir tercih, bu ise öğretmenle
# yapılmış bir anlaşma. Çözücü zorunlu kalmadıkça bu sınırı bozmamalı.
CEZA_GUN_SINIRI = 40
VARSAYILAN_SURE_SN = 30.0
# Varsayım çekirdeği (tanı kipi) için iş parçacığı sayısı. Tek iş parçacığı
# kesin çalışır ama büyük modelde süre yetmez; deneyle ayarlanır.
TANI_ISCI = 1


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
    # Gün başından beri dakika. Yalnızca "saat" çakışma ölçütünde okunur;
    # girilmemişse o satır yalnızca kendisiyle çakışır (bkz. app.cakisma).
    baslangic: int | None = None
    bitis: int | None = None


@dataclass(frozen=True)
class Lesson:
    """Çözücünün gördüğü haliyle bir müfredat satırı."""
    entry_id: int
    # Asıl şube; iletilerde bu ad geçer.
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
    # Dersi birlikte gören şubeler: (kimlik, ad) çiftleri, tanım sırasında.
    # Birleşik derste birden fazladır ve hepsi aynı anda meşgul olur. Boşsa
    # `section_id`/`section_name` tek başına geçerlidir.
    sections: tuple[tuple[int, str], ...] = ()
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
    # Öğretmen boşluklarına nasıl davranılacağı: "bosluklu" | "ideal" | "siki".
    # "ideal" hiçbir amaç eklemez — model saf sağlanabilirlik problemi kalır.
    bosluk_politikasi: str = "ideal"
    # Çakışma neye göre ölçülür: "ders_saati" (ızgara satırı) | "saat"
    # (gerçek aralık). Bkz. app.cakisma.
    cakisma_olcutu: str = cakisma.DERS_SAATI
    # Günlük ders tekrar sınırı, öğretmen gün sınırı ve bina kuralı
    # aşılabilsin mi? Aşım cezalandırılır, yasak değildir.
    esnek_gunluk: bool = False


@dataclass(frozen=True)
class Celisen:
    """Çelişkiye katılan, KULLANICININ DEĞİŞTİREBİLECEĞİ tek bir kısıt.

    `tur` arayüzün gruplaması için, `metin` ne olduğunu, `oneri` ne
    yapılacağını söyler. `tek_basina_yeterli`, yalnızca bunu değiştirmenin
    programı kurulabilir kılıp kılmadığıdır.
    """
    tur: str
    metin: str
    oneri: str
    # True: yalnız bunu değiştirmek yeter. False: yetmez. None: sınama süresi
    # yetmedi, bilinmiyor — "yetmez" demek yanlış olurdu.
    tek_basina_yeterli: bool | None = False


class _Kisitlar:
    """Kısıtları ya doğrudan ekler ya da tanı için varsayım anahtarıyla kuşatır.

    Tanı kipinde her kullanıcı-değiştirilebilir kısıt bir anahtarın arkasına
    alınır ve varsayım olarak sunulur; model çözümsüzse CP-SAT bu
    anahtarlardan hangilerinin birlikte çelişki ürettiğini söyler.

    Tanı kapalıyken hiçbir ek değişken kurulmaz — üretim yolu değişmez.
    """

    def __init__(self, model, tani: bool):
        self.model = model
        self.tani = tani
        self.anahtarlar: list = []
        self.etiketler: dict[int, Celisen] = {}

    def ekle(self, ifade, etiket: Celisen | None = None) -> None:
        if not self.tani or etiket is None:
            self.model.Add(ifade)
            return
        anahtar = self.model.NewBoolVar(f"varsayim_{len(self.anahtarlar)}")
        self.model.Add(ifade).OnlyEnforceIf(anahtar)
        self.anahtarlar.append(anahtar)
        self.etiketler[anahtar.Index()] = etiket

    def cozumle(self, solver) -> list[Celisen]:
        """Çözücünün bildirdiği çelişki çekirdeğini etiketlere çevirir."""
        cekirdek = solver.SufficientAssumptionsForInfeasibility()
        gorulen: list[Celisen] = []
        for i in cekirdek:
            etiket = self.etiketler.get(i)
            # Aynı etiket birden çok kısıttan gelebilir (örn. günlere yayılan
            # kurallar); tekrarları eleriz.
            if etiket is not None and etiket not in gorulen:
                gorulen.append(etiket)
        return gorulen


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
    # Çözümsüzlükte çelişen kısıtlar (yalnızca tanı kipinde dolar).
    celisenler: list[Celisen] = field(default_factory=list)
    # Esnek (günlük sınırı cezalı) model de çözümsüz olduğunu KANITLADI mı?
    # İkisi birden kanıtlıysa yeniden denemek hiçbir tohumla sonuç vermez.
    esnek_proven_infeasible: bool = False


def sube_ciftleri(lesson: Lesson) -> tuple[tuple[int, str], ...]:
    """Dersi gören şubeler, (kimlik, ad) olarak. Birleşik değilse tek eleman."""
    return lesson.sections or ((lesson.section_id, lesson.section_name),)


def subeleri(lesson: Lesson) -> frozenset[int]:
    """Dersi gören şube kimlikleri."""
    return frozenset(si for si, _ in sube_ciftleri(lesson))


def sube_etiketi(lesson: Lesson) -> str:
    """İletilerde geçen şube adı: birleşik derste "9-A + 9-B"."""
    return " + ".join(ad for _, ad in sube_ciftleri(lesson))


def _ders_adi(lesson: Lesson) -> str:
    return f"{sube_etiketi(lesson)} · {lesson.subject_name}"


def _yuk_etiketi(lesson: Lesson) -> Celisen:
    return Celisen(
        tur="yuk",
        metin=f"{_ders_adi(lesson)} haftada {lesson.weekly_hours} saat okutulmalı",
        oneri=f"{_ders_adi(lesson)} dersinin haftalık saatini azaltın",
    )


def _musaitlik_etiketi(lesson: Lesson) -> Celisen | None:
    """Dersi kısıtlayan kapalı saatler. Kapalı saat yoksa etiket de yok."""
    ogretmen = bool(lesson.blocked_period_ids)
    sube = bool(lesson.section_blocked_period_ids)
    if not ogretmen and not sube:
        return None
    if ogretmen and sube:
        metin = (f"{lesson.teacher_name} ve {sube_etiketi(lesson)} "
                 f"için kapatılmış saatler")
        oneri = (f"{lesson.teacher_name} ya da {sube_etiketi(lesson)} "
                 f"müsaitlik matrisinde birkaç saat açın")
    elif ogretmen:
        metin = f"{lesson.teacher_name} için kapatılmış saatler"
        oneri = f"{lesson.teacher_name} müsaitlik matrisinde birkaç saat açın"
    else:
        metin = f"{sube_etiketi(lesson)} için kapatılmış saatler"
        oneri = f"{sube_etiketi(lesson)} müsaitlik matrisinde birkaç saat açın"
    return Celisen(tur="musaitlik", metin=metin, oneri=oneri)


def _gunluk_etiketi(lesson: Lesson) -> Celisen:
    return Celisen(
        tur="gunluk_sinir",
        metin=(f"{_ders_adi(lesson)} günde en fazla "
               f"{lesson.max_per_day} saat olabilir"),
        oneri=f"{_ders_adi(lesson)} için günlük sınırı yükseltin",
    )


def _desen_etiketi(lesson: Lesson) -> Celisen:
    desen = "+".join(str(b) for b in lesson.blocks)
    return Celisen(
        tur="desen",
        metin=f"{_ders_adi(lesson)} dersinin dağılımı {desen}",
        oneri=(f"{_ders_adi(lesson)} dağılımını gevşetin "
               f"(örn. blokları tek saatlere bölün)"),
    )


def _gun_siniri_etiketi(teacher_id: int, ad: str, yarim_gun: int) -> Celisen:
    gun = f"{yarim_gun / 2:g}".replace(".", ",")
    return Celisen(
        tur="gun_siniri",
        metin=f"{ad} haftada en fazla {gun} gün okulda olabilir",
        oneri=f"{ad} için haftalık gün sınırını yükseltin",
    )


def _bina_etiketi(ad: str) -> Celisen:
    return Celisen(
        tur="bina",
        metin=f"{ad} bir günde tek binada ders verebilir",
        oneri="Binalar sayfasından bina geçişi kuralını kapatın",
    )


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

    esnek_kanit = False
    if data.esnek_gunluk:
        esnek = _calistir(data, gevsek=False, esnek_gunluk=True)
        if esnek.ok:
            return esnek
        esnek_kanit = esnek.status_name == "INFEASIBLE"

    gevsek = _calistir(data, gevsek=True)
    gevsek.proven_infeasible = sert.status_name == "INFEASIBLE"
    gevsek.esnek_proven_infeasible = esnek_kanit
    return gevsek


# Çekirdek büyükse hepsini tek tek sınamak pahalıya gelir; ilk birkaçı
# kullanıcıya zaten yeterli bir resim verir.
EN_FAZLA_ADAY = 6


def tani_butcesi(ders_sayisi: int) -> float:
    """Varsayım çekirdeği için süre: modelle büyür (en az 10, en çok 60 sn)."""
    return min(60.0, max(10.0, 0.5 * ders_sayisi))


# Bu kadar ders satırına kadar varsayım çekirdeği (kesin ve küçük liste)
# denenir; üstünde doğrudan silme yöntemine geçilir. Ölçüm: 227 satırlık
# okulda varsayımlı model 8 iş parçacığıyla 45 sn'de bile karar veremedi,
# düz model ise çözümsüzlüğü 2,6 sn'de kanıtladı.
KUCUK_MODEL = 60
# Silme yöntemindeki tek bir sınamanın süresi ve tüm çözümlemenin tavanı.
SINAMA_SN = 20.0
COZUMLEME_TAVANI_SN = 240.0


def etiket_gruplari(data: SolveInput) -> list[tuple[Celisen, frozenset[Celisen]]]:
    """Kullanıcı-değiştirilebilir kısıtları kaynağa göre öbekler.

    Her öğretmen ve her şube bir öbektir: o kaynağın derslerine ait yük,
    müsaitlik, günlük sınır ve dağılım etiketleri (+ öğretmende gün sınırı).
    Öbeğin başlığı, çözümlemede kullanıcıya gösterilecek `Celisen`'dir.
    En sıkışık kaynak (yük / açık saat) başa gelir: sınama sırası budur.
    """
    toplam = len(data.slots)
    ogretmen: dict[int, dict] = {}
    sube: dict[int, dict] = {}
    for l in data.lessons:
        etiketler = [_yuk_etiketi(l), _gunluk_etiketi(l), _desen_etiketi(l)]
        m = _musaitlik_etiketi(l)
        if m is not None:
            etiketler.append(m)
        o = ogretmen.setdefault(l.teacher_id, {
            "ad": l.teacher_name, "yuk": 0, "acik": toplam - len(l.blocked_period_ids),
            "etiketler": set(),
        })
        o["yuk"] += l.weekly_hours
        o["etiketler"].update(etiketler)
        for si, ad in sube_ciftleri(l):
            sb = sube.setdefault(si, {
                "ad": ad, "yuk": 0, "acik": toplam - len(l.section_blocked_period_ids),
                "etiketler": set(),
            })
            sb["yuk"] += l.weekly_hours
            sb["etiketler"].update(etiketler)
    for tid, yarim in data.ogretmen_yarim_gun.items():
        if tid in ogretmen:
            ogretmen[tid]["etiketler"].add(
                _gun_siniri_etiketi(tid, ogretmen[tid]["ad"], yarim))

    def oran(k: dict) -> float:
        return k["yuk"] / k["acik"] if k["acik"] else 9.9

    def pay_metni(k: dict) -> str:
        """Yükün açık saate göre durumu — uyarının asıl gerekçesi.

        "24 saat yük, 24 açık saat" tek başına çelişki gibi okunmaz; sorun
        boşluk payının sıfır olması: öğretmenler başka şubelerle çakışınca
        kaydıracak saat kalmıyor. Bunu açıkça söylemek gerekir.
        """
        pay = k["acik"] - k["yuk"]
        if k["acik"] == 0:
            return f"haftalık {k['yuk']} saat yükü var ama hiç açık saati yok"
        if pay <= 0:
            return (f"haftalık {k['yuk']} saat yükü {k['acik']} açık saate tam sığıyor, "
                    f"boşluk payı yok")
        return (f"haftalık {k['yuk']} saat yükü, {k['acik']} açık saat, yalnızca "
                f"{pay} saat pay")

    gruplar: list[tuple[float, Celisen, frozenset[Celisen]]] = []
    for k in ogretmen.values():
        gruplar.append((oran(k), Celisen(
            tur="ogretmen",
            metin=(f"{k['ad']} (öğretmen): {pay_metni(k)} — kısıtları kaldırılınca "
                   f"program kuruluyor"),
            oneri=(f"{k['ad']} için müsaitlik matrisinde birkaç saat açın, bir dersini "
                   f"başka öğretmene verin ya da gün sınırını yükseltin"),
        ), frozenset(k["etiketler"])))
    for k in sube.values():
        gruplar.append((oran(k), Celisen(
            tur="sube",
            metin=(f"{k['ad']} (şube): {pay_metni(k)} — kısıtları kaldırılınca "
                   f"program kuruluyor"),
            oneri=(f"{k['ad']} şubesinde bir dersi başka öğretmene verin, kapalı "
                   f"saatlerini azaltın ya da bir dersin haftalık saatini düşürün"),
        ), frozenset(k["etiketler"])))
    gruplar.sort(key=lambda g: -g[0])
    return [(baslik, kume) for _, baslik, kume in gruplar]


def _sinama_sonucu(sonuc: SolveOutput) -> bool | None:
    """Kısıt(lar) çıkınca program kuruldu mu? True / False / bilinmiyor."""
    if sonuc.ok:
        return True
    if sonuc.status_name == "INFEASIBLE":
        return False
    return None


def celiskiyi_bul(
    data: SolveInput,
    sure_sn: float | None = None,
    devam=None,
) -> list[Celisen]:
    """Program neden kurulamıyor? Çelişen kısıtları ve çözüm önerilerini döner.

    Küçük modelde (bkz. KUCUK_MODEL) varsayım çekirdeği: kullanıcının
    değiştirebileceği kısıtlar anahtarların arkasına alınır, CP-SAT hangilerinin
    BİRLİKTE çeliştiğini söyler; sonra her aday tek tek çıkarılıp sınanır.

    Büyük modelde bu yol tıkanıyor (anahtarlar ön işlemeyi zayıflatıyor, süre
    yetmiyor). Orada SİLME yöntemi: düz model çözümsüzlüğü hızla kanıtlıyorsa
    her öğretmenin ve her şubenin kısıtları sırayla çıkarılıp yeniden
    kanıtlanmaya çalışılır. Kanıt sürüyorsa o kaynak çelişkinin parçası
    değildir; program kurulursa tek başına o kaynak yeter; süre biterse
    "bilinmiyor" ama kuşkulu (listede kalır). Sınama sırası en sıkışık
    kaynaktan başlar; `devam()` yanlış dönerse (kullanıcı durdurdu) çözümleme
    olduğu yerde kesilir.
    """
    import time as _t

    devam = devam or (lambda: True)

    if len(data.lessons) <= KUCUK_MODEL:
        cekirdek_sn = sure_sn if sure_sn is not None else tani_butcesi(len(data.lessons))
        ilk = SolveInput(**{**data.__dict__, "time_limit_seconds": cekirdek_sn})
        sonuc = _calistir(ilk, gevsek=False, tani=True)
        if sonuc.celisenler:
            sinama_sn = min(60.0, cekirdek_sn)
            sonuclar: list[Celisen] = []
            for aday in sonuc.celisenler[:EN_FAZLA_ADAY]:
                if not devam():
                    break
                sinama = _calistir(
                    SolveInput(**{**data.__dict__, "time_limit_seconds": sinama_sn}),
                    gevsek=False, atlanan=aday,
                )
                sonuclar.append(Celisen(
                    tur=aday.tur, metin=aday.metin, oneri=aday.oneri,
                    tek_basina_yeterli=_sinama_sonucu(sinama),
                ))
            return sonuclar

    # Silme yöntemi. Önce düz modelin çözümsüzlüğü kanıtladığından emin ol;
    # kanıt yoksa (yalnız süre bitti) silmeyle bir şey söylenemez.
    baslangic = _t.monotonic()
    kanit = _calistir(SolveInput(**{**data.__dict__, "time_limit_seconds": SINAMA_SN}),
                      gevsek=False)
    if kanit.status_name != "INFEASIBLE":
        return []

    sonuclar = []
    for baslik, kume in etiket_gruplari(data):
        if not devam() or _t.monotonic() - baslangic > COZUMLEME_TAVANI_SN:
            break
        if len(sonuclar) >= EN_FAZLA_ADAY:
            break
        sinama = _calistir(
            SolveInput(**{**data.__dict__, "time_limit_seconds": SINAMA_SN}),
            gevsek=False, atlanan=kume,
        )
        yeter = _sinama_sonucu(sinama)
        if yeter is False:
            # Bu kaynak çıkınca da çözümsüz: çelişkinin parçası değil.
            continue
        sonuclar.append(Celisen(tur=baslik.tur, metin=baslik.metin,
                                oneri=baslik.oneri, tek_basina_yeterli=yeter))
    return sonuclar


def _calistir(
    data: SolveInput, *, gevsek: bool, esnek_gunluk: bool = False,
    tani: bool = False, atlanan: "Celisen | frozenset[Celisen] | None" = None,
) -> SolveOutput:
    """Modeli kurar ve çözer.

    `tani=True` iken kullanıcının değiştirebileceği kısıtlar varsayım
    anahtarlarının arkasına alınır; çözümsüzlükte hangilerinin çeliştiği
    `celisenler` alanında döner. `atlanan` verilirse o kısıt hiç kurulmaz —
    "yalnızca bunu değiştirsem yeter mi?" sorusunu sınamak için.
    """
    basla = _time.monotonic()
    slots = data.slots
    gunler = _gune_gore(slots)
    slot_by_period = {s.period_id: i for i, s in enumerate(slots)}

    model = cp_model.CpModel()
    kisit = _Kisitlar(model, tani)

    def gecerli(etiket: Celisen | None) -> bool:
        """Bu kısıt kurulacak mı? Sınamada bir etiket ya da bir etiket kümesi
        dışarıda bırakılır (küme: bir öğretmenin/şubenin bütün kısıtları)."""
        if atlanan is None:
            return True
        if isinstance(atlanan, frozenset):
            return etiket not in atlanan
        return etiket != atlanan

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

        musaitlik_etiketi = _musaitlik_etiketi(lesson)
        musaitlik_kurulacak = gecerli(musaitlik_etiketi)

        for bi, boy in enumerate(bloklar):
            secenekler: dict[int, cp_model.IntVar] = {}
            for gun_slotlari in gunler.values():
                for konum in range(len(gun_slotlari) - boy + 1):
                    pencere = gun_slotlari[konum:konum + boy]
                    if not _ardisik_mi(slots, pencere):
                        continue
                    kapali = any(slots[i].period_id in engelli for i in pencere)
                    # Üretimde kapalı pencere hiç kurulmaz. Tanıda kurulur ama
                    # anahtarla yasaklanır — müsaitlik de çelişkinin parçası
                    # olarak gösterilebilsin diye. Sınamada (müsaitlik dışarıda)
                    # pencere serbest bırakılır.
                    if kapali and musaitlik_kurulacak and not tani:
                        continue
                    v = model.NewBoolVar(f"b_{li}_{bi}_{pencere[0]}")
                    if kapali and musaitlik_kurulacak:
                        kisit.ekle(v == 0, musaitlik_etiketi)
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
                if not gevsek and gecerli(_yuk_etiketi(lesson)):
                    kisit.ekle(sum([]) == 1, _yuk_etiketi(lesson))
                continue
            if gevsek:
                model.Add(sum(secenekler.values()) <= 1)
            elif gecerli(_yuk_etiketi(lesson)):
                kisit.ekle(sum(secenekler.values()) == 1, _yuk_etiketi(lesson))
            else:
                # "Saati azaltsam kurulur mu?" sınaması: blok yerleşmek
                # zorunda değil. Sıfıra indirmeyi değil, AZALTMAYI sınar.
                model.Add(sum(secenekler.values()) <= 1)

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
            elif gecerli(_gunluk_etiketi(lesson)):
                kisit.ekle(sum(gunluk) <= lesson.max_per_day,
                           _gunluk_etiketi(lesson))

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
                if len(hucreler) > en_uzun_blok and gecerli(_desen_etiketi(lesson)):
                    kisit.ekle(sum(hucreler) <= en_uzun_blok,
                               _desen_etiketi(lesson))

    # (2) Şube çakışması
    es_zamanlilar = cakisma.gruplar(
        [cakisma.Aralik(s.day_index, s.baslangic, s.bitis) for s in slots],
        data.cakisma_olcutu,
    )
    _tekil_kaynak(model, data.lessons, dolu, es_zamanlilar, subeleri)
    # (3) Öğretmen çakışması
    _tekil_kaynak(model, data.lessons, dolu, es_zamanlilar,
                  lambda l: (l.teacher_id,))

    # (10) Öğretmen gün sınırı. Günlük sınır (kural 6) gibi gevşek modelde de
    # sert kalır: orada gevşetilen tek şey "her saat yerleşmeli" kuralıdır.
    # Aksi hâlde son çare model sınırı tamamen yok sayar ve anlaşmayı sessizce
    # bozan bir programı başarılı diye döndürürdü.
    gun_asimlari = _gun_siniri(model, data, dolu, gunler, slots,
                               esnek=esnek_gunluk, kisit=kisit, gecerli=gecerli)

    # (11) Bina kuralı: bir öğretmen bir günde tek binada ders verir.
    bina_asimlari = _bina_kurali(model, data, dolu, gunler, esnek=esnek_gunluk,
                                 kisit=kisit, gecerli=gecerli)

    # (12) Boşluk tercihi. Gevşek model yalnızca "kaç saat yerleşemedi"
    # sorusunu yanıtlar; oraya tercih eklemek raporu bozar ve yavaşlatır.
    bosluklar: list[cp_model.IntVar] = []
    if not gevsek and data.bosluk_politikasi in ("siki", "bosluklu"):
        bosluklar = _bosluklar(model, data, dolu, gunler)

    # (8) Kilitli yerleşimler
    for li, lesson in enumerate(data.lessons):
        for period_id in data.locked.get(lesson.entry_id, []):
            si = slot_by_period.get(period_id)
            if si is not None and (li, si) in dolu:
                model.Add(dolu[(li, si)] == 1)

    if gevsek:
        model.Minimize(sum(CEZA_YERLESMEYEN * v for v in yerlesmeyen.values()))
    elif asimlar or gun_asimlari or bina_asimlari or bosluklar:
        # Tek amaç işlevi: çözücü hangi kuralı bozacağını bedele göre seçer,
        # gerekmedikçe hiçbirini bozmaz. Boşluk terimi en hafif olan; işareti
        # tercihe göre değişir (sıkı: azalt, boşluklu: artır).
        bosluk_yonu = -1 if data.bosluk_politikasi == "bosluklu" else 1
        model.Minimize(
            sum(CEZA_GUNLUK_ASIM * v for v in asimlar.values())
            + sum(CEZA_GUN_SINIRI * v for v in gun_asimlari.values())
            + sum(CEZA_BINA_GECISI * v for v in bina_asimlari.values())
            + bosluk_yonu * AGIRLIK_BOSLUK * sum(bosluklar)
        )

    if tani and kisit.anahtarlar:
        model.AddAssumptions(kisit.anahtarlar)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = data.time_limit_seconds
    # Çelişki çekirdeği için iş parçacığı sayısı (bkz. TANI_ISCI).
    solver.parameters.num_workers = TANI_ISCI if tani else 8
    solver.parameters.random_seed = data.seed
    status = solver.Solve(model)
    gecen = _time.monotonic() - basla

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        celisenler: list[Celisen] = []
        if tani and status == cp_model.INFEASIBLE:
            celisenler = kisit.cozumle(solver)
        return SolveOutput(
            ok=False, placements=[], seconds=gecen, unplaced={},
            status_name=solver.StatusName(status), celisenler=celisenler,
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


def _bosluklar(
    model, data: SolveInput, dolu: dict, gunler: dict[int, list[int]],
) -> list[cp_model.IntVar]:
    """Öğretmenlerin gün içindeki boşluklarını sayan değişkenler.

    Boşluk: bir öğretmenin bir gündeki İLK ve SON dersi arasında kalan boş
    ders saati. Günün başındaki ve sonundaki boşluklar sayılmaz — öğretmen
    henüz gelmemiş ya da çoktan gitmiştir.

    Bir saatin boşluk olması üç koşula bağlı: o saat boş, ÖNCESİNDE ders var,
    SONRASINDA ders var. Öncesi/sonrası birikimli VEYA zinciriyle kurulur.

    Değişkenler yalnızca amacın ittiği yönde bağlanır:
      * "siki" boşluğu azaltmak ister → alt sınır yeter (gerçek boşlukta 1
        olmaya zorlanır), çözücü zaten küçültmeye çalışır.
      * "bosluklu" boşluğu artırmak ister → üst sınır yeter (boşluk olmayan
        yerde 1 olamaz), çözücü zaten büyütmeye çalışır.
    Tek yönü bağlamak modeli belirgin biçimde küçültüyor.
    """
    artir = data.bosluk_politikasi == "bosluklu"
    ogretmen_dersleri: dict[int, list[int]] = {}
    for li, lesson in enumerate(data.lessons):
        ogretmen_dersleri.setdefault(lesson.teacher_id, []).append(li)

    bosluklar: list[cp_model.IntVar] = []
    for tid, dersler in ogretmen_dersleri.items():
        for gi, gun_slotlari in gunler.items():
            # Öğretmenin o gün her saatte meşgul olup olmadığı. Kural 3
            # sayesinde aynı saatte en fazla bir dersi olabilir.
            mesgul: list[cp_model.IntVar] = []
            for si in gun_slotlari:
                hucreler = [dolu[(li, si)] for li in dersler if (li, si) in dolu]
                v = model.NewBoolVar(f"mesgul_{tid}_{gi}_{si}")
                if hucreler:
                    model.Add(v == sum(hucreler))
                else:
                    model.Add(v == 0)
                mesgul.append(v)

            n = len(mesgul)
            if n < 3:           # boşluk için en az üç saat gerekir
                continue

            # once[i]: i dahil, i'ye kadar herhangi bir saatte ders var mı
            once: list[cp_model.IntVar] = []
            for i in range(n):
                v = model.NewBoolVar(f"once_{tid}_{gi}_{i}")
                if i == 0:
                    model.Add(v == mesgul[0])
                else:
                    model.AddMaxEquality(v, [once[i - 1], mesgul[i]])
                once.append(v)

            # sonra[i]: i dahil, i'den sonra herhangi bir saatte ders var mı
            sonra: list[cp_model.IntVar | None] = [None] * n
            for i in range(n - 1, -1, -1):
                v = model.NewBoolVar(f"sonra_{tid}_{gi}_{i}")
                if i == n - 1:
                    model.Add(v == mesgul[i])
                else:
                    model.AddMaxEquality(v, [sonra[i + 1], mesgul[i]])
                sonra[i] = v

            for i in range(1, n - 1):
                b = model.NewBoolVar(f"bosluk_{tid}_{gi}_{i}")
                if artir:
                    model.Add(b <= once[i - 1])
                    model.Add(b <= sonra[i + 1])
                    model.Add(b + mesgul[i] <= 1)
                else:
                    model.Add(b >= once[i - 1] + sonra[i + 1] - mesgul[i] - 1)
                bosluklar.append(b)

    return bosluklar


def _bina_kurali(
    model, data: SolveInput, dolu: dict, gunler: dict[int, list[int]], *,
    esnek: bool, kisit=None, gecerli=None,
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
    adlar: dict[int, str] = {}
    for li, lesson in enumerate(data.lessons):
        if lesson.building_id is None:
            continue
        ogretmen_bina.setdefault((lesson.teacher_id, lesson.building_id), []).append(li)
        adlar[lesson.teacher_id] = lesson.teacher_name

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
                etiket = _bina_etiketi(adlar.get(tid, "Öğretmen"))
                if gecerli is None or gecerli(etiket):
                    if kisit is None:
                        model.Add(sum(gun_binalari) <= 1)
                    else:
                        kisit.ekle(sum(gun_binalari) <= 1, etiket)

    return asimlar


def _gun_siniri(
    model, data: SolveInput, dolu: dict, gunler: dict[int, list[int]],
    slots: list[Slot], *, esnek: bool, kisit=None, gecerli=None,
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
    adlar: dict[int, str] = {}
    for li, lesson in enumerate(data.lessons):
        ogretmen_dersleri.setdefault(lesson.teacher_id, []).append(li)
        adlar[lesson.teacher_id] = lesson.teacher_name

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
            etiket = _gun_siniri_etiketi(tid, adlar.get(tid, "Öğretmen"), sinir)
            if gecerli is None or gecerli(etiket):
                if kisit is None:
                    model.Add(sum(yarimlar) <= sinir)
                    model.Add(sum(gun_degiskenleri) <= gun_tavani)
                else:
                    kisit.ekle(sum(yarimlar) <= sinir, etiket)
                    kisit.ekle(sum(gun_degiskenleri) <= gun_tavani, etiket)

    return asimlar


def _tekil_kaynak(model, lessons, dolu, es_zamanlilar, anahtarlar) -> None:
    """Aynı kaynağı (şube ya da öğretmen) paylaşan dersler aynı anda olamaz.

    `anahtarlar` bir dersin hangi kaynakları tuttuğunu söyler; birleşik ders
    birden fazla şubeyi aynı anda meşgul ettiği için çoğuldur.

    `es_zamanlilar`, aynı ana denk gelen slot kümeleridir (bkz. app.cakisma).
    "ders_saati" ölçütünde her küme tek slottur ve kısıt eskisiyle birebir
    aynıdır; "saat" ölçütünde saatleri üst üste binen slotlar aynı kümeye düşer.

    Kaynağın tek dersi olsa bile küme taranır: "saat" ölçütünde tek bir dersin
    iki bloğu, ayrı ama kesişen iki satıra düşebilir.
    """
    kaynaklar: dict[int, list[int]] = {}
    for li, lesson in enumerate(lessons):
        for kimlik in anahtarlar(lesson):
            kaynaklar.setdefault(kimlik, []).append(li)

    for uyeler in kaynaklar.values():
        for kume in es_zamanlilar:
            cakisanlar = [
                dolu[(li, si)] for li in uyeler for si in kume if (li, si) in dolu
            ]
            if len(cakisanlar) > 1:
                model.AddAtMostOne(cakisanlar)
