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
import { Lock, Users } from "lucide-react";

import { dersZemini } from "../lib/renkler";
import type { DersSaati, Gun, Hucre } from "../lib/types";
import type { Bakis } from "./ProgramIzgarasi";
import { ortakNotu, subeEtiketi } from "../lib/cakisma";
import { siraKarsilastirici } from "../lib/siralama";

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

/** Yoğunluk: "sikisik" haftayı tek ekrana sığdırır (28px sütun); "rahat"
 *  hücreleri büyütür ve yazıyı okunur kılar, gerekirse tablo yatay kayar. */
export type Yogunluk = "sikisik" | "rahat";

const OLCULER: Record<Yogunluk, {
  ad: number; sutun: number; satir: string; ust: string; alt: string; baslik: string;
  gunYukseklik: string; saatUst: string;
}> = {
  sikisik: {
    ad: AD_GENISLIK, sutun: EN_AZ_SUTUN, satir: "h-9",
    ust: "text-[10px]", alt: "text-[9px]", baslik: "text-[11px]",
    gunYukseklik: "h-[30px]", saatUst: "top-[30px]",
  },
  rahat: {
    ad: 160, sutun: 46, satir: "h-12",
    ust: "text-[12px]", alt: "text-[10px]", baslik: "text-[12px]",
    gunYukseklik: "h-[34px]", saatUst: "top-[34px]",
  },
};

/** Bir satırın bir gündeki hücrelerinin çizim planı. */
type Parca =
  | { tur: "ders"; hucre: Hucre; kilitli: boolean; genislik: number; anahtar: string }
  | {
      tur: "bos" | "kapali";
      genislik: number;
      anahtar: string;
    };

function ust(hucre: Hucre): string {
  return hucre.subject_short || hucre.subject_name;
}

/** Şube bakışında öğretmen, öğretmen bakışında şube. */
function alt(hucre: Hucre, bakis: Bakis): string {
  return bakis === "sube"
    ? hucre.teacher_short || hucre.teacher_name
    : subeEtiketi(hucre);
}

/** İki hücre aynı ders atamasının parçası mı?
 *  (şube, ders, öğretmen) üçlüsü bir müfredat satırını tekil olarak belirler. */
function ayniDers(a: Hucre, b: Hucre): boolean {
  return (
    a.section_id === b.section_id &&
    a.teacher_id === b.teacher_id &&
    a.subject_name === b.subject_name &&
    (a.merged_entry_id ?? null) === (b.merged_entry_id ?? null)
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
    if (p.is_break) continue;               // aralar sütun değildir
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
  olcu,
}: {
  parca: Extract<Parca, { tur: "ders" }>;
  bakis: Bakis;
  gunbas: boolean;
  olcu: (typeof OLCULER)[Yogunluk];
}) {
  const { hucre, kilitli, genislik } = parca;
  const kim = bakis === "sube" ? hucre.teacher_name : subeEtiketi(hucre);
  return (
    <td
      colSpan={genislik}
      title={`${hucre.subject_name} · ${kim}${genislik > 1 ? ` · ${genislik} saatlik blok` : ""}${kilitli ? " · kilitli" : ""}${ortakNotu(hucre) ? ` · ${ortakNotu(hucre)}` : ""}`}
      className={clsx(
        olcu.satir, "border border-cizgi p-px align-middle",
        gunbas && "border-l-2 border-l-cizgi-guclu",
      )}
    >
      <div
        className="relative flex h-full w-full flex-col justify-center overflow-hidden rounded-sm px-1 text-center"
        style={dersZemini(hucre.subject_color, 2)}
      >
        {/* Ortak ders: hücre birkaç şubenin satırında birden görünür. Çarşaf
          * hücresi dar; simge satır içinde kısa kodu ezmesin diye köşede. */}
        {ortakNotu(hucre) && (
          <Users
            className="absolute right-0.5 top-0.5 h-2 w-2 text-murekkep-yumusak"
            aria-label="Ortak ders"
          />
        )}
        <span className={clsx("sayisal flex items-center justify-center gap-0.5 truncate font-mono font-medium leading-tight text-murekkep", olcu.ust)}>
          {kilitli && <Lock className="h-2 w-2 shrink-0 text-murekkep-silik" />}
          <span className="truncate">{ust(hucre)}</span>
        </span>
        {/* Ders renginin üzerinde `silik` ton koyu temada 3.2:1'e düşüyor;
          * `yumusak` en kötü durumda 5.7:1 (bkz. erişilebilirlik denetimi). */}
        <span className={clsx("truncate leading-tight text-murekkep-yumusak", olcu.alt)}>
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
  subeSirasi,
  kapali,
  ac,
  saatGoster,
  yogunluk,
}: {
  gunler: Gun[];
  hucreler: Hucre[];
  bakis: Bakis;
  /** Şube adları, kurumun seçtiği sırayla (ızgara yanıtından). */
  subeSirasi?: string[];
  /** Kayıt kimliği -> kapalı ders saati kimlikleri. */
  kapali?: Record<number, number[]>;
  /** Satır adına tıklanınca çağrılır; ayrı sayfa görünümüne geçmek için. */
  ac?: (anahtar: string) => void;
  /** Ad yanında yerleşen ders saati sayısı: "Mustafa DİRİM (34)". */
  saatGoster?: boolean;
  /** Hücre büyüklüğü; varsayılan rahat. */
  yogunluk?: Yogunluk;
}) {
  const olcu = OLCULER[yogunluk ?? "rahat"];
  // Her günün kendi ders saatleri — günler farklı uzunlukta olabilir.
  const gunSaatleri = gunler
    .filter((g) => g.is_active)
    // Aralar (teneffüs, öğle) sütun değildir: yalnız ders saatleri.
    .map((g) => ({
      gun: g,
      saatler: g.periods.filter((p) => !p.is_break).sort((a, b) => a.index - b.index),
    }))
    .filter((x) => x.saatler.length > 0);
  const sutunSayisi = gunSaatleri.reduce((t, x) => t + x.saatler.length, 0);

  // Satırlar yerleşmiş derslerden çıkar: ad, kimlik ve hücre haritası.
  const satirlar = new Map<string, { id: number; hucreler: Map<string, Hucre> }>();
  for (const h of hucreler) {
    // Birleşik ders her şubesinin satırına düşer; öğretmen görünümünde tektir.
    const adlar = bakis === "sube"
      ? (h.section_names?.length ? h.section_names : [h.section_name])
      : [h.teacher_name];
    for (const ad of adlar) {
      let satir = satirlar.get(ad);
      if (!satir) {
        satirlar.set(ad, (satir = {
          id: bakis === "sube" ? h.section_id : h.teacher_id,
          hucreler: new Map(),
        }));
      }
      satir.hucreler.set(`${h.day_index}:${h.period_index}`, h);
    }
  }
  // Şube satırları kurumun seçtiği sırayla; öğretmen satırları ada göre.
  const karsilastir =
    bakis === "sube" ? siraKarsilastirici(subeSirasi ?? []) : (a: string, b: string) => a.localeCompare(b, "tr");
  const sirali = [...satirlar.entries()].sort((a, b) => karsilastir(a[0], b[0]));

  return (
    // Dikey kaydırma satır sayısı arttığında devreye girer; başlıklar ve ad
    // sütunu yapışkan olduğu için ne baktığınız kaybolmaz.
    <div className="max-h-[70vh] overflow-auto">
      <table
        className="w-full table-fixed border-collapse"
        style={{ minWidth: olcu.ad + sutunSayisi * olcu.sutun }}
      >
        <colgroup>
          <col style={{ width: olcu.ad }} />
          {gunSaatleri.flatMap((x) =>
            x.saatler.map((p) => <col key={p.id} />),
          )}
        </colgroup>
        <thead>
          <tr>
            <th
              rowSpan={2}
              className={clsx("sticky left-0 top-0 z-30 border border-cizgi bg-yuzey-alt px-2 py-1.5 text-left font-semibold text-murekkep-yumusak", olcu.baslik)}
            >
              {bakis === "sube" ? "Şube" : "Öğretmen"}
            </th>
            {gunSaatleri.map((x) => (
              <th
                key={x.gun.id}
                colSpan={x.saatler.length}
                // Yükseklik açıkça verilir: ikinci başlık satırının yapışkan
                // konumu (top-[30px]) buna dayanıyor, yazı tipine değil.
                className={clsx("sticky top-0 z-20 border border-cizgi border-l-2 border-l-cizgi-guclu bg-yuzey-alt px-1 font-semibold text-murekkep-yumusak", olcu.gunYukseklik, olcu.baslik)}
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
                      ? `${x.gun.name} · ${konum + 1}. ders (${p.start_time.slice(0, 5)}–${p.end_time.slice(0, 5)})`
                      : `${x.gun.name} · ${konum + 1}. ders`
                  }
                  className={clsx(
                    "sayisal sticky z-20 border border-cizgi bg-yuzey-alt px-0.5 py-1 font-mono font-medium text-murekkep-silik",
                    olcu.saatUst, olcu.ust,
                    konum === 0 && "border-l-2 border-l-cizgi-guclu",
                  )}
                >
                  {konum + 1}
                </th>
              )),
            )}
          </tr>
        </thead>
        <tbody>
          {sirali.map(([ad, satir]) => {
            const kapaliSaatler = new Set(kapali?.[satir.id] ?? []);
            // Birleşik/ortak ders tek hücredir; öğretmen için bir kez sayılır.
            const etiket = saatGoster ? `${ad} (${satir.hucreler.size})` : ad;
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
                      className={clsx("block w-full truncate text-left font-semibold text-murekkep underline-offset-2 hover:underline", olcu.baslik)}
                    >
                      {etiket}
                    </button>
                  ) : (
                    <span className={clsx("block truncate font-semibold text-murekkep", olcu.baslik)}>
                      {etiket}
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
                            olcu={olcu}
                          />
                        );
                      }
                      if (parca.tur === "kapali") {
                        return (
                          <td
                            key={parca.anahtar}
                            title={`${ad} bu saatte uygun değil`}
                            className={clsx(
                              olcu.satir, "border border-cizgi bg-yuzey-alt text-center align-middle leading-none text-murekkep-silik", olcu.ust,
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
                            olcu.satir, "border border-cizgi bg-yuzey-alt/60",
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
