/** Sürüm geçmişi: programda yapılan her değişiklik.
 *
 *  Üretimler ve elle düzenlemeler aynı zincirde durur. Hiçbir sürüm silinmez —
 *  geri alıp başka yöne gitseniz de terk edilen dal listede kalır ve geri
 *  yüklenebilir.
 *
 *  Liste uzayabildiği için varsayılan olarak son birkaç sürüm gösterilir.
 */
import { useState } from "react";
import { History, Play, Pencil, RotateCcw, Sparkles } from "lucide-react";
import clsx from "clsx";

import { Buton, Kart, Yukleniyor } from "./ui";
import type { Surum, SurumTuru } from "../lib/types";

const KISALTILMIS = 6;

const TUR: Record<SurumTuru, { etiket: string; Simge: typeof Play }> = {
  ilk: { etiket: "Başlangıç", Simge: Sparkles },
  uretim: { etiket: "Üretim", Simge: Play },
  elle: { etiket: "Elle", Simge: Pencil },
};

function zaman(iso: string): string {
  return new Date(iso).toLocaleString("tr-TR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

export default function SurumGecmisi({
  surumler,
  yukleniyor,
  simdiki,
  don,
  bekliyor,
}: {
  surumler: Surum[];
  yukleniyor: boolean;
  /** Programın şu an durduğu sürüm numarası. */
  simdiki: number | null;
  don: (number: number) => void;
  bekliyor: boolean;
}) {
  const [hepsi, setHepsi] = useState(false);
  const gosterilen = hepsi ? surumler : surumler.slice(0, KISALTILMIS);

  return (
    <Kart
      baslik="Sürüm geçmişi"
      aciklama="Her değişiklik bir sürüm bırakır. İstediğiniz sürüme dönebilirsiniz; sonraki sürümler silinmez."
      sag={<History className="h-4 w-4 text-murekkep-silik" />}
    >
      {yukleniyor ? (
        <Yukleniyor />
      ) : !surumler.length ? (
        <p className="text-sm text-murekkep-silik">Henüz sürüm yok.</p>
      ) : (
        <div className="space-y-1.5">
          {gosterilen.map((s) => {
            const { etiket, Simge } = TUR[s.kind];
            const bu = s.number === simdiki;
            return (
              <div
                key={s.number}
                className={clsx(
                  "flex items-center gap-3 rounded-lg border px-3 py-2",
                  bu
                    ? "border-cizgi-guclu bg-yuzey-alt"
                    : "border-cizgi hover:bg-yuzey-alt",
                )}
              >
                <span className="sayisal shrink-0 font-mono text-xs text-murekkep-silik">
                  v{s.number}
                </span>
                <Simge className="h-3.5 w-3.5 shrink-0 text-murekkep-silik" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-murekkep">{s.label}</p>
                  <p className="sayisal text-xs text-murekkep-silik">
                    {etiket} · {s.placed} ders saati · {zaman(s.created_at)}
                  </p>
                </div>
                {bu ? (
                  <span className="shrink-0 rounded-md bg-murekkep px-2 py-0.5 text-xs font-medium text-uzeri">
                    şu an
                  </span>
                ) : (
                  <Buton
                    tur="ikincil"
                    className="shrink-0"
                    disabled={bekliyor}
                    onClick={() => don(s.number)}
                    title={`v${s.number} sürümüne dön`}
                  >
                    <RotateCcw className="h-4 w-4" />
                    <span className="hidden sm:inline">Bu sürüme dön</span>
                  </Buton>
                )}
              </div>
            );
          })}

          {surumler.length > KISALTILMIS && (
            <Buton tur="sade" onClick={() => setHepsi((h) => !h)}>
              {hepsi
                ? "Yalnızca son sürümleri göster"
                : `Tümünü göster (${surumler.length} sürüm)`}
            </Buton>
          )}
        </div>
      )}
    </Kart>
  );
}
