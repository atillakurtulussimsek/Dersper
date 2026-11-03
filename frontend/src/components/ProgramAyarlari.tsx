/** Kendi zaman ızgarası olan programın ayarları: ızgara ve programa özel
 *  öğretmen/şube müsaitliği. Buradaki her değişiklik yalnızca bu programı
 *  etkiler; dönemin genel ızgarası ve müsaitlikleri olduğu gibi kalır.
 *
 *  Müsaitlik matrisi kendi kutusunda açılır; o açıkken bu pencere gizlenir,
 *  kapanınca aynı sekmeye geri dönülür. */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";

import MusaitlikMatrisi, { OGRETMEN_SOZLERI } from "./MusaitlikMatrisi";
import { Kutu, Uyari } from "./ui";
import ZamanIzgarasi from "../pages/ZamanIzgarasi";
import { get } from "../lib/api";
import type { Gun, Ogretmen, Program, Sube } from "../lib/types";

type Sekme = "izgara" | "ogretmen" | "sube";

const SEKMELER: { id: Sekme; etiket: string }[] = [
  { id: "izgara", etiket: "Zaman ızgarası" },
  { id: "ogretmen", etiket: "Öğretmen müsaitliği" },
  { id: "sube", etiket: "Şube müsaitliği" },
];

export default function ProgramAyarlari({
  program,
  kapat,
}: {
  program: Program;
  kapat: () => void;
}) {
  const [sekme, setSekme] = useState<Sekme>("izgara");
  const [matris, setMatris] = useState<
    { tur: "ogretmen"; kayit: Ogretmen } | { tur: "sube"; kayit: Sube } | null
  >(null);

  const gunler = useQuery({
    queryKey: ["timegrid", program.id],
    queryFn: () => get<Gun[]>(`/timetables/${program.id}/timegrid`),
  });
  const ogretmenler = useQuery({ queryKey: ["ogretmenler"], queryFn: () => get<Ogretmen[]>("/teachers") });
  const subeler = useQuery({ queryKey: ["subeler"], queryFn: () => get<Sube[]>("/sections") });

  const sorgu = `?timetable_id=${program.id}`;
  const programSubeleri = (subeler.data ?? []).filter(
    (s) => program.section_ids === null || program.section_ids.includes(s.id),
  );

  if (matris?.tur === "ogretmen")
    return (
      <MusaitlikMatrisi
        baslik={`${matris.kayit.full_name} · ${program.name} müsaitliği`}
        yol={`/teachers/${matris.kayit.id}`}
        sorgu={sorgu}
        aciklama="Öğretmenin bu programda derse girebileceği saatleri işaretleyin."
        gunler={gunler.data ?? []}
        kopyaHedefleri={(ogretmenler.data ?? [])
          .filter((t) => t.id !== matris.kayit.id)
          .map((t) => ({ id: t.id, name: t.full_name }))}
        kopyaAlani="teacher_ids"
        kopyaSozleri={OGRETMEN_SOZLERI}
        kapat={() => setMatris(null)}
      />
    );
  if (matris?.tur === "sube")
    return (
      <MusaitlikMatrisi
        baslik={`${matris.kayit.name} · ${program.name} müsaitliği`}
        yol={`/sections/${matris.kayit.id}`}
        sorgu={sorgu}
        aciklama="Şubenin bu programda ders görebileceği saatleri işaretleyin."
        gunler={gunler.data ?? []}
        kopyaHedefleri={programSubeleri
          .filter((s) => s.id !== matris.kayit.id)
          .map((s) => ({ id: s.id, name: s.name }))}
        kapat={() => setMatris(null)}
      />
    );

  return (
    <Kutu acik genis kapat={kapat} baslik={`${program.name} · program ayarları`}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-1.5" role="tablist">
          {SEKMELER.map((s) => (
            <button
              key={s.id}
              role="tab"
              aria-selected={sekme === s.id}
              onClick={() => setSekme(s.id)}
              className={clsx(
                "rounded-lg border px-3 py-1.5 text-sm",
                sekme === s.id
                  ? "border-cizgi-guclu bg-yuzey-alt font-medium text-murekkep"
                  : "border-cizgi text-murekkep-yumusak hover:bg-yuzey-alt",
              )}
            >
              {s.etiket}
            </button>
          ))}
        </div>

        {sekme === "izgara" && <ZamanIzgarasi programId={program.id} />}

        {sekme !== "izgara" && (
          <>
            <Uyari>
              Bu programa özel müsaitlik. Dönemin genel müsaitliği değişmez.
            </Uyari>
            <div className="flex flex-wrap gap-1.5">
              {sekme === "ogretmen"
                ? (ogretmenler.data ?? []).map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setMatris({ tur: "ogretmen", kayit: t })}
                      className="rounded-lg border border-cizgi px-2.5 py-1.5 text-sm hover:bg-yuzey-alt"
                    >
                      {t.full_name}
                    </button>
                  ))
                : programSubeleri.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => setMatris({ tur: "sube", kayit: s })}
                      className="rounded-lg border border-cizgi px-2.5 py-1.5 text-sm hover:bg-yuzey-alt"
                    >
                      {s.name}
                    </button>
                  ))}
            </div>
          </>
        )}
      </div>
    </Kutu>
  );
}
