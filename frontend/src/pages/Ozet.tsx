/** Kurulum ilerlemesi ve kısayollar. */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";

import { Buton, Kart, SayfaBasligi, Yukleniyor } from "../components/ui";
import { get } from "../lib/api";
import type { Ders, Gun, MufredatSatiri, Ogretmen, Program, Sube } from "../lib/types";

export default function Ozet() {
  const ogretmenler = useQuery({ queryKey: ["ogretmenler"], queryFn: () => get<Ogretmen[]>("/teachers") });
  const dersler = useQuery({ queryKey: ["dersler"], queryFn: () => get<Ders[]>("/subjects") });
  const subeler = useQuery({ queryKey: ["subeler"], queryFn: () => get<Sube[]>("/sections") });
  const mufredat = useQuery({ queryKey: ["mufredat-hepsi"], queryFn: () => get<MufredatSatiri[]>("/curriculum") });
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const programlar = useQuery({ queryKey: ["programlar"], queryFn: () => get<Program[]>("/timetables") });

  if (
    [ogretmenler, dersler, subeler, mufredat, izgara, programlar].some((q) => q.isLoading)
  )
    return <Yukleniyor />;

  const haftalikSaat = (izgara.data ?? [])
    .filter((g) => g.is_active)
    .reduce((t, g) => t + g.periods.filter((p) => !p.is_break).length, 0);
  const toplamYuk = (mufredat.data ?? []).reduce((t, m) => t + m.weekly_hours, 0);

  const adimlar = [
    {
      ad: "Zaman ızgarasını tanımlayın",
      yol: "/zaman-izgarasi",
      tamam: haftalikSaat > 0,
      not: `${haftalikSaat} ders saati`,
    },
    { ad: "Dersleri girin", yol: "/dersler", tamam: (dersler.data?.length ?? 0) > 0, not: `${dersler.data?.length ?? 0} ders` },
    { ad: "Öğretmenleri girin", yol: "/ogretmenler", tamam: (ogretmenler.data?.length ?? 0) > 0, not: `${ogretmenler.data?.length ?? 0} öğretmen` },
    { ad: "Şubeleri girin", yol: "/subeler", tamam: (subeler.data?.length ?? 0) > 0, not: `${subeler.data?.length ?? 0} şube` },
    { ad: "Ders atamalarını yapın", yol: "/ders-atamalari", tamam: (mufredat.data?.length ?? 0) > 0, not: `${toplamYuk} saat yük` },
    { ad: "Programı üretin", yol: "/programlar", tamam: (programlar.data?.length ?? 0) > 0, not: `${programlar.data?.length ?? 0} program` },
  ];

  const kalan = adimlar.filter((a) => !a.tamam).length;

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Özet"
        aciklama={
          kalan === 0
            ? "Tüm tanımlar hazır. Programınızı üretebilirsiniz."
            : `Program üretmeden önce ${kalan} adım kaldı.`
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ["Haftalık ders saati", haftalikSaat],
          ["Toplam ders yükü", `${toplamYuk} saat`],
          ["Doluluk", haftalikSaat ? `%${Math.round((toplamYuk / (haftalikSaat * Math.max(1, subeler.data?.length ?? 1))) * 100)}` : "—"],
        ].map(([etiket, deger]) => (
          <Kart key={etiket as string}>
            <p className="text-2xs font-semibold uppercase tracking-[0.08em] text-murekkep-silik">
              {etiket}
            </p>
            <p className="sayisal mt-1.5 font-baslik text-3xl font-semibold tracking-tight text-murekkep">
              {deger}
            </p>
          </Kart>
        ))}
      </div>

      <Kart baslik="Kurulum adımları">
        <ol className="divide-y divide-cizgi">
          {adimlar.map((a) => (
            <li key={a.yol} className="flex items-center gap-3 py-3">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                  a.tamam ? "bg-basari-zemin text-basari" : "bg-yuzey-alt text-murekkep-silik"
                }`}
              >
                {a.tamam ? <Check className="h-3.5 w-3.5" /> : "•"}
              </span>
              <span className="flex-1 text-sm font-medium text-murekkep">{a.ad}</span>
              <span className="sayisal text-sm text-murekkep-silik">{a.not}</span>
              <Link to={a.yol}>
                <Buton tur="sade">
                  <ArrowRight className="h-4 w-4" />
                </Buton>
              </Link>
            </li>
          ))}
        </ol>
      </Kart>
    </div>
  );
}
