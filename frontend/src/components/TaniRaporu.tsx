/** Çözümsüzlük raporu: sayısal bulgular + yapay zekanın sade Türkçe açıklaması. */
import { AlertTriangle, Ban, Sparkles } from "lucide-react";

import { Kart, Rozet, Uyari } from "./ui";
import type { Deneme } from "../lib/types";

function Markdown({ metin }: { metin: string }) {
  // Yapay zekadan gelen sade markdown: başlık, madde, kalın.
  const satirlar = metin.split("\n");
  return (
    <div className="space-y-1.5 text-sm leading-relaxed text-murekkep-yumusak">
      {satirlar.map((s, i) => {
        const t = s.trim();
        if (!t) return <div key={i} className="h-1" />;
        if (/^#{1,6}\s/.test(t))
          return (
            <p key={i} className="pt-2 font-semibold text-murekkep">
              {t.replace(/^#{1,6}\s/, "")}
            </p>
          );
        if (/^[-*]\s/.test(t))
          return (
            <p key={i} className="flex gap-2 pl-1">
              <span className="text-murekkep-silik">•</span>
              <span>{kalin(t.replace(/^[-*]\s/, ""))}</span>
            </p>
          );
        return <p key={i}>{kalin(t)}</p>;
      })}
    </div>
  );
}

function kalin(s: string) {
  return s.split(/\*\*(.+?)\*\*/g).map((parca, i) =>
    i % 2 === 1 ? <b key={i}>{parca}</b> : <span key={i}>{parca}</span>,
  );
}

export default function TaniRaporu({ deneme }: { deneme: Deneme }) {
  const rapor = deneme.report;
  if (!rapor) return null;

  const engeller = rapor.bulgular.filter((b) => b.onem === "engel");
  const uyarilar = rapor.bulgular.filter((b) => b.onem === "uyari");
  const celiskiler = rapor.celiskiler ?? [];
  // Tek başına değiştirmesi yeten kısıtlar önce: kullanıcının en kısa çıkışı.
  const cikislar = celiskiler.filter((c) => c.tek_basina_yeterli === true);
  const belirsizler = celiskiler.filter((c) => c.tek_basina_yeterli === null);
  // Ne kesin engel ne çelişki çekirdeği varsa gevşek çözümden türeyen
  // ipuçları gösterilir; kesin bir neden varken "bulunamadı" demek yanlış olur.
  const sikisiklik =
    celiskiler.length === 0 && engeller.length === 0 ? (rapor.sikisiklik ?? []) : [];

  return (
    <div className="space-y-4">
      <Kart
        baslik={
          deneme.status === "calisiyor"
            ? "Son denemede tıkanan noktalar"
            : "Program neden tamamlanamadı"
        }
        aciklama={`${rapor.ozet.yerlesmeyen_toplam} ders saati yerleşemedi · ${rapor.sure_sn} sn`}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Haftalık ders saati", rapor.ozet.ders_saati_sayisi],
              ["Toplam yük", `${rapor.ozet.toplam_ders_saati} saat`],
              ["Şube", rapor.ozet.sube_sayisi],
              ["Öğretmen", rapor.ozet.ogretmen_sayisi],
            ].map(([etiket, deger]) => (
              <div key={etiket as string} className="rounded-lg bg-yuzey-alt px-3 py-2">
                <p className="text-xs text-murekkep-silik">{etiket}</p>
                <p className="text-lg font-semibold text-murekkep">{deger}</p>
              </div>
            ))}
          </div>

          {celiskiler.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-murekkep">
                Şu kısıtlar birlikte çelişiyor:
              </p>
              <ul className="space-y-1.5">
                {celiskiler.map((c, i) => (
                  <li
                    key={i}
                    className="flex gap-2.5 rounded-lg border border-cizgi bg-yuzey-alt px-3 py-2"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-murekkep-silik" />
                    <span className="text-sm">
                      <span className="text-murekkep">{c.metin}</span>
                      <span className="mt-0.5 block text-xs text-murekkep-silik">
                        {c.oneri}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>

              {cikislar.length > 0 && (
                <div className="rounded-lg border border-basari/25 bg-basari-zemin px-4 py-3">
                  <p className="text-sm font-medium text-basari">
                    Bunlardan <b>yalnızca birini</b> değiştirmek yeterli:
                  </p>
                  <ul className="mt-1 space-y-0.5">
                    {cikislar.map((c, i) => (
                      <li key={i} className="text-sm text-basari">
                        · {c.oneri}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {cikislar.length === 0 && belirsizler.length > 0 && (
                <p className="text-xs text-murekkep-silik">
                  Tek başına hangisinin yeteceği sınanamadı (süre yetmedi); listedekilerden
                  birini gevşetip yeniden üretmeyi deneyin.
                </p>
              )}
              {cikislar.length === 0 && belirsizler.length === 0 && (
                <p className="text-xs text-murekkep-silik">
                  Hiçbiri tek başına yetmiyor; birden fazlasını birlikte gevşetmek gerekir.
                </p>
              )}
            </div>
          )}

          {sikisiklik.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-murekkep">
                Kesin bir çelişki bulunamadı; yerleşemeyen derslerin en sıkışık noktaları:
              </p>
              <ul className="space-y-1.5">
                {sikisiklik.map((k, i) => (
                  <li
                    key={i}
                    className="flex gap-2.5 rounded-lg border border-cizgi bg-yuzey-alt px-3 py-2"
                  >
                    <span
                      className={
                        k.oran >= 90
                          ? "sayisal mt-0.5 shrink-0 rounded-md bg-hata-zemin px-1.5 text-xs font-semibold text-hata"
                          : "sayisal mt-0.5 shrink-0 rounded-md bg-uyari-zemin px-1.5 text-xs font-semibold text-uyari"
                      }
                    >
                      {k.oran > 100 ? "%100+" : `%${k.oran}`}
                    </span>
                    <span className="text-sm">
                      <span className="text-murekkep">{k.metin}</span>
                      <span className="mt-0.5 block text-xs text-murekkep-silik">{k.oneri}</span>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-murekkep-silik">
                Oran = haftalık yük / açık saat. %100'e yaklaştıkça o kaynağa ders sığdırmak
                zorlaşır; en yüksek olandan başlayın.
              </p>
            </div>
          )}

          {engeller.length > 0 && (
            <div className="space-y-2">
              {engeller.map((b, i) => (
                <div
                  key={i}
                  className="flex gap-3 rounded-lg border border-hata/25 bg-hata-zemin px-4 py-3"
                >
                  <Ban className="mt-0.5 h-4 w-4 shrink-0 text-hata" />
                  <div>
                    <p className="text-sm font-medium text-hata">{b.baslik}</p>
                    <p className="mt-0.5 text-sm text-hata">{b.detay}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {uyarilar.length > 0 && (
            <div className="space-y-2">
              {uyarilar.map((b, i) => (
                <div
                  key={i}
                  className="flex gap-3 rounded-lg border border-uyari/25 bg-uyari-zemin px-4 py-3"
                >
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-uyari" />
                  <div>
                    <p className="text-sm font-medium text-uyari">{b.baslik}</p>
                    <p className="mt-0.5 text-sm text-uyari">{b.detay}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {rapor.yerlesmeyenler.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-cizgi">
              <table className="w-full text-sm">
                <thead className="bg-yuzey-alt text-left text-xs uppercase tracking-wide text-murekkep-silik">
                  <tr>
                    <th className="px-3 py-2 font-medium">Şube</th>
                    <th className="px-3 py-2 font-medium">Ders</th>
                    <th className="px-3 py-2 font-medium">Öğretmen</th>
                    <th className="px-3 py-2 font-medium">Yerleşmeyen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cizgi">
                  {rapor.yerlesmeyenler.map((y, i) => (
                    <tr key={i}>
                      <td className="px-3 py-2">{y.sube}</td>
                      <td className="px-3 py-2">{y.ders}</td>
                      <td className="px-3 py-2 text-murekkep-yumusak">{y.ogretmen}</td>
                      <td className="px-3 py-2">
                        <Rozet tur="kotu">
                          {y.yerlesmeyen_saat} / {y.istenen_saat} saat
                        </Rozet>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Kart>

      <Kart
        baslik="Yapay zeka yorumu"
        aciklama="Raporun sade Türkçe özeti ve öneriler"
        sag={<Sparkles className="h-4 w-4 text-murekkep-silik" />}
      >
        {deneme.ai_explanation ? (
          <Markdown metin={deneme.ai_explanation} />
        ) : (
          <Uyari>
            Yapay zeka kapalı. Ayarlar &gt; Yapay Zeka bölümünden kendi API anahtarınızı
            girerseniz, bu tıkanmanın sebebini ve çözüm önerilerini sade bir dille
            açıklayabilir.
          </Uyari>
        )}
      </Kart>
    </div>
  );
}
