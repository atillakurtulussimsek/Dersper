/** Ders programı ekranının araç çubuğu: bakış, düzen, kayıt seçimi ve çıktılar.
 *  Tek satırda toplanır, tabloyla birlikte kaydırılmasın diye yapışkandır.
 *
 *  Düzen seçimi hem ekranı hem çıktıyı belirler: ne görüyorsanız onu
 *  yazdırırsınız. Kayıt şeritleri yalnızca ayrı sayfa düzeninde anlamlıdır,
 *  çarşafta zaten hepsi görünür — o durumda çağıran boş liste geçirir. */
import { ChevronDown, Download, FileSpreadsheet, Printer } from "lucide-react";
import clsx from "clsx";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Buton } from "./ui";
import type { Bakis } from "./ProgramIzgarasi";
import type { Yogunluk } from "./CarsafIzgarasi";

export type Duzen = "ayri" | "carsaf";

/** PDF menüsünden seçilen çıktı: hangi bakış, hangi düzen, tek kayıt mı,
 *  her kayıt ayrı dosya (ZIP) mı. */
export type PdfSecenek = {
  bakis: Bakis;
  duzen: Duzen;
  kayit?: string;
  zip?: boolean;
  /** Çarşaf kâğıdı; verilmezse sunucu A3 kullanır. */
  kagit?: "a3" | "a4";
  /** Çarşaf: günler sayfalara bölünsün (okunur) mü? Varsayılan tek sayfa. */
  bolunmus?: boolean;
};

function PdfMenusu({
  seciliAnahtar,
  bakis,
  duzen,
  indir,
}: {
  seciliAnahtar?: string;
  bakis: Bakis;
  duzen: Duzen;
  indir: (s: PdfSecenek) => void;
}) {
  const [acik, setAcik] = useState(false);
  const kutu = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!acik) return;
    const kapat = (e: MouseEvent) => {
      if (!kutu.current?.contains(e.target as Node)) setAcik(false);
    };
    document.addEventListener("mousedown", kapat);
    return () => document.removeEventListener("mousedown", kapat);
  }, [acik]);

  const secili = duzen === "ayri" ? seciliAnahtar : undefined;
  const bolumler: { baslik: string; ogeler: { etiket: string; secenek: PdfSecenek }[] }[] = [
    {
      baslik: "Şube çarşafı",
      ogeler: [
        { etiket: "Tek sayfa — A3 yatay", secenek: { bakis: "sube", duzen: "carsaf", kagit: "a3" } },
        { etiket: "Tek sayfa — A4 yatay", secenek: { bakis: "sube", duzen: "carsaf", kagit: "a4" } },
        { etiket: "Günler sayfalara bölünmüş — A3 (büyük yazı)", secenek: { bakis: "sube", duzen: "carsaf", kagit: "a3", bolunmus: true } },
      ],
    },
    {
      baslik: "Öğretmen çarşafı",
      ogeler: [
        { etiket: "Tek sayfa — A3 yatay", secenek: { bakis: "ogretmen", duzen: "carsaf", kagit: "a3" } },
        { etiket: "Tek sayfa — A4 yatay", secenek: { bakis: "ogretmen", duzen: "carsaf", kagit: "a4" } },
        { etiket: "Günler sayfalara bölünmüş — A3 (büyük yazı)", secenek: { bakis: "ogretmen", duzen: "carsaf", kagit: "a3", bolunmus: true } },
      ],
    },
    {
      baslik: "Öğretmen programları",
      ogeler: [
        { etiket: "Tüm öğretmenler, tek PDF (her biri ayrı sayfa)",
          secenek: { bakis: "ogretmen", duzen: "ayri" } },
        { etiket: "Her öğretmen ayrı dosya (ZIP)",
          secenek: { bakis: "ogretmen", duzen: "ayri", zip: true } },
        ...(bakis === "ogretmen" && secili
          ? [{ etiket: `Yalnız ${secili}`, secenek: { bakis: "ogretmen" as Bakis, duzen: "ayri" as Duzen, kayit: secili } }]
          : []),
      ],
    },
    {
      baslik: "Şube programları",
      ogeler: [
        { etiket: "Tüm şubeler, tek PDF (her biri ayrı sayfa)",
          secenek: { bakis: "sube", duzen: "ayri" } },
        { etiket: "Her şube ayrı dosya (ZIP)",
          secenek: { bakis: "sube", duzen: "ayri", zip: true } },
        ...(bakis === "sube" && secili
          ? [{ etiket: `Yalnız ${secili}`, secenek: { bakis: "sube" as Bakis, duzen: "ayri" as Duzen, kayit: secili } }]
          : []),
      ],
    },
  ];

  return (
    <div ref={kutu} className="relative">
      <Buton tur="ikincil" onClick={() => setAcik((a) => !a)} title="PDF indir">
        <Download className="h-4 w-4" />
        <span className="hidden sm:inline">PDF</span>
        <ChevronDown className="h-3.5 w-3.5" />
      </Buton>
      {acik && (
        <div className="absolute right-0 z-30 mt-1 w-72 rounded-lg border border-cizgi bg-yuzey p-1 shadow-xl shadow-murekkep/10">
          {bolumler.map((b) => (
            <div key={b.baslik} className="py-1">
              <p className="px-2 pb-1 text-2xs font-semibold uppercase tracking-[0.08em] text-murekkep-silik">
                {b.baslik}
              </p>
              {b.ogeler.map((o) => (
                <button
                  key={o.etiket}
                  onClick={() => { setAcik(false); indir(o.secenek); }}
                  className="block w-full truncate rounded-md px-2 py-1.5 text-left text-sm text-murekkep hover:bg-yuzey-alt"
                >
                  {o.etiket}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Segment<T extends string>({
  deger,
  secenekler,
  degistir,
}: {
  deger: T;
  secenekler: { id: T; etiket: string; ipucu?: string }[];
  degistir: (d: T) => void;
}) {
  return (
    <div className="flex shrink-0 rounded-lg border border-cizgi-guclu bg-yuzey p-0.5">
      {secenekler.map((s) => (
        <button
          key={s.id}
          onClick={() => degistir(s.id)}
          title={s.ipucu}
          className={clsx(
            "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
            deger === s.id ? "bg-murekkep text-uzeri" : "text-murekkep-yumusak hover:bg-yuzey-alt",
          )}
        >
          {s.etiket}
        </button>
      ))}
    </div>
  );
}

export default function ProgramAracCubugu({
  bakis,
  bakisDegistir,
  duzen,
  duzenDegistir,
  anahtarlar,
  seciliAnahtar,
  anahtarDegistir,
  baslik,
  ozet,
  yazdir,
  indir,
  saatGoster,
  saatGosterDegistir,
  kapaliGoster,
  kapaliGosterDegistir,
  yogunluk,
  yogunlukDegistir,
  pdfIndir,
}: {
  bakis: Bakis;
  bakisDegistir: (b: Bakis) => void;
  duzen: Duzen;
  duzenDegistir: (d: Duzen) => void;
  anahtarlar: string[];
  seciliAnahtar?: string;
  anahtarDegistir: (a: string) => void;
  /** Kayıt şeritleri yokken (çarşaf) neye bakıldığını söyler. */
  baslik?: string;
  /** "23 saat dolu" gibi kısa sayımlar; şeritlerin sağına yaslanır. */
  ozet?: ReactNode;
  yazdir: () => void;
  indir: (bicim: "xlsx") => void;
  /** Çarşafta satır adının yanında yerleşen saat sayısı: "Ad (34)". */
  saatGoster?: boolean;
  saatGosterDegistir?: (v: boolean) => void;
  /** Çarşafta kapalı saatler (×) görünsün mü? Dağıtılan çıktıda kapatılır. */
  kapaliGoster?: boolean;
  kapaliGosterDegistir?: (v: boolean) => void;
  /** Çarşaf hücre büyüklüğü. */
  yogunluk?: Yogunluk;
  yogunlukDegistir?: (y: Yogunluk) => void;
  /** PDF menüsü: çarşaf, toplu, tek kişilik ya da ZIP. */
  pdfIndir: (s: PdfSecenek) => void;
}) {
  return (
    // z-40: çarşafın yapışkan başlıkları z-30'da; PDF menüsü gibi açılır
    // parçalar araç çubuğunun katmanında olduğu için onun üstünde kalmalı.
    <div className="sticky top-0 z-40 -mx-5 -mt-5 mb-4 space-y-2.5 border-b border-cizgi bg-yuzey/95 px-5 py-3 backdrop-blur">
      <div className="flex flex-wrap items-center gap-2">
        <Segment
          deger={bakis}
          degistir={bakisDegistir}
          secenekler={[
            { id: "sube", etiket: "Şube" },
            { id: "ogretmen", etiket: "Öğretmen" },
          ]}
        />

        <span className="text-xs text-murekkep-silik">Düzen:</span>
        <Segment
          deger={duzen}
          degistir={duzenDegistir}
          secenekler={[
            {
              id: "ayri",
              etiket: "Ayrı sayfa",
              ipucu: "Her kayıt ayrı tabloda — sürükle-bırak ile düzenlenir",
            },
            {
              id: "carsaf",
              etiket: "Çarşaf",
              ipucu: "Hepsi tek tabloda — toplu inceleme",
            },
          ]}
        />

        {duzen === "carsaf" && yogunluk && yogunlukDegistir && (
          <Segment
            deger={yogunluk}
            degistir={yogunlukDegistir}
            secenekler={[
              { id: "rahat", etiket: "Rahat", ipucu: "Büyük hücreler, okunur yazı; gerekirse yatay kayar" },
              { id: "sikisik", etiket: "Sıkışık", ipucu: "Haftayı tek ekrana sığdırır" },
            ]}
          />
        )}
        {duzen === "carsaf" && saatGosterDegistir && (
          <label className="flex cursor-pointer items-center gap-1.5 text-xs text-murekkep-yumusak">
            <input
              type="checkbox"
              checked={Boolean(saatGoster)}
              onChange={(e) => saatGosterDegistir(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-cizgi-guclu"
            />
            Saat sayısı
          </label>
        )}
        {duzen === "carsaf" && kapaliGosterDegistir && (
          <label
            className="flex cursor-pointer items-center gap-1.5 text-xs text-murekkep-yumusak"
            title="Kapalı saatleri (×) göster. Öğretmenlere dağıtılacak çıktı için kapatın."
          >
            <input
              type="checkbox"
              checked={Boolean(kapaliGoster)}
              onChange={(e) => kapaliGosterDegistir(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-cizgi-guclu"
            />
            Kapalı saatler
          </label>
        )}

        <div className="ml-auto flex shrink-0 gap-1.5">
          <Buton tur="ikincil" onClick={yazdir} title="Yazdır">
            <Printer className="h-4 w-4" />
            <span className="hidden sm:inline">Yazdır</span>
          </Buton>
          <PdfMenusu seciliAnahtar={seciliAnahtar} bakis={bakis} duzen={duzen} indir={pdfIndir} />
          <Buton tur="ikincil" onClick={() => indir("xlsx")} title="Excel indir">
            <FileSpreadsheet className="h-4 w-4" />
            <span className="hidden sm:inline">Excel</span>
          </Buton>
        </div>
      </div>

      {(anahtarlar.length > 0 || baslik || ozet) && (
        <div className="flex items-center gap-3">
          {anahtarlar.length > 0 ? (
            // Sağ kenardaki soluklaşma, listenin devam ettiğini belli eder.
            <div
              className="flex min-w-0 flex-1 gap-1.5 overflow-x-auto pb-0.5"
              style={{
                maskImage:
                  "linear-gradient(to right, #000 calc(100% - 28px), transparent 100%)",
                WebkitMaskImage:
                  "linear-gradient(to right, #000 calc(100% - 28px), transparent 100%)",
              }}
            >
              {anahtarlar.map((a) => (
                <button
                  key={a}
                  onClick={() => anahtarDegistir(a)}
                  className={clsx(
                    "shrink-0 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors",
                    a === seciliAnahtar
                      ? "bg-murekkep text-uzeri"
                      : "border border-cizgi-guclu bg-yuzey text-murekkep-yumusak hover:bg-yuzey-alt",
                  )}
                >
                  {a}
                </button>
              ))}
            </div>
          ) : (
            <span className="min-w-0 flex-1 truncate text-sm font-medium text-murekkep">
              {baslik}
            </span>
          )}
          {ozet && (
            <div className="hidden shrink-0 gap-3 text-xs text-murekkep-silik sm:flex">
              {ozet}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
