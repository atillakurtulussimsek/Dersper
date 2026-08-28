/** Çözümsüzlük raporu: sayısal bulgular + yapay zekanın sade Türkçe açıklaması. */
import { AlertTriangle, Ban, Sparkles } from "lucide-react";

import { Kart, Rozet, Uyari } from "./ui";
import type { Deneme } from "../lib/types";

function Markdown({ metin }: { metin: string }) {
  // Yapay zekadan gelen sade markdown: başlık, madde, kalın.
  const satirlar = metin.split("\n");
  return (
    <div className="space-y-1.5 text-sm leading-relaxed text-slate-700">
      {satirlar.map((s, i) => {
        const t = s.trim();
        if (!t) return <div key={i} className="h-1" />;
        if (/^#{1,6}\s/.test(t))
          return (
            <p key={i} className="pt-2 font-semibold text-slate-900">
              {t.replace(/^#{1,6}\s/, "")}
            </p>
          );
        if (/^[-*]\s/.test(t))
          return (
            <p key={i} className="flex gap-2 pl-1">
              <span className="text-slate-400">•</span>
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
              <div key={etiket as string} className="rounded-lg bg-slate-50 px-3 py-2">
                <p className="text-xs text-slate-500">{etiket}</p>
                <p className="text-lg font-semibold text-slate-900">{deger}</p>
              </div>
            ))}
          </div>

          {engeller.length > 0 && (
            <div className="space-y-2">
              {engeller.map((b, i) => (
                <div
                  key={i}
                  className="flex gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3"
                >
                  <Ban className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
                  <div>
                    <p className="text-sm font-medium text-red-900">{b.baslik}</p>
                    <p className="mt-0.5 text-sm text-red-800">{b.detay}</p>
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
                  className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3"
                >
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                  <div>
                    <p className="text-sm font-medium text-amber-900">{b.baslik}</p>
                    <p className="mt-0.5 text-sm text-amber-800">{b.detay}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {rapor.yerlesmeyenler.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-2 font-medium">Şube</th>
                    <th className="px-3 py-2 font-medium">Ders</th>
                    <th className="px-3 py-2 font-medium">Öğretmen</th>
                    <th className="px-3 py-2 font-medium">Yerleşmeyen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rapor.yerlesmeyenler.map((y, i) => (
                    <tr key={i}>
                      <td className="px-3 py-2">{y.sube}</td>
                      <td className="px-3 py-2">{y.ders}</td>
                      <td className="px-3 py-2 text-slate-600">{y.ogretmen}</td>
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
        sag={<Sparkles className="h-4 w-4 text-slate-400" />}
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
