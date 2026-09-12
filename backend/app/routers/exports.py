"""Çıktı: sınıf / öğretmen bazında HTML, PDF ve Excel."""
from __future__ import annotations

import io
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import aktif_donem, current_user
from app.models import (
    Availability, Day, Institution, Section, SectionAvailability, Teacher,
    TeacherAvailability, Term, Timetable,
)
from app import siralama
from app.routers.timetables import izgara_hucreleri

router = APIRouter(prefix="/timetables/{timetable_id}/export", tags=["çıktı"],
                   dependencies=[Depends(current_user)])

BAKIS = {"sube": "Şube", "ogretmen": "Öğretmen"}
DUZEN = {"ayri": "Ayrı sayfalar", "carsaf": "Çarşaf liste"}


def _ders_indexleri(gun: Day) -> list[int]:
    """Günün ders saati dizinleri, sırayla. Teneffüs ve öğle arası çıktıda yer almaz:
    ders programı ders saatlerini gösterir, aralar satır/sütun değildir."""
    return sorted(p.index for p in gun.periods if not p.is_break)


def _izgara_yapisi(db: Session, donem: Term) -> tuple[list[Day], list[int]]:
    """Dönemin aktif günleri ve haftada en az bir günde ders olan dizinler."""
    gunler = [
        g for g in db.scalars(
            select(Day).options(selectinload(Day.periods))
            .where(Day.term_id == donem.id, Day.is_active.is_(True))
            .order_by(Day.index)
        )
    ]
    return gunler, sorted({di for g in gunler for di in _ders_indexleri(g)})


def _tablolar(db: Session, timetable_id: int, bakis: str,
              kayit: str | None = None) -> dict[str, dict]:
    """Anahtar (şube adı ya da öğretmen adı) -> {(gun, ders): hücre}

    Şube tabloları kurumun seçtiği şube sırasıyla dizilir (bkz. app.siralama);
    ekrandaki şeritler ve çarşafla aynı sıra. Öğretmenler ada göre.
    """
    hucreler = izgara_hucreleri(db, timetable_id)
    gruplar: dict[str, dict] = defaultdict(dict)
    for h in hucreler:
        # Birleşik ders her şubesinin tablosunda görünür.
        anahtarlar = (h.section_names or [h.section_name]) if bakis == "sube" else [h.teacher_name]
        for anahtar in anahtarlar:
            gruplar[anahtar][(h.day_index, h.period_index)] = h
    # Tek kayıt istenmişse (bir öğretmenin kendi programı) yalnız o kalır.
    if kayit is not None:
        if kayit not in gruplar:
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                                f"\"{kayit}\" için yerleşmiş ders yok.")
        gruplar = {kayit: gruplar[kayit]}
    if bakis == "sube":
        t = db.get(Timetable, timetable_id)
        sira = siralama.ad_sirasi(siralama.sirali_subeler(db, t.term), t.term.section_order.value)
        return dict(sorted(gruplar.items(), key=lambda kv: (sira.get(kv[0], 10**6), kv[0])))
    return dict(sorted(gruplar.items()))


def _baslik(db: Session, timetable_id: int, donem: Term) -> tuple[Timetable, str]:
    """Program yalnızca kendi dönemi üzerinden okunur; kurum yalıtımı burada başlar."""
    t = db.get(Timetable, timetable_id)
    if t is None or t.is_deleted or t.term_id != donem.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ders programı bulunamadı.")
    kurum = db.get(Institution, donem.institution_id)
    return t, (kurum.name if kurum else "")


def _html(db: Session, timetable_id: int, bakis: str, donem: Term,
          kayit: str | None = None) -> str:
    t, kurum_adi = _baslik(db, timetable_id, donem)
    gunler, ders_indexleri = _izgara_yapisi(db, donem)
    gruplar = _tablolar(db, timetable_id, bakis, kayit)

    # Her kayıt TEK sayfaya sığar: A4 yatay sayfanın içi 277×190 mm'dir.
    # Başlıklar (~12 mm) ve gün satırı (8 mm) düşülür, kalan yükseklik ders
    # satırlarına eşit bölünür; hücre metni tek satır ve kesilir (…), satırlar
    # büyümez, sayfa taşmaz. Satır sayısı arttıkça yazı küçülür.
    satir_sayisi = max(1, len(ders_indexleri))
    # 188 − başlıklar 14 − gün satırı 8 − kenarlık payı 3 = 163 mm ders satırlarına.
    satir_mm = min(13.0, 163.0 / satir_sayisi)
    punto = max(7.0, min(11.0, satir_mm * 0.75))
    parcalar = [
        "<style>",
        "@page{size:A4 landscape;margin:10mm}",
        "html{color-scheme:light}",
        f"body{{font-family:'Helvetica Neue',Arial,sans-serif;font-size:{punto:g}px;"
        "color:#0f172a;background:#fff;margin:0}",
        "h1{font-size:16px;margin:0 0 2px;line-height:1.2}"
        "h2{font-size:12px;margin:0 0 6px;color:#475569;font-weight:500;line-height:1.2}",
        "section{height:188mm;overflow:hidden;box-sizing:border-box;page-break-after:always}"
        "section:last-child{page-break-after:auto}",
        "table{border-collapse:collapse;width:100%;table-layout:fixed}",
        "tr{page-break-inside:avoid}",
        "th,td{border:1px solid #cbd5e1;padding:0 4px;text-align:center;"
        "vertical-align:middle;overflow:hidden}",
        f"th{{background:#f1f5f9;font-weight:600;height:8mm;white-space:nowrap}}",
        f"td{{height:{satir_mm:.2f}mm}}",
        "th:first-child{width:22mm}",
        "td div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.25}",
        f"td .ders{{font-weight:600}}td .alt{{font-size:{max(6.0, punto - 2):g}px;color:#64748b}}",
        "</style>",
    ]
    for anahtar, hucre_map in gruplar.items():
        parcalar.append("<section>")
        parcalar.append(f"<h1>{_kacis(anahtar)}</h1>")
        parcalar.append(f"<h2>{_kacis(kurum_adi)} · {_kacis(t.name)}</h2>")
        parcalar.append("<table><thead><tr><th></th>")
        for g in gunler:
            parcalar.append(f"<th>{_kacis(g.name)}</th>")
        parcalar.append("</tr></thead><tbody>")
        for sira, di in enumerate(ders_indexleri, start=1):
            parcalar.append(f"<tr><th>{sira}. ders</th>")
            for g in gunler:
                h = hucre_map.get((g.index, di))
                if h is None:
                    parcalar.append("<td></td>")
                else:
                    alt = h.teacher_name if bakis == "sube" else h.section_name
                    # Hücre tek satırdır; uzun ders adı (İnkılap Tarihi…) kesilmesin
                    # diye kısa kodu varsa o yazılır.
                    ders = (h.subject_short
                            if len(h.subject_name) > 22 and h.subject_short
                            else h.subject_name)
                    parcalar.append(
                        f'<td style="background:{h.subject_color}22">'
                        f'<div class="ders">{_kacis(ders)}</div>'
                        f'<div class="alt">{_kacis(alt)}</div></td>'
                    )
            parcalar.append("</tr>")
        parcalar.append("</tbody></table></section>")
    if not gruplar:
        parcalar.append("<p>Bu programda yerleşmiş ders yok.</p>")
    return "".join(parcalar)


def _kapali_saatler(db: Session, donem: Term, bakis: str) -> dict[str, set[int]]:
    """Kayıt adı -> kapalı ders saati kimlikleri.

    Çarşafta boş bir hücrenin neden boş olduğunu ayırt etmek için: yerleşmemiş
    saat mi, yoksa o şubeye/öğretmene kapalı saat mi. Ekrandaki çarşaf da aynı
    ayrımı yapar; basılan sayfa ondan farklı okunmasın.
    """
    if bakis == "sube":
        model, alan, sahip = SectionAvailability, SectionAvailability.section_id, Section
        ad = Section.name
    else:
        model, alan, sahip = TeacherAvailability, TeacherAvailability.teacher_id, Teacher
        ad = Teacher.full_name

    sonuc: dict[str, set[int]] = defaultdict(set)
    for isim, period_id in db.execute(
        select(ad, model.period_id)
        .join(sahip, sahip.id == alan)
        .where(sahip.term_id == donem.id,
               sahip.deleted_at.is_(None),
               model.state == Availability.UYGUN_DEGIL)
    ):
        sonuc[isim].add(period_id)
    return sonuc


def _carsaf_satiri(
    saatler: list, hucre_map: dict, gun_index: int, kapali: set[int]
) -> list[tuple[str, object, int]]:
    """Bir günün hücrelerini (tür, içerik, genişlik) olarak böler.

    Aynı dersin ardışık saatleri tek hücrede birleşir: aynı kısaltmayı iki kez
    okumak yerine bloğun uzunluğu doğrudan görünür.
    """
    parcalar: list[list] = []
    for p in saatler:
        if p.is_break:
            continue
        h = hucre_map.get((gun_index, p.index))
        if h is None:
            parcalar.append(["kapali" if p.id in kapali else "bos", None, 1])
            continue
        onceki = parcalar[-1] if parcalar else None
        if (
            onceki is not None and onceki[0] == "ders"
            and onceki[1].section_id == h.section_id
            and onceki[1].teacher_id == h.teacher_id
            and onceki[1].subject_name == h.subject_name
        ):
            onceki[2] += 1
            continue
        parcalar.append(["ders", h, 1])
    return [(a, b, c) for a, b, c in parcalar]


def _satir_adi(anahtar: str, hucre_map: dict, saat: bool) -> str:
    """Çarşaf satır başlığı; istenirse yerleşen ders saati sayısıyla:
    "Mustafa DİRİM (34)". Birleşik/ortak ders tek hücredir, bir kez sayılır."""
    return f"{anahtar} ({len(hucre_map)})" if saat else anahtar


def _carsaf_html(db: Session, timetable_id: int, bakis: str, donem: Term,
                 saat: bool = False) -> str:
    """Tüm şubeleri (ya da öğretmenleri) tek sayfada gösteren toplu liste.

    Satırlar şube/öğretmen, sütunlar gün × ders saati. Hücrelerde yer dar
    olduğu için tanımlıysa kısa kodlar kullanılır. Düzen ekrandaki çarşafın
    aynısıdır: ardışık saatler birleşir, kapalı saatler `×` ile işaretlenir.
    """
    t, kurum_adi = _baslik(db, timetable_id, donem)
    gunler, _ = _izgara_yapisi(db, donem)
    gruplar = _tablolar(db, timetable_id, bakis)
    kapali_map = _kapali_saatler(db, donem, bakis)

    # Her günün kendi ders saati dizini listesi — günler farklı uzunlukta olabilir.
    gun_saatleri = [(g, _ders_indexleri(g)) for g in gunler]
    gun_saatleri = [(g, idx) for g, idx in gun_saatleri if idx]
    sutun_sayisi = sum(len(idx) for _, idx in gun_saatleri)

    # Sütun sayısı arttıkça yazı küçülür; A4 yatay sayfaya sığması için.
    punto = 7.5 if sutun_sayisi <= 25 else 6.5 if sutun_sayisi <= 35 else 5.5

    p: list[str] = [
        "<style>",
        "@page{size:A4 landscape;margin:8mm}",
        "html{color-scheme:light}",
        "body{font-family:'Helvetica Neue',Arial,sans-serif;color:#0f172a;"
        "background:#fff;margin:0}",
        "h1{font-size:13px;margin:0 0 1px}",
        "h2{font-size:10px;margin:0 0 6px;color:#475569;font-weight:500}",
        f"table{{border-collapse:collapse;width:100%;table-layout:fixed;font-size:{punto}px}}",
        "th,td{border:1px solid #cbd5e1;padding:1px;text-align:center;"
        "overflow:hidden;background:#fff}",
        "th{background:#f1f5f9;font-weight:600}",
        "th.ad{width:70px;text-align:left;padding-left:4px}",
        "td.ad{text-align:left;padding-left:4px;font-weight:600;background:#f8fafc}",
        "td.kpl{background:#f1f5f9;color:#94a3b8}",
        "th.gun{border-left:2px solid #64748b}",
        "td.gunbas,th.gunbas{border-left:2px solid #64748b}",
        ".ders{font-weight:600;display:block;line-height:1.15}",
        ".alt{color:#475569;display:block;line-height:1.15}",
        "</style>",
        f"<h1>{_kacis(t.name)} — Çarşaf Liste "
        f"({'Şube' if bakis == 'sube' else 'Öğretmen'})</h1>",
        f"<h2>{_kacis(kurum_adi)}</h2>",
        "<table><thead><tr>",
        f'<th class="ad" rowspan="2">{"Şube" if bakis == "sube" else "Öğretmen"}</th>',
    ]
    for g, idx in gun_saatleri:
        p.append(f'<th class="gun" colspan="{len(idx)}">{_kacis(g.name)}</th>')
    p.append("</tr><tr>")
    for g, idx in gun_saatleri:
        for konum in range(len(idx)):
            sinif = ' class="gunbas"' if konum == 0 else ""
            p.append(f"<th{sinif}>{konum + 1}</th>")
    p.append("</tr></thead><tbody>")

    for anahtar, hucre_map in gruplar.items():
        p.append(f'<tr><td class="ad">{_kacis(_satir_adi(anahtar, hucre_map, saat))}</td>')
        kapali = kapali_map.get(anahtar, set())
        for g, idx in gun_saatleri:
            saatler = [x for x in sorted(g.periods, key=lambda y: y.index)
                       if x.index in set(idx)]
            for konum, (tur, h, genislik) in enumerate(
                _carsaf_satiri(saatler, hucre_map, g.index, kapali)
            ):
                sinif = "gunbas" if konum == 0 else ""
                genis = f' colspan="{genislik}"' if genislik > 1 else ""
                if tur == "kapali":
                    p.append(f'<td class="kpl {sinif}"{genis}>×</td>')
                elif tur == "bos":
                    p.append(f'<td class="{sinif}"{genis}></td>')
                else:
                    ders = h.subject_short or h.subject_name
                    alt = (
                        (h.teacher_short or h.teacher_name)
                        if bakis == "sube"
                        else h.section_name
                    )
                    p.append(
                        f'<td class="{sinif}"{genis} '
                        f'style="background:{h.subject_color}1f">'
                        f'<span class="ders">{_kacis(ders)}</span>'
                        f'<span class="alt">{_kacis(alt)}</span></td>'
                    )
        p.append("</tr>")

    p.append("</tbody></table>")
    if not gruplar:
        p.append("<p>Bu programda yerleşmiş ders yok.</p>")
    return "".join(p)


def _dosya_adi(ad: str) -> str:
    """Kayıt adından dosya adı parçası: harf, rakam, tire."""
    import re
    import unicodedata
    duz = unicodedata.normalize("NFKD", ad.replace("ı", "i").replace("İ", "I"))
    duz = "".join(c for c in duz if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "-", duz).strip("-").lower() or "kayit"


def _kacis(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _icerik(db: Session, timetable_id: int, bakis: str, duzen: str, donem: Term,
            saat: bool = False, kayit: str | None = None) -> str:
    if duzen == "carsaf":
        return _carsaf_html(db, timetable_id, bakis, donem, saat)
    return _html(db, timetable_id, bakis, donem, kayit)


@router.get("/html", response_class=Response)
def html_cikti(
    timetable_id: int,
    bakis: str = Query("sube", pattern="^(sube|ogretmen)$"),
    duzen: str = Query("ayri", pattern="^(ayri|carsaf)$"),
    # Çarşafta satır adının yanına yerleşen ders saati sayısı: "Ad (34)".
    saat: bool = Query(False),
    # Yalnız bu kayıt (öğretmen ya da şube adı): tek kişilik çıktı.
    kayit: str | None = Query(None),
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Response:
    return Response(
        _icerik(db, timetable_id, bakis, duzen, donem, saat, kayit),
        media_type="text/html; charset=utf-8",
    )


@router.get("/pdf", response_class=Response)
def pdf_cikti(
    timetable_id: int,
    bakis: str = Query("sube", pattern="^(sube|ogretmen)$"),
    duzen: str = Query("ayri", pattern="^(ayri|carsaf)$"),
    saat: bool = Query(False),
    kayit: str | None = Query(None),
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Response:
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "PDF üretimi için gereken sistem kütüphaneleri kurulu değil "
            f"(macOS: brew install pango). Ayrıntı: {e}. "
            "Bu arada HTML çıktısını tarayıcıdan yazdırabilirsiniz.",
        )
    pdf = HTML(string=_icerik(db, timetable_id, bakis, duzen, donem, saat, kayit)).write_pdf()
    ad = f"ders-programi-{_dosya_adi(kayit) if kayit else f'{duzen}-{bakis}'}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{ad}"'})


@router.get("/zip", response_class=Response)
def zip_cikti(
    timetable_id: int,
    bakis: str = Query("ogretmen", pattern="^(sube|ogretmen)$"),
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Response:
    """Her öğretmen (ya da şube) için ayrı bir PDF; hepsi tek ZIP dosyasında.
    Öğretmenlere kendi programlarını tek tek dağıtmak için."""
    import zipfile

    try:
        from weasyprint import HTML
    except (ImportError, OSError) as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "PDF üretimi için gereken sistem kütüphaneleri kurulu değil "
            f"(macOS: brew install pango). Ayrıntı: {e}.",
        )
    _baslik(db, timetable_id, donem)
    gruplar = _tablolar(db, timetable_id, bakis)
    if not gruplar:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bu programda yerleşmiş ders yok.")
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as arsiv:
        for anahtar in gruplar:
            pdf = HTML(string=_html(db, timetable_id, bakis, donem, kayit=anahtar)).write_pdf()
            arsiv.writestr(f"{_dosya_adi(anahtar)}.pdf", pdf)
    ad = f"ders-programlari-{bakis}.zip"
    return Response(tampon.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{ad}"'})


@router.get("/xlsx", response_class=Response)
def excel_cikti(
    timetable_id: int,
    bakis: str = Query("sube", pattern="^(sube|ogretmen)$"),
    duzen: str = Query("ayri", pattern="^(ayri|carsaf)$"),
    saat: bool = Query(False),
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Response:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side

    _baslik(db, timetable_id, donem)      # kurum yalıtımı denetimi
    gunler, ders_indexleri = _izgara_yapisi(db, donem)
    gruplar = _tablolar(db, timetable_id, bakis)

    wb = Workbook()
    wb.remove(wb.active)
    kenar = Border(*[Side(style="thin", color="CBD5E1")] * 4)
    ortala = Alignment(horizontal="center", vertical="center", wrap_text=True)

    if duzen == "carsaf":
        _carsaf_excel(wb, gunler, gruplar, bakis, kenar, ortala, Font, Alignment, saat)
        return _excel_yanit(wb, f"carsaf-{bakis}")

    for anahtar, hucre_map in gruplar.items():
        ws = wb.create_sheet(title=anahtar[:31].replace("/", "-"))
        ws.cell(row=1, column=1, value="").border = kenar
        for c, g in enumerate(gunler, start=2):
            h = ws.cell(row=1, column=c, value=g.name)
            h.font, h.alignment, h.border = Font(bold=True), ortala, kenar
            ws.column_dimensions[h.column_letter].width = 24
        for r, di in enumerate(ders_indexleri, start=2):
            b = ws.cell(row=r, column=1, value=f"{r - 1}. ders")
            b.font, b.alignment, b.border = Font(bold=True), ortala, kenar
            ws.row_dimensions[r].height = 32
            for c, g in enumerate(gunler, start=2):
                hucre = hucre_map.get((g.index, di))
                metin = ""
                if hucre is not None:
                    alt = hucre.teacher_name if bakis == "sube" else hucre.section_name
                    metin = f"{hucre.subject_name}\n{alt}"
                x = ws.cell(row=r, column=c, value=metin)
                x.alignment, x.border = ortala, kenar

    if not gruplar:
        wb.create_sheet(title="Bos")["A1"] = "Bu programda yerleşmiş ders yok."

    return _excel_yanit(wb, f"ders-programi-{bakis}")


def _carsaf_excel(wb, gunler, gruplar, bakis, kenar, ortala, Font, Alignment,
                  saat: bool = False) -> None:
    """Tek sayfada toplu liste: satırlar şube/öğretmen, sütunlar gün × ders saati."""
    ws = wb.create_sheet(title="Çarşaf")
    gun_saatleri = [(g, _ders_indexleri(g)) for g in gunler]
    gun_saatleri = [(g, idx) for g, idx in gun_saatleri if idx]

    ws.column_dimensions["A"].width = 18
    ws.freeze_panes = "B3"

    baslik = ws.cell(row=1, column=1, value="Şube" if bakis == "sube" else "Öğretmen")
    baslik.font, baslik.border = Font(bold=True), kenar
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=1)
    baslik.alignment = Alignment(horizontal="left", vertical="center")

    sutun = 2
    for g, idx in gun_saatleri:
        gun_hucre = ws.cell(row=1, column=sutun, value=g.name)
        gun_hucre.font, gun_hucre.alignment, gun_hucre.border = (
            Font(bold=True), ortala, kenar,
        )
        if len(idx) > 1:
            ws.merge_cells(start_row=1, start_column=sutun,
                           end_row=1, end_column=sutun + len(idx) - 1)
        for konum in range(len(idx)):
            h = ws.cell(row=2, column=sutun + konum, value=konum + 1)
            h.font, h.alignment, h.border = Font(bold=True), ortala, kenar
            ws.column_dimensions[h.column_letter].width = 12
        sutun += len(idx)

    for satir, (anahtar, hucre_map) in enumerate(gruplar.items(), start=3):
        ad = ws.cell(row=satir, column=1, value=_satir_adi(anahtar, hucre_map, saat))
        ad.font, ad.border = Font(bold=True), kenar
        ws.row_dimensions[satir].height = 30
        sutun = 2
        for g, idx in gun_saatleri:
            for konum, di in enumerate(idx):
                h = hucre_map.get((g.index, di))
                metin = ""
                if h is not None:
                    alt = h.teacher_name if bakis == "sube" else h.section_name
                    metin = f"{h.subject_name}\n{alt}"
                x = ws.cell(row=satir, column=sutun + konum, value=metin)
                x.alignment, x.border = ortala, kenar
            sutun += len(idx)

    if not gruplar:
        ws["A3"] = "Bu programda yerleşmiş ders yok."


def _excel_yanit(wb, dosya_adi: str) -> Response:
    tampon = io.BytesIO()
    wb.save(tampon)
    return Response(
        tampon.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{dosya_adi}.xlsx"'},
    )
