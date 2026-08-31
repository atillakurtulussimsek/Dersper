"""Ders programı: üretim, ızgara görünümü, elle düzenleme, yayınlama."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import aktif_donem, current_user
from app.models import (
    Assignment, CurriculumEntry, Day, Period, Section, SolveRun, SolveStatus, Term,
    Timetable, TimetableStatus, TimetableVersion, VersionKind,
)
from app import surumler
from app.duzenle import Duzenleyici
from app.schemas import (
    AssignmentMove, GridCell, PendingOut, PlaceIn, SolveRunOut, TargetOut,
    TimetableGrid, TimetableIn, TimetableOut, TimetableUpdate, VersionOut,
    WarningIgnoreIn, WarningOut,
)
from app.uyarilar import uyarilari_hesapla
from app.solver import arkaplan

router = APIRouter(prefix="/timetables", tags=["ders programı"],
                   dependencies=[Depends(current_user)])


def _programi_getir(db: Session, timetable_id: int, donem: Term) -> Timetable:
    t = db.get(Timetable, timetable_id)
    if t is None or t.is_deleted or t.term_id != donem.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ders programı bulunamadı.")
    return t


def izgara_hucreleri(db: Session, timetable_id: int) -> list[GridCell]:
    """Arayüzün doğrudan çizebileceği hücre listesi."""
    period_bilgi = {
        p.id: (d.index, p.index)
        for d in db.scalars(select(Day).options(selectinload(Day.periods)))
        for p in d.periods
    }

    atamalar = db.scalars(
        select(Assignment)
        .options(
            selectinload(Assignment.entry).selectinload(CurriculumEntry.section),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.subject),
            selectinload(Assignment.entry).selectinload(CurriculumEntry.teacher),
        )
        .where(Assignment.timetable_id == timetable_id)
    )
    hucreler: list[GridCell] = []
    for a in atamalar:
        konum = period_bilgi.get(a.period_id)
        if konum is None:
            continue
        gun_index, ders_index = konum
        hucreler.append(GridCell(
            assignment_id=a.id,
            period_id=a.period_id,
            day_index=gun_index,
            period_index=ders_index,
            section_id=a.entry.section_id,
            section_name=a.entry.section.name,
            subject_name=a.entry.subject.name,
            subject_short=a.entry.subject.short_code,
            subject_color=a.entry.subject.color,
            teacher_id=a.entry.teacher_id,
            teacher_name=a.entry.teacher.full_name,
            teacher_short=a.entry.teacher.short_code,
            is_locked=a.is_locked,
        ))
    return hucreler


@router.get("", response_model=list[TimetableOut])
def programlar(
    db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[Timetable]:
    return list(db.scalars(
        select(Timetable)
        .where(Timetable.term_id == donem.id, Timetable.deleted_at.is_(None))
        .order_by(Timetable.created_at.desc())
    ))


@router.post("", response_model=TimetableOut, status_code=status.HTTP_201_CREATED)
def program_olustur(
    payload: TimetableIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Timetable:
    secilenler: list[int] | None = None
    if payload.section_ids is not None:
        # Sıra korunarak tekilleştir, dönemin şubeleriyle doğrula.
        istenen = list(dict.fromkeys(payload.section_ids))
        if not istenen:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                "En az bir şube seçilmeli.")
        gecerli = set(db.scalars(
            select(Section.id).where(
                Section.term_id == donem.id, Section.deleted_at.is_(None)
            )
        ))
        bilinmeyen = [i for i in istenen if i not in gecerli]
        if bilinmeyen:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                "Seçilen şubelerden bazıları bu dönemde yok.")
        # Tüm şubeler seçildiyse kayıt "hepsi" olarak tutulur; sonradan
        # eklenen şubeler de programa girer.
        secilenler = None if len(istenen) == len(gecerli) else istenen

    t = Timetable(term_id=donem.id, name=payload.name, section_ids=secilenler,
                  gap_policy=payload.gap_policy)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.patch("/{timetable_id}", response_model=TimetableOut)
def program_guncelle(
    timetable_id: int,
    payload: TimetableUpdate,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Timetable:
    """Adı ya da boşluk tercihini değiştirir. Tercih bir sonraki üretimde geçerli
    olur; yerleşmiş programı kendiliğinden değiştirmez."""
    t = _programi_getir(db, timetable_id, donem)
    if payload.name is not None:
        t.name = payload.name
    if payload.gap_policy is not None:
        t.gap_policy = payload.gap_policy
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{timetable_id}", status_code=status.HTTP_204_NO_CONTENT)
def program_sil(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
):
    """Yumuşak silme: program gizlenir, yerleşimleri saklı kalır."""
    t = _programi_getir(db, timetable_id, donem)
    t.deleted_at = datetime.now(timezone.utc)
    t.public_token = None
    db.commit()


@router.get("/{timetable_id}/grid", response_model=TimetableGrid)
def izgara(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> TimetableGrid:
    t = _programi_getir(db, timetable_id, donem)
    return _izgara(db, t)


@router.post("/{timetable_id}/solve", response_model=SolveRunOut,
             status_code=status.HTTP_202_ACCEPTED)
def uret(
    timetable_id: int,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> SolveRun:
    """Program üretimini arka planda başlatır ve hemen döner.

    Üretim, tam yerleşim sağlanana ya da durdurulana kadar arka planda deneme
    yapmayı sürdürür; ilerleme `/runs/active` ucundan izlenir.
    """
    t = _programi_getir(db, timetable_id, donem)

    calisan = db.scalar(
        select(SolveRun)
        .where(SolveRun.timetable_id == t.id,
               SolveRun.status.in_([SolveStatus.BEKLIYOR, SolveStatus.CALISIYOR]))
        .limit(1)
    )
    if calisan is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Bu program için zaten bir üretim çalışıyor. Önce onu durdurun.",
        )

    run = SolveRun(timetable_id=t.id, status=SolveStatus.BEKLIYOR)
    db.add(run)
    db.commit()
    db.refresh(run)

    arkaplan.baslat(run.id, donem.id)
    return run


@router.get("/{timetable_id}/runs/active", response_model=SolveRunOut | None)
def calisan_uretim(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> SolveRun | None:
    """Sürmekte olan üretim; yoksa null. Arayüz bunu düzenli aralıklarla sorar."""
    _programi_getir(db, timetable_id, donem)
    db.expire_all()
    return db.scalar(
        select(SolveRun)
        .where(SolveRun.timetable_id == timetable_id,
               SolveRun.status.in_([SolveStatus.BEKLIYOR, SolveStatus.CALISIYOR]))
        .order_by(SolveRun.id.desc())
        .limit(1)
    )


@router.post("/{timetable_id}/runs/{run_id}/stop", response_model=SolveRunOut)
def uretimi_durdur(
    timetable_id: int,
    run_id: int,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> SolveRun:
    """Çalışan üretimi durdurur; o ana kadarki en iyi yerleşim kaydedilir."""
    _programi_getir(db, timetable_id, donem)
    run = db.get(SolveRun, run_id)
    if run is None or run.timetable_id != timetable_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Çalıştırma bulunamadı.")

    run.stop_requested = True
    db.commit()
    if not arkaplan.durdur(run.id) and run.status in (
        SolveStatus.BEKLIYOR, SolveStatus.CALISIYOR
    ):
        # İş parçacığı yok (örneğin uygulama yeniden başlamış): kaydı kapat.
        run.status = SolveStatus.DURDURULDU
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
    db.refresh(run)
    return run


@router.get("/{timetable_id}/runs", response_model=list[SolveRunOut])
def denemeler(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[SolveRun]:
    _programi_getir(db, timetable_id, donem)
    return list(db.scalars(
        select(SolveRun)
        .where(SolveRun.timetable_id == timetable_id)
        .order_by(SolveRun.started_at.desc())
    ))


def _izgara(db: Session, t: Timetable) -> TimetableGrid:
    simdiki = surumler.gecerli_surum(db, t)
    return TimetableGrid(
        timetable=TimetableOut.model_validate(t),
        cells=izgara_hucreleri(db, t.id),
        can_undo=surumler.onceki_surum(db, t) is not None,
        can_redo=surumler.sonraki_surum(db, t) is not None,
        version=simdiki.number if simdiki else None,
    )


@router.patch("/{timetable_id}/assignments/{assignment_id}", response_model=TimetableGrid)
def dersi_tasi(
    timetable_id: int,
    assignment_id: int,
    payload: AssignmentMove,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> TimetableGrid:
    """Elle sürükle-bırak.

    Blok bütün taşınır; hedefte eşit uzunlukta tek blok varsa yer değiştirirler.
    Kurallar `app.duzenle` içinde, çözücüyle aynı yerde tanımlı.
    """
    t = _programi_getir(db, timetable_id, donem)
    Duzenleyici(db, t, donem).tasi(assignment_id, payload.period_id)
    return _izgara(db, t)


@router.post("/{timetable_id}/assignments/{assignment_id}/unplace",
             response_model=TimetableGrid)
def izgaradan_al(
    timetable_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> TimetableGrid:
    """Bloğu ızgaradan çıkarır; saatleri bekleyenler rafına düşer."""
    t = _programi_getir(db, timetable_id, donem)
    Duzenleyici(db, t, donem).izgaradan_al(assignment_id)
    return _izgara(db, t)


@router.post("/{timetable_id}/place", response_model=TimetableGrid)
def yerlestir(
    timetable_id: int,
    payload: PlaceIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> TimetableGrid:
    """Bekleyen bir bloğu ızgaraya koyar."""
    t = _programi_getir(db, timetable_id, donem)
    Duzenleyici(db, t, donem).yerlestir(
        payload.curriculum_entry_id, payload.period_id, payload.uzunluk
    )
    return _izgara(db, t)


@router.get("/{timetable_id}/pending", response_model=list[PendingOut])
def bekleyenler(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[dict]:
    """Yerleşmemiş ders blokları — çözücünün koyamadıkları ve elle alınanlar."""
    t = _programi_getir(db, timetable_id, donem)
    return Duzenleyici(db, t, donem).bekleyen_listesi()


@router.get("/{timetable_id}/targets", response_model=list[TargetOut])
def hedefler(
    timetable_id: int,
    assignment_id: int | None = None,
    curriculum_entry_id: int | None = None,
    uzunluk: int = 1,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> list[dict]:
    """Sürüklenen ders nereye konabilir? Arayüz sürükleme başlarken sorar.

    Ya taşınan bir yerleşim (`assignment_id`) ya da raftan gelen bir blok
    (`curriculum_entry_id` + `uzunluk`) sorulur.
    """
    t = _programi_getir(db, timetable_id, donem)
    d = Duzenleyici(db, t, donem)
    if assignment_id is not None:
        atama = d._atama(assignment_id)
        blok = d.bloklar[atama.id]
        return d.hedefleri_degerlendir(
            atama.entry, len(blok), {a.id for a in blok}
        )
    if curriculum_entry_id is not None:
        entry = d._mufredat_satiri(curriculum_entry_id)
        return d.hedefleri_degerlendir(entry, uzunluk, set())
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "assignment_id ya da curriculum_entry_id gerekli.")


@router.post("/{timetable_id}/undo", response_model=TimetableGrid)
def geri_al(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> TimetableGrid:
    """Bir önceki sürüme döner. Sonraki sürümler silinmez, ileri alınabilir."""
    t = _programi_getir(db, timetable_id, donem)
    surumler.geri_al(db, t)
    return _izgara(db, t)


@router.post("/{timetable_id}/redo", response_model=TimetableGrid)
def ileri_al(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> TimetableGrid:
    t = _programi_getir(db, timetable_id, donem)
    surumler.ileri_al(db, t)
    return _izgara(db, t)


@router.get("/{timetable_id}/versions", response_model=list[VersionOut])
def surumler_listesi(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[TimetableVersion]:
    """Programın sürüm geçmişi, en yeniden eskiye."""
    t = _programi_getir(db, timetable_id, donem)
    return list(db.scalars(
        select(TimetableVersion)
        .where(TimetableVersion.timetable_id == t.id)
        .order_by(TimetableVersion.number.desc())
    ))


@router.post("/{timetable_id}/versions/{number}/restore", response_model=TimetableGrid)
def surume_don(
    timetable_id: int,
    number: int,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> TimetableGrid:
    """Seçilen sürüme döner. Sonraki sürümler silinmez; geçmişte dururlar."""
    t = _programi_getir(db, timetable_id, donem)
    surumler.geri_yukle(db, t, number)
    return _izgara(db, t)


@router.post("/{timetable_id}/assignments/{assignment_id}/lock",
             response_model=TimetableGrid)
def kilidi_degistir(
    timetable_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> TimetableGrid:
    t = _programi_getir(db, timetable_id, donem)
    a = db.get(Assignment, assignment_id)
    if a is None or a.timetable_id != t.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Yerleşim bulunamadı.")
    surumler.baslangici_guvence_al(db, t)
    a.is_locked = not a.is_locked
    db.flush()
    entry = a.entry
    surumler.surum_yaz(
        db, t, VersionKind.ELLE,
        f"{entry.subject.name} · {entry.section.name} "
        f"{'kilitlendi' if a.is_locked else 'kilidi açıldı'}",
    )
    db.commit()
    return _izgara(db, t)


@router.get("/{timetable_id}/warnings", response_model=list[WarningOut])
def uyarilar(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> list[dict]:
    """Yerleşimdeki uyarılar. Her istekte o anki programdan hesaplanır."""
    t = _programi_getir(db, timetable_id, donem)
    return uyarilari_hesapla(db, t)


@router.post("/{timetable_id}/warnings/ignore", response_model=list[WarningOut])
def uyariyi_gizle(
    timetable_id: int,
    payload: WarningIgnoreIn,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> list[dict]:
    """Uyarıyı bu program için kalıcı olarak gizler."""
    t = _programi_getir(db, timetable_id, donem)
    gizlenen = list(t.ignored_warnings or [])
    if payload.key not in gizlenen:
        gizlenen.append(payload.key)
        t.ignored_warnings = gizlenen
        db.commit()
    return uyarilari_hesapla(db, t)


@router.delete("/{timetable_id}/warnings/ignore/{key}", response_model=list[WarningOut])
def uyariyi_geri_getir(
    timetable_id: int,
    key: str,
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> list[dict]:
    t = _programi_getir(db, timetable_id, donem)
    gizlenen = [k for k in (t.ignored_warnings or []) if k != key]
    t.ignored_warnings = gizlenen
    db.commit()
    return uyarilari_hesapla(db, t)


@router.post("/{timetable_id}/publish", response_model=TimetableOut)
def yayinla(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> Timetable:
    """Herkese açık, girişsiz görüntülenebilen bir bağlantı üretir."""
    t = _programi_getir(db, timetable_id, donem)
    t.public_token = t.public_token or secrets.token_urlsafe(16)
    t.status = TimetableStatus.YAYINDA
    db.commit()
    db.refresh(t)
    return t


@router.post("/{timetable_id}/unpublish", response_model=TimetableOut)
def yayindan_kaldir(
    timetable_id: int, db: Session = Depends(get_db), donem: Term = Depends(aktif_donem)
) -> Timetable:
    t = _programi_getir(db, timetable_id, donem)
    t.public_token = None
    t.status = TimetableStatus.URETILDI
    db.commit()
    db.refresh(t)
    return t
