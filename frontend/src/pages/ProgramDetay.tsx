/** Tek bir ders programı: üretim, ızgara, elle düzenleme, çıktı, yayın. */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import {
  Copy, Download, FileSpreadsheet, Globe, Play, Printer,
} from "lucide-react";
import clsx from "clsx";

import ProgramIzgarasi, { type Bakis } from "../components/ProgramIzgarasi";
import TaniRaporu from "../components/TaniRaporu";
import { Buton, Kart, Rozet, Secim, Uyari, Yukleniyor } from "../components/ui";
import { get, jetonuAl, patch, post } from "../lib/api";
import type { Deneme, Gun, Izgara, Program } from "../lib/types";

export default function ProgramDetay() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [bakis, setBakis] = useState<Bakis>("sube");
  // Çıktı düzeni: her şubeye ayrı sayfa mı, hepsi tek çarşafta mı.
  const [duzen, setDuzen] = useState<"ayri" | "carsaf">("ayri");
  const [anahtar, setAnahtar] = useState<string | null>(null);
  const [tasimaHatasi, setTasimaHatasi] = useState<string | null>(null);

  const izgaraSorgu = useQuery({
    queryKey: ["izgara", id],
    queryFn: () => get<Izgara>(`/timetables/${id}/grid`),
  });
  const gunler = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const denemeler = useQuery({
    queryKey: ["denemeler", id],
    queryFn: () => get<Deneme[]>(`/timetables/${id}/runs`),
  });

  const uret = useMutation({
    mutationFn: () => post<Deneme>(`/timetables/${id}/solve?time_limit_seconds=45`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["izgara", id] });
      qc.invalidateQueries({ queryKey: ["denemeler", id] });
    },
  });

  const tasi = useMutation({
    mutationFn: ({ atama, saat }: { atama: number; saat: number }) =>
      patch<Izgara>(`/timetables/${id}/assignments/${atama}`, { period_id: saat }),
    onSuccess: (veri) => {
      setTasimaHatasi(null);
      qc.setQueryData(["izgara", id], veri);
    },
    onError: (e: Error) => setTasimaHatasi(e.message),
  });

  const kilitle = useMutation({
    mutationFn: (atama: number) =>
      post<Izgara>(`/timetables/${id}/assignments/${atama}/lock`),
    onSuccess: (veri) => qc.setQueryData(["izgara", id], veri),
  });

  const yayin = useMutation({
    mutationFn: (ac: boolean) =>
      post<Program>(`/timetables/${id}/${ac ? "publish" : "unpublish"}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["izgara", id] }),
  });

  const hucreler = izgaraSorgu.data?.cells ?? [];
  const anahtarlar = useMemo(() => {
    const set = new Set(
      hucreler.map((h) => (bakis === "sube" ? h.section_name : h.teacher_name)),
    );
    return [...set].sort((a, b) => a.localeCompare(b, "tr"));
  }, [hucreler, bakis]);

  const seciliAnahtar = anahtar && anahtarlar.includes(anahtar) ? anahtar : anahtarlar[0];
  const sonDeneme = denemeler.data?.[0];
  const gosterRapor =
    sonDeneme && sonDeneme.status !== "basarili" && sonDeneme.report !== null;

  if (izgaraSorgu.isLoading || gunler.isLoading) return <Yukleniyor />;
  if (izgaraSorgu.error)
    return <Uyari tur="hata">{(izgaraSorgu.error as Error).message}</Uyari>;

  const program = izgaraSorgu.data!.timetable;

  function ciktiAdresi(bicim: "pdf" | "xlsx" | "html") {
    // Çıktı uçları jeton ister; yeni sekmede açmak için sorgu dizesiyle taşınamaz,
    // bu yüzden fetch ile indirilir.
    return `/api/timetables/${id}/export/${bicim}?bakis=${bakis}&duzen=${duzen}`;
  }

  async function indir(bicim: "pdf" | "xlsx") {
    const yanit = await fetch(ciktiAdresi(bicim), {
      headers: { Authorization: `Bearer ${jetonuAl() ?? ""}` },
    });
    if (!yanit.ok) {
      const govde = await yanit.json().catch(() => null);
      setTasimaHatasi(govde?.detail ?? "Çıktı alınamadı.");
      return;
    }
    const blob = await yanit.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ders-programi-${duzen}-${bakis}.${bicim}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function yazdir() {
    const yanit = await fetch(ciktiAdresi("html"), {
      headers: { Authorization: `Bearer ${jetonuAl() ?? ""}` },
    });
    const html = await yanit.text();
    const pencere = window.open("", "_blank");
    if (!pencere) return;
    pencere.document.write(html);
    pencere.document.close();
    pencere.focus();
    pencere.print();
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{program.name}</h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-slate-500">
            <Rozet
              tur={
                program.status === "yayinda"
                  ? "uyari"
                  : program.status === "uretildi"
                    ? "iyi"
                    : "notr"
              }
            >
              {program.status === "yayinda"
                ? "Yayında"
                : program.status === "uretildi"
                  ? "Üretildi"
                  : "Taslak"}
            </Rozet>
            {hucreler.length} ders saati yerleşmiş
          </p>
        </div>
        <Buton onClick={() => uret.mutate()} yukleniyor={uret.isPending}>
          <Play className="h-4 w-4" />
          {hucreler.length ? "Yeniden üret" : "Programı üret"}
        </Buton>
      </header>

      {uret.isPending && (
        <Uyari>
          Program üretiliyor. Okulun büyüklüğüne göre bu işlem bir dakikaya kadar
          sürebilir.
        </Uyari>
      )}
      {uret.error && <Uyari tur="hata">{(uret.error as Error).message}</Uyari>}
      {tasimaHatasi && <Uyari tur="hata">{tasimaHatasi}</Uyari>}
      {sonDeneme?.status === "basarili" && !uret.isPending && (
        <Uyari tur="basari">
          Program eksiksiz yerleşti ({sonDeneme.seconds?.toFixed(1)} sn). Hücreleri
          sürükleyerek elle düzenleyebilir, çift tıklayarak kilitleyebilirsiniz.
        </Uyari>
      )}

      {gosterRapor && <TaniRaporu deneme={sonDeneme!} />}

      {hucreler.length > 0 && (
        <Kart
          baslik="Haftalık program"
          sag={
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex rounded-lg border border-slate-300 p-0.5">
                {(["sube", "ogretmen"] as Bakis[]).map((b) => (
                  <button
                    key={b}
                    onClick={() => {
                      setBakis(b);
                      setAnahtar(null);
                    }}
                    className={clsx(
                      "rounded-md px-2.5 py-1 text-xs font-medium",
                      bakis === b ? "bg-slate-900 text-white" : "text-slate-600",
                    )}
                  >
                    {b === "sube" ? "Şube" : "Öğretmen"}
                  </button>
                ))}
              </div>
              <Secim
                value={seciliAnahtar ?? ""}
                onChange={(e) => setAnahtar(e.target.value)}
                className="w-auto"
              >
                {anahtarlar.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </Secim>
              <div className="flex rounded-lg border border-slate-300 p-0.5">
                {(
                  [
                    ["ayri", "Ayrı sayfa"],
                    ["carsaf", "Çarşaf"],
                  ] as const
                ).map(([d, etiket]) => (
                  <button
                    key={d}
                    onClick={() => setDuzen(d)}
                    title={
                      d === "carsaf"
                        ? "Tüm şubeler/öğretmenler tek sayfada, toplu liste"
                        : "Her şube/öğretmen için ayrı sayfa"
                    }
                    className={clsx(
                      "rounded-md px-2.5 py-1 text-xs font-medium",
                      duzen === d ? "bg-slate-900 text-white" : "text-slate-600",
                    )}
                  >
                    {etiket}
                  </button>
                ))}
              </div>
              <Buton tur="ikincil" onClick={yazdir}>
                <Printer className="h-4 w-4" /> Yazdır
              </Buton>
              <Buton tur="ikincil" onClick={() => indir("pdf")}>
                <Download className="h-4 w-4" /> PDF
              </Buton>
              <Buton tur="ikincil" onClick={() => indir("xlsx")}>
                <FileSpreadsheet className="h-4 w-4" /> Excel
              </Buton>
            </div>
          }
        >
          {duzen === "carsaf" && (
            <div className="mb-4">
              <Uyari>
                Çıktı düzeni <b>çarşaf</b> seçili: yazdırma, PDF ve Excel çıktılarında
                tüm {bakis === "sube" ? "şubeler" : "öğretmenler"} tek sayfada, toplu
                liste olarak gelir. Aşağıdaki ekran görünümü tek tek gösterir.
              </Uyari>
            </div>
          )}
          {seciliAnahtar && (
            <ProgramIzgarasi
              gunler={gunler.data ?? []}
              hucreler={hucreler}
              bakis={bakis}
              anahtar={seciliAnahtar}
              tasi={(atama, saat) => tasi.mutate({ atama, saat })}
              kilitle={(atama) => kilitle.mutate(atama)}
            />
          )}
        </Kart>
      )}

      {hucreler.length > 0 && (
        <Kart
          baslik="Yayın"
          aciklama="Yayınlanan program, girişe gerek kalmadan bir bağlantı üzerinden görüntülenebilir."
          sag={<Globe className="h-4 w-4 text-slate-400" />}
        >
          {program.public_token ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <code className="flex-1 truncate rounded-lg bg-slate-100 px-3 py-2 text-sm">
                  {`${location.origin}/p/${program.public_token}`}
                </code>
                <Buton
                  tur="ikincil"
                  onClick={() =>
                    navigator.clipboard.writeText(
                      `${location.origin}/p/${program.public_token}`,
                    )
                  }
                >
                  <Copy className="h-4 w-4" /> Kopyala
                </Buton>
              </div>
              <Buton tur="tehlike" onClick={() => yayin.mutate(false)} yukleniyor={yayin.isPending}>
                Yayından kaldır
              </Buton>
            </div>
          ) : (
            <Buton onClick={() => yayin.mutate(true)} yukleniyor={yayin.isPending}>
              <Globe className="h-4 w-4" /> Yayınla
            </Buton>
          )}
        </Kart>
      )}
    </div>
  );
}
