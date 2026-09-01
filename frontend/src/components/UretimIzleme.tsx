/** Arka planda süren program üretiminin canlı izlemesi.
 *
 *  Üretim sunucuda çalışır; bu ekran kapatılsa da sürer. Burada kaç deneme
 *  yapıldığı, ne kadar süredir çalıştığı ve en iyi denemede kaç ders saatinin
 *  yerleştiği gösterilir.
 */
import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Square } from "lucide-react";

import { Buton, Kart } from "./ui";
import { post } from "../lib/api";
import type { Deneme } from "../lib/types";

/** "3 dk 12 sn" biçiminde süre. */
export function sureMetni(saniye: number): string {
  const s = Math.max(0, Math.floor(saniye));
  const saat = Math.floor(s / 3600);
  const dakika = Math.floor((s % 3600) / 60);
  const kalan = s % 60;
  if (saat) return `${saat} sa ${dakika} dk`;
  if (dakika) return `${dakika} dk ${kalan} sn`;
  return `${kalan} sn`;
}

export default function UretimIzleme({ deneme }: { deneme: Deneme }) {
  const qc = useQueryClient();
  const [simdi, setSimdi] = useState(() => Date.now());

  // Geçen süre sunucuya sormadan, saniyede bir yerelde ilerler.
  useEffect(() => {
    const t = setInterval(() => setSimdi(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const durdur = useMutation({
    mutationFn: () =>
      post<Deneme>(`/timetables/${deneme.timetable_id}/runs/${deneme.id}/stop`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["calisan-uretim"] });
      qc.invalidateQueries({ queryKey: ["denemeler"] });
    },
  });

  const gecen = (simdi - new Date(deneme.started_at + "Z").getTime()) / 1000;
  const oran = deneme.required
    ? Math.round((deneme.best_placed / deneme.required) * 100)
    : 0;

  const istatistikler: [string, string][] = [
    ["Deneme", `${deneme.attempts}`],
    ["Süre", sureMetni(gecen)],
    ["En iyi yerleşim", `${deneme.best_placed} / ${deneme.required} saat`],
    ["Kalan", `${Math.max(0, deneme.required - deneme.best_placed)} saat`],
  ];

  return (
    <Kart
      baslik="Program üretiliyor"
      aciklama="Üretim sunucuda sürüyor. Bu sayfadan ayrılabilir, sonra geri dönebilirsiniz."
      sag={
        <Buton
          tur="tehlike"
          onClick={() => durdur.mutate()}
          yukleniyor={durdur.isPending}
          disabled={deneme.stop_requested}
        >
          <Square className="h-4 w-4" />
          {deneme.stop_requested ? "Durduruluyor…" : "Durdur"}
        </Buton>
      }
    >
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm text-murekkep-yumusak">
          <Loader2 className="h-4 w-4 animate-spin text-murekkep-silik" />
          Tam yerleşim sağlanana kadar denemeye devam ediliyor.
        </div>

        <div>
          <div className="mb-1 flex justify-between text-xs text-murekkep-silik">
            <span>En iyi deneme</span>
            <span>%{oran}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-yuzey-alt">
            <div
              className="h-full rounded-full bg-vurgu transition-all duration-500"
              style={{ width: `${oran}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {istatistikler.map(([etiket, deger]) => (
            <div key={etiket} className="rounded-lg bg-yuzey-alt px-3 py-2">
              <p className="text-xs text-murekkep-silik">{etiket}</p>
              <p className="text-lg font-semibold tabular-nums text-murekkep">{deger}</p>
            </div>
          ))}
        </div>

        {deneme.proven_infeasible && (
          <div className="flex gap-3 rounded-lg border border-uyari/25 bg-uyari-zemin px-4 py-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-uyari" />
            <div className="text-sm text-uyari">
              <p className="font-medium">
                Bu kısıtlarla tam yerleşim mümkün değil — çözücü bunu kanıtladı.
              </p>
              <p className="mt-0.5 text-uyari">
                Denemeler sürüyor ama sonuç değişmeyecek. Aşağıdaki bulguları giderip
                yeniden başlatmanız gerekiyor. Denemeler arası bekleme kademeli olarak
                açıldığı için işlemci boşuna yorulmaz.
              </p>
            </div>
          </div>
        )}

      </div>
    </Kart>
  );
}
