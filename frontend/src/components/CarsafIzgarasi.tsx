/** Çarşaf görünümü: bütün şubeler (ya da öğretmenler) tek tabloda.
 *
 *  Satırlar şube/öğretmen, sütunlar gün × ders saati. Çıktıdaki çarşafın
 *  ekrandaki karşılığıdır; amaç haftanın tamamını tek bakışta görmektir.
 *
 *  Üç karar bu görünümü okunur kılıyor:
 *
 *  1. **Ardışık saatler tek hücrede birleşir.** Aynı dersin arka arkaya gelen
 *     saatleri (blok) tek geniş hücre olarak çizilir. Aynı kısaltmayı iki kez
 *     okumak yerine bloğun uzunluğu doğrudan görünür.
 *  2. **Kapalı saatler boş saatten ayrılır.** Şubeye/öğretmene kapalı saatler
 *     `×` ile taranır; yoksa akşamcı bir şubenin sabahları "doldurulmamış"
 *     gibi okunurdu.
 *  3. **Salt inceleme.** Sürükle-bırak burada yok: birleşmiş bir bloğun hangi
 *     saatinin taşındığı belirsiz olurdu. Satır adına tıklamak o kaydı ayrı
 *     sayfa görünümünde açar; düzenleme orada yapılır.
 */
import clsx from "clsx";
import { Lock } from "lucide-react";

import { dersZemini } from "../lib/renkler";
import type { DersSaati, Gun, Hucre } from "../lib/types";
import type { Bakis } from "./ProgramIzgarasi";

/** Ad sütununun genişliği ve bir ders saatinin en az genişliği (px).
 *
 *  Toplamı kapsayıcıdan genişse tablo yatay kayar, darsa sütunlar eşit
 *  bölüşür — yani alt sınır yalnızca yoğun durumda bağlar, sütun az olduğunda
 *  kendiliğinden genişlerler.
 *
 *  28px, olağan haftanın (5 gün × 8 saat = 40 sütun) masaüstünde tek ekrana
 *  sığması için seçildi: ölçülen kullanılabilir genişlik 1239px, bu düzende
 *  tablo 1230px. Kısa kodlar bu genişlikte okunur. Dar ekranda ya da daha uzun
 *  haftalarda tablo kaydırılır; ad sütunu ve başlıklar yapışkan olduğu için
 *  yön kaybolmaz. */
const AD_GENISLIK = 110;
const EN_AZ_SUTUN = 28;

/** Bir satırın bir gündeki hücrelerinin çizim planı. */
type Parca =
  | { tur: "ders"; hucre: Hucre; kilitli: boolean; genislik: number; anahtar: string }
  | {
      tur: "bos" | "teneffus" | "kapali";
      genislik: number;
      anahtar: string;
      ogle?: boolean;
    };

function ust(hucre: Hucre): string {
  return hucre.subject_short || hucre.subject_name;
}

/** Şube bakışında öğretmen, öğretmen bakışında şube. */
function alt(hucre: Hucre, bakis: Bakis): string {
  return bakis === "sube"
    ? hucre.teacher_short || hucre.teacher_name
    : hucre.section_name;
}

/** İki hücre aynı ders atamasının parçası mı?
 *  (şube, ders, öğretmen) üçlüsü bir müfredat satırını tekil olarak belirler. */
function ayniDers(a: Hucre, b: Hucre): boolean {
  return (
    a.section_id === b.section_id &&
    a.teacher_id === b.teacher_id &&
    a.subject_name === b.subject_name
  );
}

/** Bir günün saatlerini çizim parçalarına böler; ardışık aynı ders birleşir. */
function gunuBol(
  saatler: DersSaati[],
  hucreler: Map<string, Hucre>,
  gunIndex: number,
  kapaliSaatler: Set<number>,
): Parca[] {
  const parcalar: Parca[] = [];
  for (const p of saatler) {
    const anahtar = String(p.id);
    if (p.is_break) {
      parcalar.push({ tur: "teneffus", genislik: 1, anahtar, ogle: p.is_lunch });
      continue;
    }
    const h = hucreler.get(`${gunIndex}:${p.index}`);
    if (!h) {
      parcalar.push({
        tur: kapaliSaatler.has(p.id) ? "kapali" : "bos",
        genislik: 1,
        anahtar,
      });
      continue;
    }
    // Önceki parça aynı dersse genişlet; blok tek hücre olarak okunur.
    const onceki = parcalar[parcalar.length - 1];
    if (onceki?.tur === "ders" && ayniDers(onceki.hucre, h)) {
      onceki.genislik += 1;
      onceki.kilitli = onceki.kilitli || h.is_locked;
      continue;
    }
    parcalar.push({
      tur: "ders", hucre: h, kilitli: h.is_locked, genislik: 1, anahtar,
    });
  }
  return parcalar;
}

function DersHucresi({
  parca,
  bakis,
  gunbas,
}: {
  parca: Extract<Parca, { tur: "ders" }>;
  bakis: Bakis;
  gunbas: boolean;
}) {
  const { hucre, kilitli, genislik } = parca;
  const kim = bakis === "sube" ? hucre.teacher_name : hucre.section_name;
  return (
    <td
      colSpan={genislik}
      title={`${hucre.subject_name} · ${kim}${genislik > 1 ? ` · ${genislik} saatlik blok` : ""}${kilitli ? " · kilitli" : ""}`}
      className={clsx(
        "h-9 border border-cizgi p-px align-middle",
        gunbas && "border-l-2 border-l-cizgi-guclu",
      )}
    >
      <div
        className="flex h-full w-full flex-col justify-center overflow-hidden rounded-sm px-0.5 text-center"
        style={dersZemini(hucre.subject_color, 2)}
      >
        <span className="sayisal flex items-center justify-center gap-0.5 truncate font-mono text-[10px] font-medium leading-tight text-murekkep">
          {kilitli && <Lock className="h-2 w-2 shrink-0 text-murekkep-silik" />}
          <span className="truncate">{ust(hucre)}</span>
        </span>
        {/* Ders renginin üzerinde `silik` ton koyu temada 3.2:1'e düşüyor;
          * `yumusak` en kötü durumda 5.7:1 (bkz. erişilebilirlik denetimi). */}
        <span className="truncate text-[9px] leading-tight text-murekkep-yumusak">
          {alt(hucre, bakis)}
        </span>
      </div>
    </td>
  );
}

export default function CarsafIzgarasi({
  gunler,
  hucreler,
  bakis,
  kapali,
  ac,
}: {
  gunler: Gun[];
  hucreler: Hucre[];
  bakis: Bakis;
  /** Kayıt kimliği -> kapalı ders saati kimlikleri. */
  kapali?: Record<number, number[]>;
  /** Satır adına tıklanınca çağrılır; ayrı sayfa görünümüne geçmek için. */
  ac?: (anahtar: string) => void;
}) {
  // Her günün kendi ders saatleri — günler farklı uzunlukta olabilir.
  const gunSaatleri = gunler
    .filter((g) => g.is_active)
    .map((g) => ({ gun: g, saatler: [...g.periods].sort((a, b) => a.index - b.index) }))
    .filter((x) => x.saatler.length > 0);
  const sutunSayisi = gunSaatleri.reduce((t, x) => t + x.saatler.length, 0);

  // Satırlar yerleşmiş derslerden çıkar: ad, kimlik ve hücre haritası.
  const satirlar = new Map<string, { id: number; hucreler: Map<string, Hucre> }>();
  for (const h of hucreler) {
    const ad = bakis === "sube" ? h.section_name : h.teacher_name;
    let satir = satirlar.get(ad);
    if (!satir) {
      satirlar.set(ad, (satir = {
        id: bakis === "sube" ? h.section_id : h.teacher_id,
        hucreler: new Map(),
      }));
    }
    satir.hucreler.set(`${h.day_index}:${h.period_index}`, h);
  }
  const sirali = [...satirlar.entries()].sort((a, b) => a[0].localeCompare(b[0], "tr"));

  return (
    // Dikey kaydırma satır sayısı arttığında devreye girer; başlıklar ve ad
    // sütunu yapışkan olduğu için ne baktığınız kaybolmaz.
    <div className="max-h-[70vh] overflow-auto">
      <table
        className="w-full table-fixed border-collapse"
        style={{ minWidth: AD_GENISLIK + sutunSayisi * EN_AZ_SUTUN }}
      >
        <colgroup>
          <col style={{ width: AD_GENISLIK }} />
          {gunSaatleri.flatMap((x) =>
            x.saatler.map((p) => <col key={p.id} />),
          )}
        </colgroup>
        <thead>
          <tr>
            <th
              rowSpan={2}
              className="sticky left-0 top-0 z-30 border border-cizgi bg-yuzey-alt px-2 py-1.5 text-left text-[11px] font-semibold text-murekkep-yumusak"
            >
              {bakis === "sube" ? "Şube" : "Öğretmen"}
            </th>
            {gunSaatleri.map((x) => (
              <th
                key={x.gun.id}
                colSpan={x.saatler.length}
                // Yükseklik açıkça verilir: ikinci başlık satırının yapışkan
                // konumu (top-[30px]) buna dayanıyor, yazı tipine değil.
                className="sticky top-0 z-20 h-[30px] border border-cizgi border-l-2 border-l-cizgi-guclu bg-yuzey-alt px-1 text-[11px] font-semibold text-murekkep-yumusak"
              >
                {x.gun.name}
              </th>
            ))}
          </tr>
          <tr>
            {gunSaatleri.flatMap((x) =>
              x.saatler.map((p, konum) => (
                <th
                  key={p.id}
                  title={
                    p.start_time && p.end_time
                      ? `${x.gun.name} · ${p.index + 1}. ders (${p.start_time.slice(0, 5)}–${p.end_time.slice(0, 5)})`
                      : `${x.gun.name} · ${p.index + 1}. ders`
                  }
                  className={clsx(
                    "sayisal sticky top-[30px] z-20 border border-cizgi bg-yuzey-alt px-0.5 py-1 font-mono text-[10px] font-medium text-murekkep-silik",
                    konum === 0 && "border-l-2 border-l-cizgi-guclu",
                  )}
                >
                  {p.index + 1}
                </th>
              )),
            )}
          </tr>
        </thead>
        <tbody>
          {sirali.map(([ad, satir]) => {
            const kapaliSaatler = new Set(kapali?.[satir.id] ?? []);
            return (
              <tr key={ad} className="group">
                <th
                  scope="row"
                  className="sticky left-0 z-10 border border-cizgi bg-yuzey px-2 py-1 text-left align-middle group-hover:bg-yuzey-alt"
                >
                  {ac ? (
                    <button
                      onClick={() => ac(ad)}
                      title={`${ad} — ayrı sayfa görünümünde aç`}
                      className="block w-full truncate text-left text-[11px] font-semibold text-murekkep underline-offset-2 hover:underline"
                    >
                      {ad}
                    </button>
                  ) : (
                    <span className="block truncate text-[11px] font-semibold text-murekkep">
                      {ad}
                    </span>
                  )}
                </th>
                {gunSaatleri.flatMap((x) =>
                  gunuBol(x.saatler, satir.hucreler, x.gun.index, kapaliSaatler).map(
                    (parca, konum) => {
                      const gunbas = konum === 0;
                      if (parca.tur === "ders") {
                        return (
                          <DersHucresi
                            key={parca.anahtar}
                            parca={parca}
                            bakis={bakis}
                            gunbas={gunbas}
                          />
                        );
                      }
                      if (parca.tur === "teneffus") {
                        return (
                          <td
                            key={parca.anahtar}
                            title={parca.ogle ? "öğle arası" : "teneffüs"}
                            className={clsx(
                              "h-9 border border-cizgi text-center align-middle text-[9px] leading-none text-uyari",
                              // Öğle arası günü ikiye böler: yarım gün sınırı
                              // buradan geçer, o yüzden gözle seçilebilmeli.
                              parca.ogle ? "bg-uyari-zemin font-medium" : "bg-uyari-zemin",
                              gunbas && "border-l-2 border-l-cizgi-guclu",
                            )}
                          >
                            {parca.ogle ? "öğle" : ""}
                          </td>
                        );
                      }
                      if (parca.tur === "kapali") {
                        return (
                          <td
                            key={parca.anahtar}
                            title={`${ad} bu saatte uygun değil`}
                            className={clsx(
                              "h-9 border border-cizgi bg-yuzey-alt text-center align-middle text-[10px] leading-none text-murekkep-silik",
                              gunbas && "border-l-2 border-l-cizgi-guclu",
                            )}
                          >
                            ×
                          </td>
                        );
                      }
                      return (
                        <td
                          key={parca.anahtar}
                          className={clsx(
                            "h-9 border border-cizgi bg-yuzey-alt/60",
                            gunbas && "border-l-2 border-l-cizgi-guclu",
                          )}
                        />
                      );
                    },
                  ),
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
