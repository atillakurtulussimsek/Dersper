"""Çıktı: sınıf / öğretmen bazında HTML, PDF ve Excel."""
from __future__ import annotations

import io
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import aktif_donem, current_user
from datetime import date

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


def _kayit_tablosu(gunler: list, ders_indexleri: list[int], hucre_map: dict,
                   bakis: str) -> str:
    """Tek kaydın (öğretmen/şube) haftalık tablosu; ayrı sayfa ve tebligat
    çıktıları aynı tabloyu kullanır."""
    parcalar = ["<table><thead><tr><th></th>"]
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
                # Hücre tek satırdır; dikey sayfada sütun ~28 mm, kalın yazıyla
                # ~16 karakter alır. Uzun ders adı kesilmesin diye kısa kodu
                # varsa o yazılır ("Türk Dili ve Edebiyatı" → EDB).
                ders = (h.subject_short
                        if len(h.subject_name) > 16 and h.subject_short
                        else h.subject_name)
                parcalar.append(
                    f'<td style="background:{h.subject_color}22">'
                    f'<div class="ders">{_kacis(ders)}</div>'
                    f'<div class="alt">{_kacis(alt)}</div></td>'
                )
        parcalar.append("</tr>")
    parcalar.append("</tbody></table>")
    return "".join(parcalar)


def _tablo_css(satir_mm: float, punto: float) -> str:
    return (
        "table{border-collapse:collapse;width:100%;table-layout:fixed}"
        "tr{page-break-inside:avoid}"
        "th,td{border:1px solid #cbd5e1;padding:0 4px;text-align:center;"
        "vertical-align:middle;overflow:hidden}"
        "th{background:#f1f5f9;font-weight:600;height:8mm;white-space:nowrap}"
        f"td{{height:{satir_mm:.2f}mm}}"
        "th:first-child{width:22mm}"
        "td div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.25}"
        f"td .ders{{font-weight:600}}td .alt{{font-size:{max(6.0, punto - 2):g}px;color:#64748b}}"
    )


# A4 sayfanın iç alanı (10 mm kenar boşluğuyla): yön -> (genişlik, yükseklik) mm.
A4_IC_MM = {"dikey": (190.0, 277.0), "yatay": (277.0, 190.0)}


def _html(db: Session, timetable_id: int, bakis: str, donem: Term,
          kayit: str | None = None, yon: str = "dikey") -> str:
    t, kurum_adi = _baslik(db, timetable_id, donem)
    gunler, ders_indexleri = _izgara_yapisi(db, donem)
    gruplar = _tablolar(db, timetable_id, bakis, kayit)

    # Her kayıt TEK sayfaya sığar: A4 DİKEY sayfanın içi 190×277 mm'dir. Altı
    # gün 190 mm'ye rahat sığar (28 mm sütun); dikey sayfa dosyalamaya uygun.
    # Başlıklar (~14 mm), gün satırı (8 mm), imza (4 mm) ve pay (3 mm) düşülür,
    # kalan yükseklik ders satırlarına eşit bölünür; hücre metni tek satır ve
    # kesilir (…), satırlar büyümez, sayfa taşmaz.
    satir_sayisi = max(1, len(ders_indexleri))
    _, yukseklik = A4_IC_MM.get(yon, A4_IC_MM["dikey"])
    satir_mm = min(16.0, (yukseklik - 29.0) / satir_sayisi)
    punto = max(7.0, min(11.0, satir_mm * 0.75))
    parcalar = [
        "<style>",
        f"@page{{size:A4 {'landscape' if yon == 'yatay' else 'portrait'};margin:10mm}}",
        "html{color-scheme:light}",
        f"body{{font-family:'Helvetica Neue',Arial,sans-serif;font-size:{punto:g}px;"
        "color:#0f172a;background:#fff;margin:0}",
        "h1{font-size:16px;margin:0 0 2px;line-height:1.2}"
        "h2{font-size:12px;margin:0 0 6px;color:#475569;font-weight:500;line-height:1.2}",
        f"section{{height:{yukseklik:.0f}mm;overflow:hidden;box-sizing:border-box;"
        "page-break-after:always}section:last-child{page-break-after:auto}",
        IMZA_CSS,
        _tablo_css(satir_mm, punto),
        "</style>",
    ]
    for anahtar, hucre_map in gruplar.items():
        parcalar.append("<section>")
        parcalar.append(f"<h1>{_kacis(anahtar)}</h1>")
        parcalar.append(f"<h2>{_kacis(kurum_adi)}</h2>")
        parcalar.append(_kayit_tablosu(gunler, ders_indexleri, hucre_map, bakis))
        parcalar.append(IMZA_HTML + "</section>")
    if not gruplar:
        parcalar.append("<p>Bu programda yerleşmiş ders yok.</p>")
    return "".join(parcalar)


def _tebligat_html(db: Session, timetable_id: int, donem: Term,
                   kayit: str | None = None, yon: str = "dikey") -> str:
    """Öğretmenlere resmi tebligat: MEB "Tebliğ-Tebellüğ Belgesi" düzeninde,
    her öğretmene bir A4 yatay sayfa. Üstte kimlik ve yazı bilgileri, ortada
    haftalık program, altta tebliğ cümlesi ile Tebliğ Eden (okul müdürü) ve
    Tebellüğ Eden (öğretmen) imza alanları. Tarih ve sayı alanları elle
    doldurulmak üzere boş bırakılır."""
    t, kurum_adi = _baslik(db, timetable_id, donem)
    kurum = db.get(Institution, donem.institution_id)
    mudur = (kurum.principal_name or "").strip() if kurum else ""
    gunler, ders_indexleri = _izgara_yapisi(db, donem)
    gruplar = _tablolar(db, timetable_id, "ogretmen", kayit)
    ogretmenler = {
        o.full_name: o for o in db.scalars(
            select(Teacher).where(Teacher.term_id == donem.id, Teacher.deleted_at.is_(None))
        )
    }

    # A4 DİKEY (iç alan 190×277 mm). Yükseklik bütçesi: başlık 16 + bilgi 30 +
    # tebliğ cümlesi 10 + imzalar 22 + imza satırı 4 + gün satırı 8 + pay 5 =
    # 95 → tabloya 182 mm.
    satir_sayisi = max(1, len(ders_indexleri))
    _, yukseklik = A4_IC_MM.get(yon, A4_IC_MM["dikey"])
    satir_mm = min(13.0, (yukseklik - 95.0) / satir_sayisi)
    punto = max(6.5, min(10.0, satir_mm * 0.9))
    bugun = date.today().strftime("%d.%m.%Y")
    bos = "…… / …… / ……"

    parcalar = [
        "<style>",
        f"@page{{size:A4 {'landscape' if yon == 'yatay' else 'portrait'};margin:10mm}}",
        "html{color-scheme:light}",
        f"body{{font-family:'Helvetica Neue',Arial,sans-serif;font-size:{punto:g}px;"
        "color:#0f172a;background:#fff;margin:0}",
        f"section{{height:{yukseklik:.0f}mm;overflow:hidden;box-sizing:border-box;"
        "page-break-after:always;position:relative}section:last-child{page-break-after:auto}",
        ".ust{text-align:center;margin-bottom:3mm}",
        ".ust .kurum{font-size:13px;font-weight:700;letter-spacing:0.02em}",
        ".ust .belge{font-size:12px;font-weight:700;margin-top:1mm}",
        ".ust .donem{font-size:10px;color:#475569;margin-top:0.5mm}",
        "table.bilgi{border-collapse:collapse;width:100%;table-layout:fixed;margin-bottom:3mm;"
        "font-size:9px}",
        "table.bilgi td{border:1px solid #cbd5e1;padding:1.2mm 2mm;text-align:left;"
        "vertical-align:middle;height:auto}",
        "table.bilgi td.e{width:34mm;background:#f1f5f9;font-weight:600;white-space:nowrap}",
        "p.teblig{margin:3mm 0 0;font-size:9.5px;line-height:1.4}",
        "table.imza{border-collapse:collapse;width:100%;table-layout:fixed;margin-top:4mm;"
        "font-size:9.5px}",
        "table.imza td{border:0;text-align:center;vertical-align:top;padding:0;height:auto}",
        "table.imza .rol{font-weight:700}",
        "table.imza .cizgi{margin:9mm auto 1mm;width:55mm;border-top:1px solid #0f172a}",
        "table.imza .ad{font-weight:600}",
        "table.imza .unvan{color:#475569}",
        IMZA_CSS,
        "footer{position:absolute;right:0;bottom:0}",
        _tablo_css(satir_mm, punto),
        "</style>",
    ]
    for ad, hucre_map in gruplar.items():
        o = ogretmenler.get(ad)
        brans = (o.branch or "").strip() if o else ""
        gorev = f"{brans} Öğretmeni" if brans else "Öğretmen"
        parcalar.append("<section>")
        parcalar.append(
            '<div class="ust">'
            f'<div class="kurum">{_kacis(kurum_adi.upper())}</div>'
            '<div class="belge">HAFTALIK DERS PROGRAMI TEBLİĞ – TEBELLÜĞ BELGESİ</div></div>'
        )
        parcalar.append(
            '<table class="bilgi"><tr>'
            f'<td class="e">Adı Soyadı</td><td>{_kacis(ad)}</td>'
            f'<td class="e">Görevi</td><td>{_kacis(gorev)}</td></tr><tr>'
            f'<td class="e">Görev Yeri</td><td>{_kacis(kurum_adi)}</td>'
            f'<td class="e">Tebliğ Edildiği Yer</td><td>{_kacis(kurum_adi)}</td></tr><tr>'
            f'<td class="e">Yazının Tarih ve Sayısı</td><td>{bos} &nbsp;–&nbsp; Sayı: ……………</td>'
            f'<td class="e">Tebliğ Tarihi</td><td>{bos}</td></tr><tr>'
            f'<td class="e">Yazının Özü</td><td colspan="3">Haftalık ders programının tebliği '
            f'(düzenleme tarihi {bugun})</td></tr></table>'
        )
        parcalar.append(_kayit_tablosu(gunler, ders_indexleri, hucre_map, "ogretmen"))
        parcalar.append(
            '<p class="teblig">Yukarıda adı soyadı, görevi ve görev yeri yazılı bulunan '
            'öğretmene, yukarıdaki haftalık ders programı tebliğ edilmiştir. Programın '
            'belirtilen tarihten itibaren uygulanması hususunda bilgilerinizi ve gereğini '
            'rica ederim.</p>'
        )
        parcalar.append(
            # Solda tebellüğ eden öğretmen (ad, branş, tarih), sağda tebliğ
            # eden kurum müdürü: resmi yazıda imza sağda durur.
            '<table class="imza"><tr>'
            '<td><div class="rol">Tebellüğ Eden</div><div class="cizgi"></div>'
            f'<div class="ad">{_kacis(ad)}</div>'
            f'<div class="unvan">{_kacis(gorev)}</div>'
            f'<div class="unvan">Tarih: {bos}</div></td>'
            '<td><div class="rol">Tebliğ Eden</div><div class="cizgi"></div>'
            f'<div class="ad">{_kacis(mudur) if mudur else "…………………………………"}</div>'
            '<div class="unvan">Kurum Müdürü</div></td>'
            '</tr></table>'
        )
        parcalar.append(IMZA_HTML + "</section>")
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


# Çarşaf kâğıdı: yatay sayfanın iç genişliği (mm, 8 mm kenar boşluğuyla).
KAGIT_GENISLIK_MM = {"a4": 281.0, "a3": 404.0}
# Yatay sayfanın iç yüksekliği (mm, 8 mm kenar boşluğuyla).
KAGIT_YUKSEKLIK_MM = {"a4": 194.0, "a3": 281.0}


def _carsaf_html(db: Session, timetable_id: int, bakis: str, donem: Term,
                 saat: bool = False, kapali: bool = True, kagit: str = "a3",
                 tek_sayfa: bool = True) -> str:
    """Tüm şubeleri (ya da öğretmenleri) tek sayfada gösteren toplu liste.

    Satırlar şube/öğretmen, sütunlar gün × ders saati. Hücrelerde yer dar
    olduğu için tanımlıysa kısa kodlar kullanılır. Düzen ekrandaki çarşafın
    aynısıdır: ardışık saatler birleşir, kapalı saatler `×` ile işaretlenir.
    """
    t, kurum_adi = _baslik(db, timetable_id, donem)
    gunler, _ = _izgara_yapisi(db, donem)
    gruplar = _tablolar(db, timetable_id, bakis)
    # Kapalı saatler idarenin işine yarar; öğretmenlere/velilere dağıtılan
    # çarşafta gösterilmeyebilir (kapali=False): o hücreler boş kalır.
    kapali_map = _kapali_saatler(db, donem, bakis) if kapali else {}

    # Her günün kendi ders saati dizini listesi — günler farklı uzunlukta olabilir.
    gun_saatleri = [(g, _ders_indexleri(g)) for g in gunler]
    gun_saatleri = [(g, idx) for g, idx in gun_saatleri if idx]

    # Okunurluk sütun genişliğinden gelir. 70 sütunluk (6 gün × 12 saat) hafta
    # A3'e bile 5 mm'lik sütunlarla sığar; bu okunmaz. Bunun yerine günler
    # sayfalara bölünür: her sayfada en çok EN_COK_SUTUN sütun, ad sütunu her
    # sayfada yinelenir. Kısa hafta tek sayfada kalır.
    # `tek_sayfa`: bütün hafta ve bütün kayıtlar TEK sayfaya sığdırılır; yazı
    # hem genişliğe hem yüksekliğe göre küçülür (idarenin duvar çarşafı).
    # Aksi hâlde günler sayfalara bölünür: her sayfada en çok EN_COK_SUTUN
    # sütun, ad sütunu her sayfada yinelenir (okunur, çok sayfalı).
    en_cok_sutun = 10**6 if tek_sayfa else (40 if kagit == "a3" else 28)
    sayfalar: list[list[tuple]] = [[]]
    for g, idx in gun_saatleri:
        dolu = sum(len(i) for _, i in sayfalar[-1])
        if sayfalar[-1] and dolu + len(idx) > en_cok_sutun:
            sayfalar.append([])
        sayfalar[-1].append((g, idx))
    sutun_sayisi = max(sum(len(idx) for _, idx in sayfa) for sayfa in sayfalar)

    # Yazı boyu sütun genişliğinden türetilir. Üst satır (kısa kod, ~4
    # karakter) tek satırda sığmalı: yazı ≈ sütun/3.6. Alt satır (öğretmen/
    # şube) daha küçük ve iki satıra sarabilir; satır yüksekliği buna göre.
    ad_mm = 30.0 if not tek_sayfa else 36.0
    sutun_mm = (KAGIT_GENISLIK_MM.get(kagit, KAGIT_GENISLIK_MM["a3"]) - ad_mm) / max(1, sutun_sayisi)
    sutun_px = sutun_mm * 3.78
    punto = max(4.5, min(10.0, sutun_px / 3.6))
    ders_satir = 1.2         # üst satır (kısa kod) tek satır (em)
    alt_satir = 2.3          # alt satır en çok iki satır (em)
    if tek_sayfa:
        # Sayfa TAMAMEN doldurulur: başlıklar (~12 mm) ve iki başlık satırı
        # (~8 mm) düşülünce kalan yükseklik kayıt sayısına bölünür ve her satır
        # o kadar olur — az kayıtta satırlar uzar, yazı büyür (aSc çarşafı gibi).
        # Yazı boyu üç düzen arasından en büyüğünü verenle seçilir: kısa kod
        # tek satırda (genişlik sınırlar) ya da iki satıra kırılarak (yükseklik
        # sınırlar); alt satır bir ya da iki satır.
        # Başlıklar (9,4 mm), iki başlık satırı (8,7 mm) ve imza (4,8 mm)
        # tarayıcıda ölçüldü: 23 mm; 3 mm pay bırakılır.
        # Satırların toplam yüksekliği tablonun `height`'ıyla SABİTLENİR; yazı
        # boyu bu paya göre seçilir. Hücre yüksekliğine güvenilmez: dolgu ve
        # kenarlığın hücre yüksekliğine dahil sayılıp sayılmaması işleyiciye
        # göre değişir (tarayıcı dahil sayar, WeasyPrint saymayabilir) ve 25
        # satırda 3 px'lik fark 20 mm eder — ikinci sayfa demek.
        satir_mm = (KAGIT_YUKSEKLIK_MM.get(kagit, 281.0) - 27.0) / max(1, len(gruplar))
        satir_px_tavan = satir_mm * 3.78 - 3.0      # kenarlık + dolgu payı
        # Genişliği en uzun kısa kod belirler (kalın yazıda karakter ≈ 0.58em).
        en_uzun = max(
            (len(h.subject_short or h.subject_name)
             for hm in gruplar.values() for h in hm.values()),
            default=4,
        )
        en_uzun = max(3, en_uzun)
        secenekler = []
        # Eşitlikte daha çok satır kazanır (max ilk büyük demeti seçer).
        for d_em, a_em in ((2.3, 3.45), (2.3, 2.3), (2.3, 1.15),
                           (1.2, 3.45), (1.2, 2.3), (1.2, 1.15)):
            # Tek satırda kodun tamamı; iki satırda kod ortadan kırılır.
            karakter = en_uzun if d_em < 2 else -(-en_uzun // 2)
            genislik = (sutun_px - 3) / (0.58 * karakter)
            # max-height'lara eklenen 0.1em'lik kırpma payı da hesaba katılır.
            yukseklik = (satir_px_tavan - 4) / ((d_em + 0.1) + 0.8 * (a_em + 0.1))
            secenekler.append((min(11.0, genislik, yukseklik), d_em, a_em))
        punto, ders_satir, alt_satir = max(secenekler)
        punto = max(4.0, punto)
        alt_punto = max(4.0, punto * 0.8)
        satir_px = satir_px_tavan
    else:
        alt_punto = max(5.5, punto * 0.8)
        satir_px = punto * 1.2 + alt_punto * 2.3 + 6

    p: list[str] = [
        "<style>",
        f"@page{{size:{kagit.upper()} landscape;margin:8mm}}",
        "html{color-scheme:light}",
        "body{font-family:'Helvetica Neue',Arial,sans-serif;color:#0f172a;"
        "background:#fff;margin:0}",
        "h1{font-size:13px;margin:0 0 1px}",
        "h2{font-size:10px;margin:0 0 6px;color:#475569;font-weight:500}",
        "section{page-break-after:always}section:last-child{page-break-after:auto}"
        # Tek sayfa ilkesi: hesap ne derse desin bölüm sayfa yüksekliğini
        # aşamaz; taşan bir milimetre ikinci sayfa açmaz, kırpılır.
        # 1 mm eksik: bölüm sayfa alanına tam eşit olursa yuvarlama boş bir
        # ikinci sayfa açabilir.
        + (f"section{{height:{KAGIT_YUKSEKLIK_MM.get(kagit, 281.0) - 1:g}mm;overflow:hidden}}"
           if tek_sayfa else ""),
        IMZA_CSS,
        f"table{{border-collapse:collapse;width:100%;table-layout:fixed;font-size:{punto:.1f}px}}",
        "td span{display:block;overflow:hidden}",
        "thead{display:table-header-group}tr{page-break-inside:avoid}",
        "th,td{border:1px solid #cbd5e1;padding:1px;text-align:center;"
        "overflow:hidden;background:#fff}",
        # Tek sayfada satır yüksekliği tabloya dağıtılır (thead kendi doğal
        # yüksekliğini alır, kalan eşit bölünür); çok sayfada hücre başına.
        (f"table{{height:{KAGIT_YUKSEKLIK_MM.get(kagit, 281.0) - 27.0 + 9.0:g}mm}}"
         if tek_sayfa else f"td{{height:{satir_px:.0f}px}}"),
        "th{background:#f1f5f9;font-weight:600}",
        f"th.ad{{width:{ad_mm:.0f}mm;text-align:left;padding-left:4px}}",
        f"td.ad{{text-align:left;padding-left:4px;font-weight:600;background:#f8fafc;"
        f"font-size:{punto + 1:.1f}px;white-space:nowrap;text-overflow:ellipsis}}",
        "td.kpl{background:#f1f5f9;color:#94a3b8}",
        "th.gun{border-left:2px solid #64748b}",
        "td.gunbas,th.gunbas{border-left:2px solid #64748b}",
        f".ders{{font-weight:600;line-height:1.15;max-height:{ders_satir + 0.1:.2f}em"
        + (";white-space:nowrap;text-overflow:ellipsis" if ders_satir < 2
           else ";word-break:break-all") + "}",
        f".alt{{color:#475569;font-size:{alt_punto:.1f}px;line-height:1.15;"
        f"max-height:{alt_satir + 0.1:.2f}em;word-break:break-word"
        + (";white-space:nowrap;text-overflow:ellipsis" if alt_satir < 2 else "") + "}",
        "</style>",
    ]
    baslik = f"{'Şube' if bakis == 'sube' else 'Öğretmen'} çarşafı"
    for sayfa_no, sayfa in enumerate(sayfalar, start=1):
        gun_adlari = ", ".join(g.name for g, _ in sayfa)
        p.append("<section>")
        p.append(f"<h1>{_kacis(kurum_adi)}</h1>")
        p.append(f"<h2>{baslik}"
                 + (f" · {_kacis(gun_adlari)} ({sayfa_no}/{len(sayfalar)})"
                    if len(sayfalar) > 1 else "")
                 + "</h2>")
        p.append("<table><thead><tr>")
        p.append(f'<th class="ad" rowspan="2">{"Şube" if bakis == "sube" else "Öğretmen"}</th>')
        for g, idx in sayfa:
            p.append(f'<th class="gun" colspan="{len(idx)}">{_kacis(g.name)}</th>')
        p.append("</tr><tr>")
        for g, idx in sayfa:
            for konum in range(len(idx)):
                sinif = ' class="gunbas"' if konum == 0 else ""
                p.append(f"<th{sinif}>{konum + 1}</th>")
        p.append("</tr></thead><tbody>")

        for anahtar, hucre_map in gruplar.items():
            p.append(f'<tr><td class="ad">{_kacis(_satir_adi(anahtar, hucre_map, saat))}</td>')
            kapali = kapali_map.get(anahtar, set())
            for g, idx in sayfa:
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
                            (h.teacher_short or _kisa_ad(h.teacher_name))
                            if bakis == "sube"
                            else h.section_name
                        )
                        # Uzun bir ad (öğretmen soyadı, şube kodu) hücreye
                        # sığmıyorsa yalnız o hücrenin alt yazısı küçülür;
                        # sayfanın geri kalanı büyük kalır.
                        alt_pt = _alt_puntosu(alt, alt_punto, sutun_px * genislik,
                                              alt_satir)
                        alt_stil = (f' style="font-size:{alt_pt:.1f}px"'
                                    if alt_pt < alt_punto - 0.05 else "")
                        p.append(
                            f'<td class="{sinif}"{genis} '
                            f'style="background:{h.subject_color}1f">'
                            f'<span class="ders">{_kacis(ders)}</span>'
                            f'<span class="alt"{alt_stil}>{_kacis(alt)}</span></td>'
                        )
            p.append("</tr>")
        p.append("</tbody></table>" + IMZA_HTML + "</section>")
    if not gruplar:
        p.append("<p>Bu programda yerleşmiş ders yok.</p>")
    return "".join(p)


def _alt_puntosu(metin: str, taban: float, sutun_px: float, alt_satir: float) -> float:
    """Alt yazının bu hücreye sığacağı yazı boyu (px), `taban`ı aşmaz.

    Sözcük ortadan kırılmasın: en uzun sözcük bir satıra sığmalı; bütün metin
    de izin verilen satır sayısına. Karakter genişliği ≈ 0.58em (Ö, M gibi
    geniş harfler için pay).
    """
    ic = max(8.0, sutun_px - 3)
    satir = max(1, round(alt_satir / 1.15))
    kelime = max((len(k) for k in metin.split()), default=1) or 1
    pt = min(taban, ic / (0.58 * kelime), ic * satir / (0.58 * max(1, len(metin))))
    return max(4.5, pt)


def _kisa_ad(ad: str) -> str:
    """Çarşafın dar hücresi için "ARİFE KARAKUM TEKİN" -> "A. K. TEKİN".

    Kısa kodu girilmemiş öğretmen için geri düşüş; tam ad ayrı sayfa
    çıktılarında olduğu gibi kalır.
    """
    parcalar = ad.split()
    if len(parcalar) < 2:
        return ad
    return " ".join(f"{p[0]}." for p in parcalar[:-1]) + " " + parcalar[-1]


def _dosya_adi(ad: str) -> str:
    """Kayıt adından dosya adı parçası: harf, rakam, tire."""
    import re
    import unicodedata
    duz = unicodedata.normalize("NFKD", ad.replace("ı", "i").replace("İ", "I"))
    duz = "".join(c for c in duz if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "-", duz).strip("-").lower() or "kayit"


# Çıktıların altındaki sessiz imza. Küçük, soluk, sağa yaslı.
IMZA = "Varkhe Digital Ders Planlama Programı"
IMZA_CSS = ("footer{margin-top:2mm;text-align:right;font-size:8.5px;color:#475569;"
            "font-weight:500;letter-spacing:0.02em}")
IMZA_HTML = f"<footer>{IMZA}</footer>"


def _kacis(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _icerik(db: Session, timetable_id: int, bakis: str, duzen: str, donem: Term,
            saat: bool = False, kayit: str | None = None, kapali: bool = True,
            kagit: str = "a3", tek_sayfa: bool = True, yon: str = "dikey") -> str:
    if duzen == "carsaf":
        return _carsaf_html(db, timetable_id, bakis, donem, saat, kapali, kagit, tek_sayfa)
    if duzen == "tebligat":
        return _tebligat_html(db, timetable_id, donem, kayit, yon)
    return _html(db, timetable_id, bakis, donem, kayit, yon)


@router.get("/html", response_class=Response)
def html_cikti(
    timetable_id: int,
    bakis: str = Query("sube", pattern="^(sube|ogretmen)$"),
    duzen: str = Query("ayri", pattern="^(ayri|carsaf|tebligat)$"),
    # Çarşafta satır adının yanına yerleşen ders saati sayısı: "Ad (34)".
    saat: bool = Query(False),
    # Yalnız bu kayıt (öğretmen ya da şube adı): tek kişilik çıktı.
    kayit: str | None = Query(None),
    # Çarşafta kapalı saatler (×) gösterilsin mi? Dağıtılan çıktıda kapatılır.
    kapali: bool = Query(True),
    # Çarşaf kâğıdı: a3 (geniş, okunur) ya da a4. Tarayıcıdan yazdırmada a4.
    kagit: str = Query("a4", pattern="^(a4|a3)$"),
    # Çarşaf tek sayfaya sığdırılsın mı (yazı küçülür), yoksa günler sayfalara
    # bölünsün mü (okunur)?
    tek_sayfa: bool = Query(True),
    # Kişisel sayfalar (ayrı, tebligat): dikey ya da yatay.
    yon: str = Query("dikey", pattern="^(dikey|yatay)$"),
    db: Session = Depends(get_db),
    donem: Term = Depends(aktif_donem),
) -> Response:
    return Response(
        _icerik(db, timetable_id, bakis, duzen, donem, saat, kayit, kapali, kagit, tek_sayfa, yon),
        media_type="text/html; charset=utf-8",
    )


@router.get("/pdf", response_class=Response)
def pdf_cikti(
    timetable_id: int,
    bakis: str = Query("sube", pattern="^(sube|ogretmen)$"),
    duzen: str = Query("ayri", pattern="^(ayri|carsaf|tebligat)$"),
    saat: bool = Query(False),
    kayit: str | None = Query(None),
    kapali: bool = Query(True),
    kagit: str = Query("a3", pattern="^(a4|a3)$"),
    tek_sayfa: bool = Query(True),
    # Kişisel sayfalar (ayrı, tebligat): dikey ya da yatay.
    yon: str = Query("dikey", pattern="^(dikey|yatay)$"),
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
    pdf = HTML(string=_icerik(db, timetable_id, bakis, duzen, donem, saat, kayit, kapali,
                              kagit, tek_sayfa, yon)).write_pdf()
    ad = f"ders-programi-{_dosya_adi(kayit) if kayit else f'{duzen}-{bakis}'}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{ad}"'})


@router.get("/zip", response_class=Response)
def zip_cikti(
    timetable_id: int,
    bakis: str = Query("ogretmen", pattern="^(sube|ogretmen)$"),
    # ayri: sade program sayfası; tebligat: resmi tebliğ-tebellüğ belgesi.
    duzen: str = Query("ayri", pattern="^(ayri|tebligat)$"),
    yon: str = Query("dikey", pattern="^(dikey|yatay)$"),
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
            html = (_tebligat_html(db, timetable_id, donem, kayit=anahtar, yon=yon)
                    if duzen == "tebligat"
                    else _html(db, timetable_id, bakis, donem, kayit=anahtar, yon=yon))
            arsiv.writestr(f"{_dosya_adi(anahtar)}.pdf", HTML(string=html).write_pdf())
    ad = f"{'tebligat' if duzen == 'tebligat' else 'ders-programlari'}-{bakis}.zip"
    return Response(tampon.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{ad}"'})


@router.get("/xlsx", response_class=Response)
def excel_cikti(
    timetable_id: int,
    bakis: str = Query("sube", pattern="^(sube|ogretmen)$"),
    duzen: str = Query("ayri", pattern="^(ayri|carsaf|tebligat)$"),
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
