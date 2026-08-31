/** Kurulum ilerlemesi ve kısayollar. */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";

import { Buton, Kart, SayfaBasligi, Yukleniyor } from "../components/ui";
import { get } from "../lib/api";
import type {
  Ders, Gun, KapaliSaatler, MufredatSatiri, Ogretmen, Program, Sube,
} from "../lib/types";

export default function Ozet() {
  const ogretmenler = useQuery({ queryKey: ["ogretmenler"], queryFn: () => get<Ogretmen[]>("/teachers") });
  const dersler = useQuery({ queryKey: ["dersler"], queryFn: () => get<Ders[]>("/subjects") });
  const subeler = useQuery({ queryKey: ["subeler"], queryFn: () => get<Sube[]>("/sections") });
  const mufredat = useQuery({ queryKey: ["mufredat-hepsi"], queryFn: () => get<MufredatSatiri[]>("/curriculum") });
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const programlar = useQuery({ queryKey: ["programlar"], queryFn: () => get<Program[]>("/timetables") });
  // Şubeler kendi saatlerini kapatmış olabilir; kapasite buna göre hesaplanır.
  const kapali = useQuery({
    queryKey: ["kapali-saatler"],
    queryFn: () => get<KapaliSaatler>("/availability/closed"),
  });

  if (
    [ogretmenler, dersler, subeler, mufredat, izgara, programlar, kapali]
      .some((q) => q.isLoading)
  )
    return <Yukleniyor />;

  // Ders KONULABİLEN saatler: aktif günlerin teneffüs olmayan ders saatleri.
  // Doluluğun paydası bunlardan çıkar.
  const yerlestirilebilir = new Set<number>();
  for (const g of izgara.data ?? []) {
    if (!g.is_active) continue;
    for (const p of g.periods) if (!p.is_break) yerlestirilebilir.add(p.id);
  }
  const haftalikSaat = yerlestirilebilir.size;

  // Programa girecek olanlar: çözücü pasif şube/ders/öğretmenin dersini
  // yerleştirmez, bu yüzden yükte de kapasitede de sayılmazlar.
  const aktifSubeler = (subeler.data ?? []).filter((s) => s.is_active);
  const sayilanYuk = (mufredat.data ?? []).filter(
    (m) => m.section.is_active && m.subject.is_active && m.teacher.is_active,
  );
  const toplamYuk = sayilanYuk.reduce((t, m) => t + m.weekly_hours, 0);

  // Kapasite şube şube toplanır: her şubenin kendi kapattığı saatler düşülür.
  // Eskiden payda "haftalık saat × şube sayısı" idi; akşamcı bir şubenin
  // kapattığı saatler de kapasite sayıldığından oran gerçekte olduğundan
  // düşük çıkıyordu.
  //
  // Kapalı işareti teneffüse konmuş olabilir; yalnızca ders konulabilen
  // saatlerdekiler sayılır, yoksa aynı saat iki kez düşülürdü.
  const kapasite = aktifSubeler.reduce((t, s) => {
    const kapaliSaat = (kapali.data?.sections[s.id] ?? []).filter((pid) =>
      yerlestirilebilir.has(pid),
    ).length;
    return t + Math.max(0, haftalikSaat - kapaliSaat);
  }, 0);
  const doluluk = kapasite > 0 ? Math.round((toplamYuk / kapasite) * 100) : null;

  /** "5 şube" ya da pasif kayıt varsa "5 şube · 1 pasif".
   *  Kartlar aktif kayıtları sayıyor; adım listesi de aynı sayıyı göstermeli,
   *  yoksa aynı ekranda iki farklı şube sayısı görünür. */
  function sayim(kayitlar: { is_active: boolean }[] | undefined, birim: string) {
    const aktifSayi = (kayitlar ?? []).filter((k) => k.is_active).length;
    const pasif = (kayitlar ?? []).length - aktifSayi;
    return `${aktifSayi} ${birim}${pasif ? ` · ${pasif} pasif` : ""}`;
  }

  const adimlar = [
    {
      ad: "Zaman ızgarasını tanımlayın",
      yol: "/zaman-izgarasi",
      tamam: haftalikSaat > 0,
      not: `${haftalikSaat} ders saati`,
    },
    { ad: "Dersleri girin", yol: "/dersler", tamam: (dersler.data?.length ?? 0) > 0, not: sayim(dersler.data, "ders") },
    { ad: "Öğretmenleri girin", yol: "/ogretmenler", tamam: (ogretmenler.data?.length ?? 0) > 0, not: sayim(ogretmenler.data, "öğretmen") },
    { ad: "Şubeleri girin", yol: "/subeler", tamam: (subeler.data?.length ?? 0) > 0, not: sayim(subeler.data, "şube") },
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
          {
            etiket: "Haftalık ders saati",
            deger: haftalikSaat,
            alt: "aktif günlerde, teneffüsler hariç",
          },
          {
            etiket: "Toplam ders yükü",
            deger: `${toplamYuk} saat`,
            alt: `${aktifSubeler.length} şubede`,
          },
          {
            etiket: "Doluluk",
            deger: doluluk === null ? "—" : `%${doluluk}`,
            alt:
              doluluk === null
                ? "şube tanımlanmamış"
                : `${toplamYuk} / ${kapasite} saat`,
          },
        ].map(({ etiket, deger, alt }) => (
          <Kart key={etiket}>
            <p className="text-2xs font-semibold uppercase tracking-[0.08em] text-murekkep-silik">
              {etiket}
            </p>
            <p className="sayisal mt-1.5 font-baslik text-3xl font-semibold tracking-tight text-murekkep">
              {deger}
            </p>
            <p className="sayisal mt-0.5 text-xs text-murekkep-silik">{alt}</p>
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
