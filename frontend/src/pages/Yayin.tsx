/** Girişsiz, herkese açık program görünümü. */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import clsx from "clsx";

import ProgramIzgarasi, { type Bakis } from "../components/ProgramIzgarasi";
import { Kart, Secim, Uyari, Yukleniyor } from "../components/ui";
import { get } from "../lib/api";
import type { Gun, Izgara } from "../lib/types";

export default function Yayin() {
  const { token } = useParams();
  const [bakis, setBakis] = useState<Bakis>("sube");
  const [anahtar, setAnahtar] = useState<string | null>(null);

  const izgara = useQuery({
    queryKey: ["yayin", token],
    queryFn: () => get<Izgara>(`/public/timetables/${token}`),
  });
  // Girişsiz uçlar: kurum ve ızgara yayın jetonundan çözülür.
  const gunler = useQuery({
    queryKey: ["yayin-izgara", token],
    queryFn: () => get<Gun[]>(`/public/timetables/${token}/timegrid`),
  });
  const kurum = useQuery({
    queryKey: ["yayin-kurum", token],
    queryFn: () =>
      get<{ name: string | null; term: string | null }>(
        `/public/timetables/${token}/institution`,
      ),
  });

  if (izgara.isLoading) return <Yukleniyor />;
  if (izgara.error)
    return (
      <div className="mx-auto max-w-lg p-10">
        <Uyari tur="hata">{(izgara.error as Error).message}</Uyari>
      </div>
    );

  const hucreler = izgara.data!.cells;
  const anahtarlar = [
    ...new Set(hucreler.map((h) => (bakis === "sube" ? h.section_name : h.teacher_name))),
  ].sort((a, b) => a.localeCompare(b, "tr"));
  const secili = anahtar && anahtarlar.includes(anahtar) ? anahtar : anahtarlar[0];

  // Yayın sayfası girişsizdir; günleri okuyamazsak hücrelerden çıkarım yaparız.
  const gunListesi: Gun[] = gunler.data?.length
    ? gunler.data
    : [...new Set(hucreler.map((h) => h.day_index))].sort().map((gi) => ({
        id: gi,
        index: gi,
        name: ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][gi] ?? `${gi + 1}. gün`,
        is_active: true,
        periods: [
          ...new Set(hucreler.filter((h) => h.day_index === gi).map((h) => h.period_index)),
        ]
          .sort((a, b) => a - b)
          .map((pi) => ({
            id: Number(`${gi}${pi}`),
            day_id: gi,
            index: pi,
            name: `${pi + 1}. ders`,
            start_time: null,
            end_time: null,
            is_break: false,
            is_lunch: false,
          })),
      }));

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-6 sm:p-10">
      <header className="ray">
        <p className="text-sm text-murekkep-silik">
          {[kurum.data?.name, kurum.data?.term].filter(Boolean).join(" · ")}
        </p>
        <h1 className="font-baslik text-2xl font-semibold tracking-tight text-murekkep">
          {izgara.data!.timetable.name}
        </h1>
      </header>

      <Kart
        sag={
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-cizgi-guclu p-0.5">
              {(["sube", "ogretmen"] as Bakis[]).map((b) => (
                <button
                  key={b}
                  onClick={() => {
                    setBakis(b);
                    setAnahtar(null);
                  }}
                  className={clsx(
                    "rounded-md px-2.5 py-1 text-xs font-medium",
                    bakis === b ? "bg-murekkep text-uzeri" : "text-murekkep-yumusak",
                  )}
                >
                  {b === "sube" ? "Şube" : "Öğretmen"}
                </button>
              ))}
            </div>
            <Secim
              value={secili ?? ""}
              onChange={(e) => setAnahtar(e.target.value)}
              className="w-auto"
            >
              {anahtarlar.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </Secim>
          </div>
        }
        baslik={secili}
      >
        {secili && (
          <ProgramIzgarasi
            gunler={gunListesi}
            hucreler={hucreler}
            bakis={bakis}
            anahtar={secili}
          />
        )}
      </Kart>

      <p className="text-center text-xs text-murekkep-silik">
        Dersper ile hazırlandı · açık kaynak ders dağıtım programı
      </p>
    </div>
  );
}
