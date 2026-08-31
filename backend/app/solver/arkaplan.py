"""Arka planda çalışan program üretimi.

Bir çalıştırma başlatıldığında iş bir arka plan iş parçacığına verilir ve
kullanıcı ekranı terk etse bile sürer. Program tam yerleşene kadar birbiri
ardına deneme yapılır; her deneme farklı bir arama tohumu ve kademeli olarak
artan bir süre sınırıyla çalışır.

Çözücü kısıtların çeliştiğini KANITLADIĞINDA başka tohum denemek sonuç vermez.
Kullanıcının tercihi denemeye devam etmek olduğu için iş durdurulmaz; bunun
yerine durum `proven_infeasible` ile işaretlenir (arayüz bunu açıkça yazar) ve
denemeler arası bekleme kademeli olarak açılır, böylece işlemci boşuna
yakılmaz.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app import surumler
from app.models import (
    Assignment, SolveRun, SolveStatus, Term, Timetable, TimetableStatus, VersionKind,
)
from app.solver.diagnose import rapor_olustur
from app.solver.engine import SolveInput, solve
from app.solver.loader import (
    dersleri_yukle, gun_sinirlarini_yukle, slotlari_yukle,
)

log = logging.getLogger("dersper.arkaplan")

# Deneme süresi kademeli artar: zor örneklerde uzun süre gerekir, kolaylarda
# ilk saniyeler yeter.
ILK_SURE_SN = 15.0
EN_UZUN_SURE_SN = 120.0
SURE_CARPANI = 1.25

# Denemeler arası bekleme. Çözümsüzlüğü kanıtlanmış işlerde kademeli açılır.
ARA_SN = 0.5
EN_UZUN_ARA_SN = 30.0

# Günlük ders tekrar sınırı ancak bu kadar deneme başarısız olduktan sonra
# esnetilir. Amaç: önce kuralına uyan bir program aramak, esnetmeye mecbur
# kalınca başvurmak.
KATI_DENEME_SAYISI = 3

# Çalışan işlerin durdurma bayrakları: run_id -> Event
_calisanlar: dict[int, threading.Event] = {}
_kilit = threading.Lock()


def calisiyor_mu(run_id: int) -> bool:
    with _kilit:
        return run_id in _calisanlar


def durdur(run_id: int) -> bool:
    """Çalışan işe durma sinyali gönderir. İş yoksa False döner."""
    with _kilit:
        olay = _calisanlar.get(run_id)
    if olay is None:
        return False
    olay.set()
    return True


def baslat(run_id: int, term_id: int) -> None:
    """İşi arka planda başlatır."""
    olay = threading.Event()
    with _kilit:
        _calisanlar[run_id] = olay
    threading.Thread(
        target=_dongu, args=(run_id, term_id, olay), name=f"cozucu-{run_id}", daemon=True
    ).start()


def _dongu(run_id: int, term_id: int, dur: threading.Event) -> None:
    """Tam yerleşim sağlanana ya da durdurulana kadar deneme yapar."""
    try:
        with SessionLocal() as db:
            donem = db.get(Term, term_id)
            run = db.get(SolveRun, run_id)
            program = db.get(Timetable, run.timetable_id)
            slots = slotlari_yukle(db, donem)
            lessons = dersleri_yukle(db, donem, program.section_ids)
            gun_sinirlari = gun_sinirlarini_yukle(db, donem)
            gereken = sum(l.weekly_hours for l in lessons)

            kilitli: dict[int, list[int]] = {}
            for a in db.scalars(
                select(Assignment).where(
                    Assignment.timetable_id == run.timetable_id,
                    Assignment.is_locked.is_(True),
                )
            ):
                kilitli.setdefault(a.curriculum_entry_id, []).append(a.period_id)

            run.required = gereken
            run.status = SolveStatus.CALISIYOR
            run.updated_at = _simdi()
            db.commit()

            if not slots or not lessons:
                _bitir(db, run_id, SolveStatus.HATA,
                       rapor_olustur(slots, lessons, {}, "VERI_YOK", 0.0,
                                     gun_sinirlari))
                return

            en_iyi: list[tuple[int, int]] = []
            en_iyi_yerlesen = -1
            en_iyi_eksik: dict[int, int] = {}
            son_rapor = None
            sure = ILK_SURE_SN
            ara = ARA_SN
            deneme = 0
            esnek = False
            baslangic = _simdi()

            while not dur.is_set():
                deneme += 1
                # Önce kurala uyan bir program ara; ancak birkaç deneme sonuç
                # vermezse ya da kısıtların çeliştiği kanıtlanırsa esnet.
                if deneme > KATI_DENEME_SAYISI:
                    esnek = True
                sonuc = solve(SolveInput(
                    slots=slots, lessons=lessons, locked=kilitli,
                    ogretmen_yarim_gun=gun_sinirlari,
                    time_limit_seconds=sure, seed=deneme, esnek_gunluk=esnek,
                ))
                if sonuc.proven_infeasible:
                    esnek = True
                yerlesen = len(sonuc.placements)
                if yerlesen > en_iyi_yerlesen:
                    en_iyi_yerlesen = yerlesen
                    en_iyi = sonuc.placements
                    en_iyi_eksik = sonuc.unplaced

                son_rapor = rapor_olustur(slots, lessons, sonuc.unplaced,
                                          sonuc.status_name, sonuc.seconds,
                                          gun_sinirlari)

                _ilerlemeyi_yaz(run_id, deneme, en_iyi_yerlesen, gereken,
                                sonuc.proven_infeasible, son_rapor, baslangic)

                if sonuc.ok:
                    _yerlesimleri_yaz(run_id, sonuc.placements, kilitli, gereken)
                    _bitir(db, run_id, SolveStatus.BASARILI, son_rapor, baslangic)
                    return

                # Kanıtlanmış çözümsüzlükte yeniden denemek sonuç vermez;
                # kullanıcı istediği için durmuyoruz ama boşuna dönmüyoruz.
                if sonuc.proven_infeasible:
                    ara = min(ara * 2, EN_UZUN_ARA_SN)
                else:
                    sure = min(sure * SURE_CARPANI, EN_UZUN_SURE_SN)
                    ara = ARA_SN

                if dur.wait(ara):
                    break

            # Durduruldu: o ana kadarki en iyi yerleşimi kaydet.
            if en_iyi:
                _yerlesimleri_yaz(run_id, en_iyi, kilitli, gereken)
            if son_rapor is None:
                son_rapor = rapor_olustur(slots, lessons, en_iyi_eksik, "DURDURULDU",
                                          0.0, gun_sinirlari)
            _bitir(db, run_id, SolveStatus.DURDURULDU, son_rapor, baslangic)
    except Exception:  # iş parçacığı sessizce ölmesin
        log.exception("Arka plan çözümü hata verdi (run_id=%s)", run_id)
        try:
            with SessionLocal() as db:
                _bitir(db, run_id, SolveStatus.HATA, None)
        except Exception:
            log.exception("Hata durumu yazılamadı (run_id=%s)", run_id)
    finally:
        with _kilit:
            _calisanlar.pop(run_id, None)


def _simdi() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ilerlemeyi_yaz(run_id: int, deneme: int, en_iyi: int, gereken: int,
                    kanitlandi: bool, rapor: dict, baslangic: datetime) -> None:
    """Her denemeden sonra sayaçları günceller — arayüz bunları gösterir."""
    with SessionLocal() as db:
        run = db.get(SolveRun, run_id)
        if run is None:
            return
        run.attempts = deneme
        run.best_placed = en_iyi
        run.required = gereken
        run.proven_infeasible = kanitlandi
        run.report = rapor
        run.updated_at = _simdi()
        run.seconds = (_simdi() - baslangic).total_seconds()
        db.commit()


def _yerlesimleri_yaz(run_id: int, yerlesim: list[tuple[int, int]],
                      kilitli: dict[int, list[int]], gereken: int) -> None:
    """Sonucu programa yazar. Yeni sonuç hazır olana kadar eskisi durur.

    Üretim de geçmişe bir sürüm bırakır: elle düzenlemelerle aynı zincirde
    dururlar, böylece "üretimden önceki hâle dön" mümkün olur.
    """
    with SessionLocal() as db:
        run = db.get(SolveRun, run_id)
        if run is None:
            return
        program = db.get(Timetable, run.timetable_id)
        # Üretimden ÖNCEKİ hâl de bir geri dönüş noktası olmalı.
        surumler.baslangici_guvence_al(db, program)

        for a in db.scalars(
            select(Assignment).where(Assignment.timetable_id == run.timetable_id)
        ):
            db.delete(a)
        db.flush()
        for entry_id, period_id in yerlesim:
            db.add(Assignment(
                timetable_id=run.timetable_id, curriculum_entry_id=entry_id,
                period_id=period_id, is_locked=period_id in kilitli.get(entry_id, []),
            ))
        db.flush()
        surumler.surum_yaz(
            db, program, VersionKind.URETIM,
            f"Üretim — {len(yerlesim)}/{gereken} ders saati yerleşti",
        )
        db.commit()


def _bitir(db, run_id: int, durum: SolveStatus, rapor: dict | None,
           baslangic: datetime | None = None) -> None:
    from app.ai import client as ai
    from app.models import AiSettings, Term

    with SessionLocal() as oturum:
        run = oturum.get(SolveRun, run_id)
        if run is None:
            return
        run.status = durum
        run.finished_at = _simdi()
        run.updated_at = run.finished_at
        if baslangic is not None:
            run.seconds = (run.finished_at - baslangic).total_seconds()
        if rapor is not None:
            run.report = rapor

        if durum is SolveStatus.BASARILI:
            program = oturum.get(Timetable, run.timetable_id)
            if program is not None and program.status is TimetableStatus.TASLAK:
                program.status = TimetableStatus.URETILDI
        elif rapor is not None:
            # Yapay zeka ayarı programın bağlı olduğu kurumdan gelir.
            ayar = oturum.scalar(
                select(AiSettings)
                .join(Term, Term.institution_id == AiSettings.institution_id)
                .join(Timetable, Timetable.term_id == Term.id)
                .where(Timetable.id == run.timetable_id)
            )
            try:
                run.ai_explanation = ai.cozumsuzluk_acikla(ayar, rapor)
            except ai.AiKapali:
                run.ai_explanation = None
            except Exception as e:  # sağlayıcı hatası işi bozmasın
                run.ai_explanation = f"Yapay zeka açıklaması alınamadı: {e}"
        oturum.commit()


def yarim_kalanlari_isaretle() -> None:
    """Uygulama yeniden başladığında, işi bitmemiş çalıştırmaları kapatır.

    İşler uygulama sürecinin içinde çalıştığı için yeniden başlatma onları
    öldürür; veritabanında 'çalışıyor' görünmeye devam etmemeliler.

    Şema henüz kurulmamışsa (ilk kurulum, erişilemeyen veritabanı) uygulama
    yine de açılır: bu temizlik zorunlu değildir.
    """
    try:
        with SessionLocal() as db:
            yarim = list(db.scalars(
                select(SolveRun).where(
                    SolveRun.status.in_([SolveStatus.CALISIYOR, SolveStatus.BEKLIYOR])
                )
            ))
            for run in yarim:
                run.status = SolveStatus.DURDURULDU
                run.finished_at = _simdi()
            if yarim:
                db.commit()
                log.info("Yeniden başlatma nedeniyle %d çalıştırma durduruldu.",
                         len(yarim))
    except Exception as e:
        log.warning(
            "Yarım kalan çalıştırmalar denetlenemedi (%s). Veritabanı şeması "
            "güncel mi? Uygulama yine de açılıyor.", e,
        )
