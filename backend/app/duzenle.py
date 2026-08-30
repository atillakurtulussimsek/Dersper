"""Ders programının elle düzenlenmesi.

Çözücünün ürettiği program son söz değildir; müdürün bildiği ama sisteme
girilmemiş nedenler olur. Bu modül elle yapılan her müdahalenin tek kural
kaynağıdır: taşıma, yer değiştirme, ızgaradan alma, geri koyma ve geri alma.

Üç ilke:

1. **İşlem birimi bloktur, saat değil.** "2+2" deseni istenmişken bir saati
   ayrı çekmek çözücünün asla üretmeyeceği bir programı elle oluşturmak olurdu.
   Bir hücreyi tutmak, o hücrenin içinde bulunduğu kesintisiz bloğu tutar.

2. **Elle yapılan da kurallara uyar.** Çözücünün uyduğu müsaitlik ve çakışma
   kuralları burada da geçerli. Uymayan bir bırakma reddedilir ve NEDENİ
   Türkçe söylenir. (Esnetilebilir olanlar — günlük sınır, öğretmenin gün
   sınırı — burada engel değildir; onlar uyarı olarak görünür.)

3. **Reddetmeden önce göster.** `hedefleri_degerlendir` her ders saati için
   "konabilir mi, konamazsa neden" bilgisini döndürür; arayüz sürükleme
   başlarken bunu sorar ve kullanıcı denemeden görür.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import bloklar
from app.models import (
    Assignment, Availability, CurriculumEntry, Day, Period, Section,
    SectionAvailability, Teacher, TeacherAvailability, Term, Timetable,
)

# Geri alma yığınında tutulacak en fazla adım. Amaç son birkaç hatayı geri
# almak; sınırsız geçmiş programın kendisinden büyük bir kayıt yığar.
GERI_ALMA_SINIRI = 25


@dataclass(frozen=True)
class Saat:
    """Dönemin bir ders saati, düzenleme için gereken alanlarıyla."""
    id: int
    gun_index: int
    period_index: int
    gun_adi: str
    ad: str
    ders_mi: bool          # teneffüs/öğle arası değil ve günü açık


def saatleri_oku(db: Session, donem: Term) -> dict[int, Saat]:
    """Dönemin ders saatleri. Kapalı günler ve teneffüsler de listede ama
    `ders_mi=False` ile — hedef denetiminde nedeni söyleyebilmek için."""
    saatler: dict[int, Saat] = {}
    for gun in db.scalars(
        select(Day).options(selectinload(Day.periods)).where(Day.term_id == donem.id)
    ):
        for p in gun.periods:
            saatler[p.id] = Saat(
                id=p.id,
                gun_index=gun.index,
                period_index=p.index,
                gun_adi=gun.name,
                ad=p.name,
                ders_mi=gun.is_active and not p.is_break,
            )
    return saatler


def _gun_dizisi(saatler: dict[int, Saat], gun_index: int) -> list[Saat]:
    """Bir günün ders saatleri, sırasıyla."""
    return sorted(
        (s for s in saatler.values() if s.gun_index == gun_index and s.ders_mi),
        key=lambda s: s.period_index,
    )


def hedef_dizisi(
    saatler: dict[int, Saat], baslangic: Saat, uzunluk: int
) -> list[Saat] | None:
    """`baslangic`tan itibaren `uzunluk` kadar KESİNTİSİZ ders saati.

    Teneffüs ya da günün sonu diziyi böler; blok bölünemeyeceği için böyle bir
    hedef geçersizdir ve None döner.
    """
    gun = _gun_dizisi(saatler, baslangic.gun_index)
    try:
        nerede = next(i for i, s in enumerate(gun) if s.id == baslangic.id)
    except StopIteration:
        return None
    dizi = gun[nerede:nerede + uzunluk]
    if len(dizi) < uzunluk:
        return None
    for onceki, sonraki in zip(dizi, dizi[1:]):
        if sonraki.period_index - onceki.period_index != 1:
            return None
    return dizi


def bloklari_cikar(
    atamalar: list[Assignment], saatler: dict[int, Saat]
) -> dict[int, list[Assignment]]:
    """Yerleşimleri bloklara ayırır: assignment_id -> bloğun tüm yerleşimleri.

    Blok, aynı müfredat satırının aynı gün içinde arka arkaya gelen
    saatleridir. Her yerleşim kendi bloğuna eşlenir, böylece hangi hücreye
    dokunulursa dokunulsun blok bulunur.
    """
    gunluk: dict[tuple[int, int], list[Assignment]] = defaultdict(list)
    for a in atamalar:
        saat = saatler.get(a.period_id)
        if saat is None:
            continue
        gunluk[(a.curriculum_entry_id, saat.gun_index)].append(a)

    sonuc: dict[int, list[Assignment]] = {}
    for grup in gunluk.values():
        grup.sort(key=lambda a: saatler[a.period_id].period_index)
        blok: list[Assignment] = []
        for a in grup:
            if blok and (saatler[a.period_id].period_index
                         - saatler[blok[-1].period_id].period_index) != 1:
                for uye in blok:
                    sonuc[uye.id] = blok
                blok = []
            blok.append(a)
        for uye in blok:
            sonuc[uye.id] = blok
    return sonuc


def _atamalari_oku(db: Session, timetable_id: int) -> list[Assignment]:
    return list(db.scalars(
        select(Assignment)
        .options(
            selectinload(Assignment.entry).selectinload(CurriculumEntry.section),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.teacher),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.subject),
        )
        .where(Assignment.timetable_id == timetable_id)
    ))


def _kapali_saatler(db: Session, donem: Term) -> tuple[dict[int, set[int]], dict[int, set[int]]]:
    """(öğretmen_id -> kapalı period kümesi, şube_id -> kapalı period kümesi)"""
    ogretmen: dict[int, set[int]] = defaultdict(set)
    for row in db.scalars(
        select(TeacherAvailability)
        .join(Teacher, Teacher.id == TeacherAvailability.teacher_id)
        .where(Teacher.term_id == donem.id,
               TeacherAvailability.state == Availability.UYGUN_DEGIL)
    ):
        ogretmen[row.teacher_id].add(row.period_id)

    sube: dict[int, set[int]] = defaultdict(set)
    for row in db.scalars(
        select(SectionAvailability)
        .join(Section, Section.id == SectionAvailability.section_id)
        .where(Section.term_id == donem.id,
               SectionAvailability.state == Availability.UYGUN_DEGIL)
    ):
        sube[row.section_id].add(row.period_id)
    return ogretmen, sube


class Duzenleyici:
    """Bir programın elle düzenlenmesi. Kuralları ve geri alma yığınını tutar."""

    def __init__(self, db: Session, program: Timetable, donem: Term):
        self.db = db
        self.program = program
        self.donem = donem
        self.saatler = saatleri_oku(db, donem)
        self.atamalar = _atamalari_oku(db, program.id)
        self.bloklar = bloklari_cikar(self.atamalar, self.saatler)
        self.ogretmen_kapali, self.sube_kapali = _kapali_saatler(db, donem)
        # period_id -> o saatteki yerleşimler
        self.doluluk: dict[int, list[Assignment]] = defaultdict(list)
        for a in self.atamalar:
            self.doluluk[a.period_id].append(a)

    # --- Denetimler ---

    def _saat(self, period_id: int) -> Saat:
        saat = self.saatler.get(period_id)
        if saat is None:
            # Başka bir dönemin/kurumun ders saati. Yalıtım burada başlar.
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ders saati bulunamadı.")
        return saat

    def _atama(self, assignment_id: int) -> Assignment:
        for a in self.atamalar:
            if a.id == assignment_id:
                return a
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yerleşim bulunamadı.")

    def engel(
        self, entry: CurriculumEntry, saat: Saat, yoksay: set[int]
    ) -> str | None:
        """Bu ders bu saate konabilir mi? Konamazsa Türkçe gerekçe döner.

        `yoksay`, taşınmakta olan yerleşimlerin kimlikleridir: bir bloğu kendi
        üstüne kaydırırken kendisiyle çakışmasın diye.
        """
        if not saat.ders_mi:
            return "Bu saate ders konmaz (teneffüs ya da kapalı gün)."
        if saat.id in self.ogretmen_kapali.get(entry.teacher_id, set()):
            return f"{entry.teacher.full_name} bu saatte müsait değil."
        if saat.id in self.sube_kapali.get(entry.section_id, set()):
            return f"{entry.section.name} şubesi bu saate kapalı."
        for diger in self.doluluk.get(saat.id, []):
            if diger.id in yoksay:
                continue
            if diger.entry.section_id == entry.section_id:
                return (f"{entry.section.name} şubesinin o saatte "
                        f"{diger.entry.subject.name} dersi var.")
            if diger.entry.teacher_id == entry.teacher_id:
                return (f"{entry.teacher.full_name} o saatte "
                        f"{diger.entry.section.name} şubesinde.")
        return None

    def hedefleri_degerlendir(
        self, entry: CurriculumEntry, uzunluk: int, yoksay: set[int]
    ) -> list[dict]:
        """Her ders saati için "buraya konabilir mi" değerlendirmesi.

        Arayüz sürükleme başlarken bunu alır; kullanıcı geçerli yerleri
        denemeden görür. Blok uzunluğu hesaba katılır: 2 saatlik blok günün son
        saatine konamaz.
        """
        sonuc: list[dict] = []
        for saat in sorted(self.saatler.values(),
                           key=lambda s: (s.gun_index, s.period_index)):
            if not saat.ders_mi:
                continue
            dizi = hedef_dizisi(self.saatler, saat, uzunluk)
            if dizi is None:
                sonuc.append({
                    "period_id": saat.id, "uygun": False,
                    "neden": f"{uzunluk} saatlik blok buraya sığmıyor "
                             f"(gün bitiyor ya da araya teneffüs giriyor).",
                })
                continue
            neden = next(
                (self.engel(entry, s, yoksay) for s in dizi
                 if self.engel(entry, s, yoksay) is not None),
                None,
            )
            sonuc.append({
                "period_id": saat.id,
                "uygun": neden is None,
                "neden": neden,
            })
        return sonuc

    # --- Geri alma ---

    def _anlik_goruntu(self, period_ids: list[int]) -> dict:
        """Verilen saatlerin O ANKİ içeriği. Geri alma bunu geri yazar."""
        icerik = [
            {"e": a.curriculum_entry_id, "p": a.period_id, "k": a.is_locked}
            for pid in period_ids
            for a in self.doluluk.get(pid, [])
        ]
        return {"periods": sorted(set(period_ids)), "icerik": icerik}

    def _adimi_kaydet(self, adim: dict) -> None:
        yigin = list(self.program.edit_undo or [])
        yigin.append(adim)
        self.program.edit_undo = yigin[-GERI_ALMA_SINIRI:]
        # Yeni bir düzenleme ileri alma zincirini kopartır.
        self.program.edit_redo = []

    def _adimi_uygula(self, adim: dict) -> dict:
        """Bir anlık görüntüyü geri yazar ve ÖNCEKİ hâli döndürür.

        Simetriktir: dönen değer öbür yığına konur, böylece geri alma ile ileri
        alma aynı işlemle yürür.
        """
        period_ids = list(adim["periods"])
        onceki = self._anlik_goruntu(period_ids)
        for pid in period_ids:
            for a in list(self.doluluk.get(pid, [])):
                self.db.delete(a)
        self.db.flush()
        for satir in adim["icerik"]:
            self.db.add(Assignment(
                timetable_id=self.program.id,
                curriculum_entry_id=satir["e"],
                period_id=satir["p"],
                is_locked=satir["k"],
            ))
        self.db.flush()
        return onceki

    def geri_al(self) -> None:
        yigin = list(self.program.edit_undo or [])
        if not yigin:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "Geri alınacak bir değişiklik yok.")
        adim = yigin.pop()
        onceki = self._adimi_uygula(adim)
        self.program.edit_undo = yigin
        self.program.edit_redo = list(self.program.edit_redo or []) + [onceki]
        self.db.commit()

    def ileri_al(self) -> None:
        yigin = list(self.program.edit_redo or [])
        if not yigin:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "İleri alınacak bir değişiklik yok.")
        adim = yigin.pop()
        onceki = self._adimi_uygula(adim)
        self.program.edit_redo = yigin
        self.program.edit_undo = list(self.program.edit_undo or []) + [onceki]
        self.db.commit()

    # --- İşlemler ---

    def tasi(self, assignment_id: int, hedef_period_id: int) -> None:
        """Bloğu taşır. Hedefte eşit uzunlukta tek blok varsa yer değiştirirler."""
        atama = self._atama(assignment_id)
        blok = self.bloklar[atama.id]
        if any(a.is_locked for a in blok):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Kilitli ders taşınamaz. Önce hücreye çift tıklayıp kilidi açın.",
            )

        baslangic = self._saat(hedef_period_id)
        dizi = hedef_dizisi(self.saatler, baslangic, len(blok))
        if dizi is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"{len(blok)} saatlik blok oraya sığmıyor: gün bitiyor ya da "
                f"araya teneffüs giriyor.",
            )

        kaynak_saatler = [self.saatler[a.period_id] for a in blok]
        if [s.id for s in kaynak_saatler] == [s.id for s in dizi]:
            return      # yerinde bırakıldı

        kendi = {a.id for a in blok}
        entry_on = blok[0].entry
        # Yer açması gerekenler yalnızca ÇAKIŞANLAR: bir ders saati okulun
        # tamamına ait, o saatte başka şubelerin dersleri de vardır ve onların
        # taşınmasına gerek yok. Engel olan, aynı şube ya da aynı öğretmendir.
        hedefteki: list[Assignment] = [
            a
            for s in dizi
            for a in self.doluluk.get(s.id, [])
            if a.id not in kendi
            and (a.entry.section_id == entry_on.section_id
                 or a.entry.teacher_id == entry_on.teacher_id)
        ]
        yer_degistiren: list[Assignment] = []
        if hedefteki:
            karsi_bloklar = {id(self.bloklar[a.id]): self.bloklar[a.id] for a in hedefteki}
            if len(karsi_bloklar) > 1:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Hedefte birden fazla ders çakışıyor; yer değiştirme "
                    "yapılamıyor. Önce oradaki derslerden birini ızgaradan alın.",
                )
            yer_degistiren = next(iter(karsi_bloklar.values()))
            if any(a.is_locked for a in yer_degistiren):
                raise HTTPException(status.HTTP_409_CONFLICT,
                                    "Hedefteki ders kilitli; yeri değiştirilemez.")
            if len(yer_degistiren) != len(blok):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Yer değiştirme yalnızca eşit uzunlukta bloklar arasında "
                    f"yapılabilir: taşınan {len(blok)} saat, hedefteki "
                    f"{len(yer_degistiren)} saat. Önce birini ızgaradan alın.",
                )

        yoksay = kendi | {a.id for a in yer_degistiren}
        for saat in dizi:
            neden = self.engel(entry_on, saat, yoksay)
            if neden:
                raise HTTPException(status.HTTP_409_CONFLICT, neden)

        if yer_degistiren:
            karsi_entry = yer_degistiren[0].entry
            for saat in kaynak_saatler:
                neden = self.engel(karsi_entry, saat, yoksay)
                if neden:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        f"Yer değiştirilemiyor — {karsi_entry.subject.name} dersi "
                        f"karşı tarafa konamıyor: {neden}",
                    )

        etkilenen = [s.id for s in kaynak_saatler] + [s.id for s in dizi]
        self._adimi_kaydet(self._anlik_goruntu(etkilenen))

        # Sıra önemli: önce hepsi geçici olarak boşaltılmış sayılır, sonra yazılır.
        yeni_yer = {a.id: dizi[i].id for i, a in enumerate(blok)}
        if yer_degistiren:
            yer_degistiren.sort(key=lambda a: self.saatler[a.period_id].period_index)
            for i, a in enumerate(yer_degistiren):
                yeni_yer[a.id] = kaynak_saatler[i].id
        for a in blok + yer_degistiren:
            a.period_id = yeni_yer[a.id]
        self.db.commit()

    def izgaradan_al(self, assignment_id: int) -> None:
        """Bloğu ızgaradan çıkarır; saatleri bekleyenler rafına düşer."""
        atama = self._atama(assignment_id)
        blok = self.bloklar[atama.id]
        if any(a.is_locked for a in blok):
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "Kilitli ders ızgaradan alınamaz. Önce kilidi açın.")

        etkilenen = [a.period_id for a in blok]
        self._adimi_kaydet(self._anlik_goruntu(etkilenen))
        for a in blok:
            self.db.delete(a)
        self.db.commit()

    def yerlestir(self, entry_id: int, hedef_period_id: int, uzunluk: int) -> None:
        """Bekleyen saatlerden `uzunluk` kadarını ızgaraya koyar."""
        entry = self._mufredat_satiri(entry_id)
        bekleyen = self.bekleyenler().get(entry_id, [])
        if uzunluk not in bekleyen:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Bu ders için {uzunluk} saatlik bekleyen blok yok.",
            )

        baslangic = self._saat(hedef_period_id)
        dizi = hedef_dizisi(self.saatler, baslangic, uzunluk)
        if dizi is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"{uzunluk} saatlik blok oraya sığmıyor: gün bitiyor ya da "
                f"araya teneffüs giriyor.",
            )
        for saat in dizi:
            neden = self.engel(entry, saat, set())
            if neden:
                raise HTTPException(status.HTTP_409_CONFLICT, neden)

        etkilenen = [s.id for s in dizi]
        self._adimi_kaydet(self._anlik_goruntu(etkilenen))
        for saat in dizi:
            self.db.add(Assignment(
                timetable_id=self.program.id,
                curriculum_entry_id=entry_id,
                period_id=saat.id,
            ))
        self.db.commit()

    def _mufredat_satiri(self, entry_id: int) -> CurriculumEntry:
        entry = self.db.scalar(
            select(CurriculumEntry)
            .join(Section, Section.id == CurriculumEntry.section_id)
            .options(
                selectinload(CurriculumEntry.section),
                selectinload(CurriculumEntry.teacher),
                selectinload(CurriculumEntry.subject),
            )
            .where(CurriculumEntry.id == entry_id,
                   CurriculumEntry.deleted_at.is_(None),
                   Section.term_id == self.donem.id)
        )
        if entry is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ders ataması bulunamadı.")
        return entry

    # --- Bekleyenler ---

    def bekleyenler(self) -> dict[int, list[int]]:
        """müfredat satırı -> yerleşmemiş blok uzunlukları.

        İstenen blok deseninden yerleşmiş bloklar düşülür. Elle düzenleme
        deseni bozmuş olabilir (örn. "2+2" isterken 1+1+2 yerleşmiş); o durumda
        kalan saatler tek saatlik bloklar olarak bekler — uydurma bir desen
        dayatmaktansa gerçeği söylemek yeğdir.
        """
        yerlesen: dict[int, list[int]] = defaultdict(list)
        gorulen: set[int] = set()
        for a in self.atamalar:
            blok = self.bloklar.get(a.id)
            if blok is None or blok[0].id in gorulen:
                continue
            gorulen.add(blok[0].id)
            yerlesen[a.curriculum_entry_id].append(len(blok))

        sonuc: dict[int, list[int]] = {}
        for entry in self._donemin_satirlari():
            istenen = sorted(bloklar.coz(entry.block_pattern, entry.weekly_hours),
                             reverse=True)
            kalan_bloklar = list(istenen)
            for boy in sorted(yerlesen.get(entry.id, []), reverse=True):
                if boy in kalan_bloklar:
                    kalan_bloklar.remove(boy)
                else:
                    # Desene uymayan bir blok yerleşmiş: saat saat düş.
                    dusulecek = boy
                    while dusulecek > 0 and kalan_bloklar:
                        en_buyuk = max(kalan_bloklar)
                        kalan_bloklar.remove(en_buyuk)
                        if en_buyuk > dusulecek:
                            kalan_bloklar.extend([1] * (en_buyuk - dusulecek))
                        dusulecek -= min(en_buyuk, dusulecek)
            if kalan_bloklar:
                sonuc[entry.id] = sorted(kalan_bloklar, reverse=True)
        return sonuc

    def _donemin_satirlari(self) -> list[CurriculumEntry]:
        sorgu = (
            select(CurriculumEntry)
            .join(Section, Section.id == CurriculumEntry.section_id)
            .options(
                selectinload(CurriculumEntry.section),
                selectinload(CurriculumEntry.teacher),
                selectinload(CurriculumEntry.subject),
            )
            .where(Section.term_id == self.donem.id,
                   CurriculumEntry.deleted_at.is_(None))
        )
        if self.program.section_ids is not None:
            sorgu = sorgu.where(CurriculumEntry.section_id.in_(self.program.section_ids))
        return list(self.db.scalars(sorgu))

    def bekleyen_listesi(self) -> list[dict]:
        """Arayüzün rafta gösterdiği hazır liste."""
        satirlar = {e.id: e for e in self._donemin_satirlari()}
        liste: list[dict] = []
        for entry_id, boylar in self.bekleyenler().items():
            e = satirlar.get(entry_id)
            if e is None or not e.section.is_active or not e.teacher.is_active:
                continue
            for boy in boylar:
                liste.append({
                    "curriculum_entry_id": e.id,
                    "uzunluk": boy,
                    "section_name": e.section.name,
                    "subject_name": e.subject.name,
                    "subject_color": e.subject.color,
                    "teacher_name": e.teacher.full_name,
                })
        liste.sort(key=lambda x: (x["section_name"], x["subject_name"], -x["uzunluk"]))
        return liste
