/** Ders programı ekranının araç çubuğu: bakış, düzen, kayıt seçimi ve çıktılar.
 *  Tek satırda toplanır, tabloyla birlikte kaydırılmasın diye yapışkandır.
 *
 *  Düzen seçimi hem ekranı hem çıktıyı belirler: ne görüyorsanız onu
 *  yazdırırsınız. Kayıt şeritleri yalnızca ayrı sayfa düzeninde anlamlıdır,
 *  çarşafta zaten hepsi görünür — o durumda çağıran boş liste geçirir. */
import { Download, FileSpreadsheet, Printer } from "lucide-react";
import clsx from "clsx";

import { Buton } from "./ui";
import type { Bakis } from "./ProgramIzgarasi";

export type Duzen = "ayri" | "carsaf";

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
  yazdir,
  indir,
}: {
  bakis: Bakis;
  bakisDegistir: (b: Bakis) => void;
  duzen: Duzen;
  duzenDegistir: (d: Duzen) => void;
  anahtarlar: string[];
  seciliAnahtar?: string;
  anahtarDegistir: (a: string) => void;
  yazdir: () => void;
  indir: (bicim: "pdf" | "xlsx") => void;
}) {
  return (
    <div className="sticky top-0 z-20 -mx-5 -mt-5 mb-4 space-y-2.5 border-b border-cizgi bg-yuzey/95 px-5 py-3 backdrop-blur">
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

        <div className="ml-auto flex shrink-0 gap-1.5">
          <Buton tur="ikincil" onClick={yazdir} title="Yazdır">
            <Printer className="h-4 w-4" />
            <span className="hidden sm:inline">Yazdır</span>
          </Buton>
          <Buton tur="ikincil" onClick={() => indir("pdf")} title="PDF indir">
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">PDF</span>
          </Buton>
          <Buton tur="ikincil" onClick={() => indir("xlsx")} title="Excel indir">
            <FileSpreadsheet className="h-4 w-4" />
            <span className="hidden sm:inline">Excel</span>
          </Buton>
        </div>
      </div>

      {anahtarlar.length > 0 && (
        // Sağ kenardaki soluklaşma, listenin devam ettiğini belli eder.
        <div
          className="flex gap-1.5 overflow-x-auto pb-0.5"
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
      )}
    </div>
  );
}
