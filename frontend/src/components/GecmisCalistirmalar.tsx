/** Bu program için yapılmış tüm üretim çalıştırmaları. */
import { Kart, Rozet, Tablo } from "./ui";
import { sureMetni } from "./UretimIzleme";
import type { Deneme, DenemeDurumu } from "../lib/types";

const DURUM: Record<DenemeDurumu, { etiket: string; tur: "notr" | "iyi" | "uyari" | "kotu" }> = {
  bekliyor: { etiket: "Bekliyor", tur: "notr" },
  calisiyor: { etiket: "Çalışıyor", tur: "uyari" },
  basarili: { etiket: "Başarılı", tur: "iyi" },
  cozumsuz: { etiket: "Yerleşmedi", tur: "kotu" },
  durduruldu: { etiket: "Durduruldu", tur: "notr" },
  hata: { etiket: "Hata", tur: "kotu" },
};

export default function GecmisCalistirmalar({ denemeler }: { denemeler: Deneme[] }) {
  if (!denemeler.length) return null;

  return (
    <Kart
      baslik="Geçmiş çalıştırmalar"
      aciklama="Bu program için yapılan tüm üretim denemeleri."
      katlanir
      ozet={`${denemeler.length} çalıştırma`}
    >
      <Tablo basliklar={["Başlangıç", "Durum", "Deneme", "Süre", "En iyi yerleşim"]}>
        {denemeler.map((d) => (
          <tr key={d.id} className="hover:bg-yuzey-alt">
            <td className="px-3 py-2.5 text-murekkep-yumusak">
              {new Date(d.started_at + "Z").toLocaleString("tr-TR")}
            </td>
            <td className="px-3 py-2.5">
              <span className="flex items-center gap-2">
                <Rozet tur={DURUM[d.status].tur}>{DURUM[d.status].etiket}</Rozet>
                {d.proven_infeasible && (
                  <span className="text-xs text-uyari">kısıtlar çelişiyor</span>
                )}
              </span>
            </td>
            <td className="px-3 py-2.5 tabular-nums text-murekkep-yumusak">{d.attempts}</td>
            <td className="px-3 py-2.5 tabular-nums text-murekkep-yumusak">
              {d.seconds != null ? sureMetni(d.seconds) : "—"}
            </td>
            <td className="px-3 py-2.5 tabular-nums text-murekkep-yumusak">
              {d.required ? `${d.best_placed} / ${d.required} saat` : "—"}
            </td>
          </tr>
        ))}
      </Tablo>
    </Kart>
  );
}
