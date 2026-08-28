/** Tek bir ders programı: üretim, ızgara, elle düzenleme, çıktı, yayın. */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Copy, Globe, Play } from "lucide-react";

import ProgramAracCubugu, { type Duzen } from "../components/ProgramAracCubugu";
import ProgramIzgarasi, { type Bakis } from "../components/ProgramIzgarasi";
import TaniRaporu from "../components/TaniRaporu";
import { Buton, Kart, Rozet, Uyari, Yukleniyor } from "../components/ui";
import { get, jetonuAl, patch, post } from "../lib/api";
import type { Deneme, Gun, Hucre, Izgara, Program } from "../lib/types";

const DURUM = {
  taslak: { etiket: "Taslak", tur: "notr" },
  uretildi: { etiket: "Üretildi", tur: "iyi" },
  yayinda: { etiket: "Yayında", tur: "uyari" },
} as const;

/** Seçili kayda ait haftalık özet: dolu saat, boş saat, en yoğun gün, boşluk. */
function ozetCikar(hucreler: Hucre[], gunler: Gun[]) {
  const gunluk = new Map<number, number[]>();
  for (const h of hucreler) {
    const liste = gunluk.get(h.day_index) ?? [];
    liste.push(h.period_index);
    gunluk.set(h.day_index, liste);
  }

  let bosluk = 0;
  let enYogun = { gun: "—", saat: 0 };
  for (const [gunIndex, saatler] of gunluk) {
    saatler.sort((a, b) => a - b);
    // İlk ve son ders arasındaki boş saatler = pencere.
    bosluk += saatler[saatler.length - 1] - saatler[0] + 1 - saatler.length;
    if (saatler.length > enYogun.saat) {
      enYogun = {
        gun: gunler.find((g) => g.index === gunIndex)?.name ?? "—",
        saat: saatler.length,
      };
    }
  }

  const toplamSlot = gunler
    .filter((g) => g.is_active)
    .reduce((t, g) => t + g.periods.filter((p) => !p.is_break).length, 0);

  return { dolu: hucreler.length, bos: Math.max(0, toplamSlot - hucreler.length), bosluk, enYogun };
}

export default function ProgramDetay() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [bakis, setBakis] = useState<Bakis>("sube");
  const [duzen, setDuzen] = useState<Duzen>("ayri");
  const [anahtar, setAnahtar] = useState<string | null>(null);
  const [hata, setHata] = useState<string | null>(null);

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
      setHata(null);
      qc.setQueryData(["izgara", id], veri);
    },
    onError: (e: Error) => setHata(e.message),
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
  const seciliHucreler = useMemo(
    () =>
      hucreler.filter((h) =>
        bakis === "sube" ? h.section_name === seciliAnahtar : h.teacher_name === seciliAnahtar,
      ),
    [hucreler, bakis, seciliAnahtar],
  );
  const ozet = useMemo(
    () => ozetCikar(seciliHucreler, gunler.data ?? []),
    [seciliHucreler, gunler.data],
  );

  const sonDeneme = denemeler.data?.[0];
  const gosterRapor = sonDeneme && sonDeneme.status !== "basarili" && sonDeneme.report !== null;

  if (izgaraSorgu.isLoading || gunler.isLoading) return <Yukleniyor />;
  if (izgaraSorgu.error)
    return <Uyari tur="hata">{(izgaraSorgu.error as Error).message}</Uyari>;

  const program = izgaraSorgu.data!.timetable;

  function ciktiAdresi(bicim: "pdf" | "xlsx" | "html") {
    return `/api/timetables/${id}/export/${bicim}?bakis=${bakis}&duzen=${duzen}`;
  }

  /** Çıktı uçları jeton ister; bu yüzden yeni sekme yerine fetch ile indirilir. */
  async function indir(bicim: "pdf" | "xlsx") {
    const yanit = await fetch(ciktiAdresi(bicim), {
      headers: { Authorization: `Bearer ${jetonuAl() ?? ""}` },
    });
    if (!yanit.ok) {
      const govde = await yanit.json().catch(() => null);
      setHata(govde?.detail ?? "Çıktı alınamadı.");
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
    <div className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold tracking-tight">{program.name}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-500">
            <Rozet tur={DURUM[program.status].tur}>{DURUM[program.status].etiket}</Rozet>
            <span>{hucreler.length} ders saati yerleşmiş</span>
            {sonDeneme?.seconds != null && (
              <span className="text-slate-400">· {sonDeneme.seconds.toFixed(1)} sn</span>
            )}
          </p>
        </div>
        <Buton onClick={() => uret.mutate()} yukleniyor={uret.isPending}>
          <Play className="h-4 w-4" />
          {hucreler.length ? "Yeniden üret" : "Programı üret"}
        </Buton>
      </header>

      {uret.isPending && (
        <Uyari>
          Program üretiliyor. Okulun büyüklüğüne göre bu işlem bir dakikaya kadar sürebilir.
        </Uyari>
      )}
      {uret.error && <Uyari tur="hata">{(uret.error as Error).message}</Uyari>}
      {hata && <Uyari tur="hata">{hata}</Uyari>}

      {gosterRapor && <TaniRaporu deneme={sonDeneme!} />}

      {hucreler.length > 0 && (
        <Kart className="overflow-hidden">
          <ProgramAracCubugu
            bakis={bakis}
            bakisDegistir={(b) => {
              setBakis(b);
              setAnahtar(null);
            }}
            duzen={duzen}
            duzenDegistir={setDuzen}
            anahtarlar={anahtarlar}
            seciliAnahtar={seciliAnahtar}
            anahtarDegistir={setAnahtar}
            yazdir={yazdir}
            indir={indir}
          />

          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-slate-900">{seciliAnahtar}</h2>
            <div className="flex flex-wrap gap-1.5 text-xs">
              {[
                ["dolu", `${ozet.dolu} saat dolu`],
                ["bos", `${ozet.bos} saat boş`],
                ["bosluk", `${ozet.bosluk} boşluk`],
                ["yogun", `en yoğun: ${ozet.enYogun.gun} (${ozet.enYogun.saat})`],
              ].map(([k, metin]) => (
                <span
                  key={k}
                  className="rounded-md bg-slate-100 px-2 py-1 font-medium text-slate-600"
                >
                  {metin}
                </span>
              ))}
            </div>
          </div>

          {duzen === "carsaf" && (
            <div className="mb-3">
              <Uyari>
                Çıktı düzeni <b>çarşaf</b>: yazdırma, PDF ve Excel'de tüm{" "}
                {bakis === "sube" ? "şubeler" : "öğretmenler"} tek sayfada gelir. Aşağıdaki
                ekran görünümü tek tek gösterir.
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

          <p className="mt-3 text-xs text-slate-400">
            Hücreyi sürükleyerek taşıyın, çift tıklayarak kilitleyin. Kilitli dersler
            yeniden üretimde yerinde kalır.
          </p>
        </Kart>
      )}

      {hucreler.length > 0 && (
        <Kart
          baslik="Yayın"
          aciklama="Yayınlanan program, girişe gerek kalmadan bir bağlantı üzerinden görüntülenebilir."
          sag={<Globe className="h-4 w-4 text-slate-400" />}
        >
          {program.public_token ? (
            <div className="flex flex-wrap items-center gap-2">
              <code className="min-w-0 flex-1 truncate rounded-lg bg-slate-100 px-3 py-2 text-sm">
                {`${location.origin}/p/${program.public_token}`}
              </code>
              <Buton
                tur="ikincil"
                onClick={() =>
                  navigator.clipboard.writeText(`${location.origin}/p/${program.public_token}`)
                }
              >
                <Copy className="h-4 w-4" /> Kopyala
              </Buton>
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
