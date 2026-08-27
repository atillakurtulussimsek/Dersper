"""Çıktı: sınıf / öğretmen bazında HTML, PDF ve Excel."""
from __future__ import annotations

import io
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import current_user
from app.models import Day, Institution, Timetable
from app.routers.timetables import izgara_hucreleri

router = APIRouter(prefix="/timetables/{timetable_id}/export", tags=["çıktı"],
                   dependencies=[Depends(current_user)])

BAKIS = {"sube": "Şube", "ogretmen": "Öğretmen"}


def _izgara_yapisi(db: Session) -> tuple[list[Day], list[int]]:
    """Aktif günler ve haftadaki en geniş ders saati dizini listesi."""
    gunler = [
        g for g in db.scalars(
            select(Day).options(selectinload(Day.periods))
            .where(Day.is_active.is_(True)).order_by(Day.index)
        )
    ]
    en_fazla = max(
        (max((p.index for p in g.periods), default=-1) for g in gunler), default=-1
    )
    return gunler, list(range(en_fazla + 1))


def _tablolar(db: Session, timetable_id: int, bakis: str) -> dict[str, dict]:
    """Anahtar (şube adı ya da öğretmen adı) -> {(gun, ders): hücre}"""
    hucreler = izgara_hucreleri(db, timetable_id)
    gruplar: dict[str, dict] = defaultdict(dict)
    for h in hucreler:
        anahtar = h.section_name if bakis == "sube" else h.teacher_name
        gruplar[anahtar][(h.day_index, h.period_index)] = h
    return dict(sorted(gruplar.items()))


def _html(db: Session, timetable_id: int, bakis: str) -> str:
    t = db.get(Timetable, timetable_id)
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ders programı bulunamadı.")
    kurum = db.scalar(select(Institution).limit(1))
    gunler, ders_indexleri = _izgara_yapisi(db)
    gruplar = _tablolar(db, timetable_id, bakis)

    parcalar = [
        "<style>",
        "@page{size:A4 landscape;margin:12mm}",
        "body{font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;color:#0f172a}",
        "h1{font-size:16px;margin:0 0 2px}h2{font-size:13px;margin:0 0 8px;color:#475569;font-weight:500}",
        "section{page-break-after:always}section:last-child{page-break-after:auto}",
        "table{border-collapse:collapse;width:100%}",
        "th,td{border:1px solid #cbd5e1;padding:5px 6px;text-align:center;vertical-align:middle;height:34px}",
        "th{background:#f1f5f9;font-weight:600}",
        "td .ders{font-weight:600}td .alt{font-size:9px;color:#64748b}",
        "</style>",
    ]
    for anahtar, hucre_map in gruplar.items():
        parcalar.append("<section>")
        parcalar.append(f"<h1>{_kacis(anahtar)}</h1>")
        parcalar.append(
            f"<h2>{_kacis(kurum.name if kurum else '')} · {_kacis(t.name)}</h2>"
        )
        parcalar.append("<table><thead><tr><th></th>")
        for g in gunler:
            parcalar.append(f"<th>{_kacis(g.name)}</th>")
        parcalar.append("</tr></thead><tbody>")
        for di in ders_indexleri:
            parcalar.append(f"<tr><th>{di + 1}. ders</th>")
            for g in gunler:
                h = hucre_map.get((g.index, di))
                if h is None:
                    parcalar.append("<td></td>")
                else:
                    alt = h.teacher_name if bakis == "sube" else h.section_name
                    parcalar.append(
                        f'<td style="background:{h.subject_color}22">'
                        f'<div class="ders">{_kacis(h.subject_name)}</div>'
                        f'<div class="alt">{_kacis(alt)}</div></td>'
                    )
            parcalar.append("</tr>")
        parcalar.append("</tbody></table></section>")
    if not gruplar:
        parcalar.append("<p>Bu programda yerleşmiş ders yok.</p>")
    return "".join(parcalar)


def _kacis(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


@router.get("/html", response_class=Response)
def html_cikti(
    timetable_id: int,
    bakis: str = Query("sube", pattern="^(sube|ogretmen)$"),
    db: Session = Depends(get_db),
) -> Response:
    return Response(_html(db, timetable_id, bakis), media_type="text/html; charset=utf-8")


@router.get("/pdf", response_class=Response)
def pdf_cikti(
    timetable_id: int,
    bakis: str = Query("sube", pattern="^(sube|ogretmen)$"),
    db: Session = Depends(get_db),
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
    pdf = HTML(string=_html(db, timetable_id, bakis)).write_pdf()
    ad = f"ders-programi-{bakis}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{ad}"'})


@router.get("/xlsx", response_class=Response)
def excel_cikti(
    timetable_id: int,
    bakis: str = Query("sube", pattern="^(sube|ogretmen)$"),
    db: Session = Depends(get_db),
) -> Response:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side

    gunler, ders_indexleri = _izgara_yapisi(db)
    gruplar = _tablolar(db, timetable_id, bakis)

    wb = Workbook()
    wb.remove(wb.active)
    kenar = Border(*[Side(style="thin", color="CBD5E1")] * 4)
    ortala = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for anahtar, hucre_map in gruplar.items():
        ws = wb.create_sheet(title=anahtar[:31].replace("/", "-"))
        ws.cell(row=1, column=1, value="").border = kenar
        for c, g in enumerate(gunler, start=2):
            h = ws.cell(row=1, column=c, value=g.name)
            h.font, h.alignment, h.border = Font(bold=True), ortala, kenar
            ws.column_dimensions[h.column_letter].width = 24
        for r, di in enumerate(ders_indexleri, start=2):
            b = ws.cell(row=r, column=1, value=f"{di + 1}. ders")
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

    tampon = io.BytesIO()
    wb.save(tampon)
    ad = f"ders-programi-{bakis}.xlsx"
    return Response(
        tampon.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{ad}"'},
    )
