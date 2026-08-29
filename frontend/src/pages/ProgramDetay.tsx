/** Tek bir ders programı: üretim, ızgara, elle düzenleme, çıktı, yayın. */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Copy, Globe, Play } from "lucide-react";

import CarsafIzgarasi from "../components/CarsafIzgarasi";
import GecmisCalistirmalar from "../components/GecmisCalistirmalar";
import ProgramAracCubugu, { type Duzen } from "../components/ProgramAracCubugu";
import ProgramIzgarasi, { type Bakis } from "../components/ProgramIzgarasi";
import ProgramUyarilari from "../components/ProgramUyarilari";
import TaniRaporu from "../components/TaniRaporu";
import UretimIzleme from "../components/UretimIzleme";
import { Buton, Kart, Rozet, Uyari, Yukleniyor } from "../components/ui";
import { get, jetonuAl, patch, post } from "../lib/api";
import type {
  Deneme, Gun, Hucre, Izgara, KapaliSaatler, Program, Sube,
} from "../lib/types";

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
  const subeler = useQuery({ queryKey: ["subeler"], queryFn: () => get<Sube[]>("/sections") });
  // Çarşafta boş hücreyle kapalı saati ayırt etmek için; tek istekte gelir.
  const kapali = useQuery({
    queryKey: ["kapali-saatler"],
    queryFn: () => get<KapaliSaatler>("/availability/closed"),
  });
  const denemeler = useQuery({
    queryKey: ["denemeler", id],
    queryFn: () => get<Deneme[]>(`/timetables/${id}/runs`),
  });
  // Çalışan üretim varken sık sık sorulur; iş bitince yoklama kendiliğinden durur.
  const calisan = useQuery({
    queryKey: ["calisan-uretim", id],
    queryFn: () => get<Deneme | null>(`/timetables/${id}/runs/active`),
    refetchInterval: (sorgu) => (sorgu.state.data ? 1500 : false),
  });

  const uret = useMutation({
    mutationFn: () => post<Deneme>(`/timetables/${id}/solve`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["calisan-uretim", id] });
      qc.invalidateQueries({ queryKey: ["denemeler", id] });
    },
    onError: (e: Error) => setHata(e.message),
  });

  const tasi = useMutation({
    mutationFn: ({ atama, saat }: { atama: number; saat: number }) =>
      patch<Izgara>(`/timetables/${id}/assignments/${atama}`, { period_id: saat }),
    onSuccess: (veri) => {
      setHata(null);
      qc.setQueryData(["izgara", id], veri);
      qc.invalidateQueries({ queryKey: ["uyarilar", id] });
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

  const surenUretim = calisan.data ?? null;
  // Üretim biter bitmez ızgarayı ve geçmişi bir kez tazele.
  const [oncekiCalisan, setOncekiCalisan] = useState<number | null>(null);
  if (surenUretim && surenUretim.id !== oncekiCalisan) setOncekiCalisan(surenUretim.id);
  if (!surenUretim && oncekiCalisan !== null) {
    setOncekiCalisan(null);
    qc.invalidateQueries({ queryKey: ["izgara", id] });
    qc.invalidateQueries({ queryKey: ["denemeler", id] });
    qc.invalidateQueries({ queryKey: ["uyarilar", id] });
  }

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
  /** Çarşafta tek kayıt değil, tablonun tamamı özetlenir. */
  const carsafOzeti = useMemo(() => {
    let bosluk = 0;
    for (const a of anahtarlar) {
      const kendi = hucreler.filter((h) =>
        bakis === "sube" ? h.section_name === a : h.teacher_name === a,
      );
      bosluk += ozetCikar(kendi, gunler.data ?? []).bosluk;
    }
    return { satir: anahtarlar.length, dolu: hucreler.length, bosluk };
  }, [anahtarlar, hucreler, bakis, gunler.data]);

  const sonDeneme = denemeler.data?.[0];
  const gosterRapor =
    sonDeneme && sonDeneme.status !== "basarili" && sonDeneme.report !== null;

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
        <div className="ray min-w-0">
          <h1 className="truncate font-baslik text-2xl font-semibold tracking-tight text-murekkep">
            {program.name}
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-murekkep-silik">
            <Rozet tur={DURUM[program.status].tur}>{DURUM[program.status].etiket}</Rozet>
            <span
              title={
                program.section_ids
                  ? program.section_ids
                      .map((id) => subeler.data?.find((s) => s.id === id)?.name)
                      .filter(Boolean)
                      .join(", ")
                  : undefined
              }
            >
              {program.section_ids
                ? `${program.section_ids.length} şube dahil`
                : "Tüm şubeler"}
            </span>
            <span className="sayisal">· {hucreler.length} ders saati yerleşmiş</span>
            {surenUretim && (
              <span className="sayisal text-murekkep-silik">
                · {surenUretim.attempts}. deneme sürüyor
              </span>
            )}
            {sonDeneme?.seconds != null && (
              <span className="sayisal text-murekkep-silik">
                · {sonDeneme.seconds.toFixed(1)} sn
              </span>
            )}
          </p>
        </div>
        <Buton
          onClick={() => uret.mutate()}
          yukleniyor={uret.isPending}
          disabled={Boolean(surenUretim)}
        >
          <Play className="h-4 w-4" />
          {surenUretim
            ? "Üretim sürüyor…"
            : hucreler.length
              ? "Yeniden üret"
              : "Programı üret"}
        </Buton>
      </header>

      {hata && <Uyari tur="hata">{hata}</Uyari>}

      {surenUretim && <UretimIzleme deneme={surenUretim} />}

      {/* Bulgular üretim sürerken de gösterilir: kullanıcı beklerken düzeltebilir. */}
      {surenUretim?.report ? (
        <TaniRaporu deneme={surenUretim} />
      ) : (
        gosterRapor && <TaniRaporu deneme={sonDeneme!} />
      )}

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
            anahtarlar={duzen === "ayri" ? anahtarlar : []}
            seciliAnahtar={seciliAnahtar}
            anahtarDegistir={setAnahtar}
            yazdir={yazdir}
            indir={indir}
          />

          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-murekkep">
              {duzen === "carsaf"
                ? `Tüm ${bakis === "sube" ? "şubeler" : "öğretmenler"}`
                : seciliAnahtar}
            </h2>
            <div className="flex flex-wrap gap-1.5 text-xs">
              {(duzen === "carsaf"
                ? [
                    ["satir", `${carsafOzeti.satir} ${bakis === "sube" ? "şube" : "öğretmen"}`],
                    ["dolu", `${carsafOzeti.dolu} saat dolu`],
                    ["bosluk", `${carsafOzeti.bosluk} boşluk`],
                  ]
                : [
                    ["dolu", `${ozet.dolu} saat dolu`],
                    ["bos", `${ozet.bos} saat boş`],
                    ["bosluk", `${ozet.bosluk} boşluk`],
                    ["yogun", `en yoğun: ${ozet.enYogun.gun} (${ozet.enYogun.saat})`],
                  ]
              ).map(([k, metin]) => (
                <span
                  key={k}
                  className="rounded-md bg-yuzey-alt px-2 py-1 font-medium text-murekkep-yumusak"
                >
                  {metin}
                </span>
              ))}
            </div>
          </div>

          {duzen === "carsaf" ? (
            <>
              <CarsafIzgarasi
                gunler={gunler.data ?? []}
                hucreler={hucreler}
                bakis={bakis}
                kapali={
                  bakis === "sube" ? kapali.data?.sections : kapali.data?.teachers
                }
                ac={(a) => {
                  setAnahtar(a);
                  setDuzen("ayri");
                }}
              />
              <p className="mt-3 text-xs text-murekkep-silik">
                Ardışık saatler tek hücrede birleşir; <span className="font-mono">×</span>{" "}
                o kaydın kapalı saatidir. Çarşaf inceleme içindir — düzenlemek için satır
                adına tıklayıp ayrı sayfa görünümüne geçin.
              </p>
            </>
          ) : (
            <>
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
              <p className="mt-3 text-xs text-murekkep-silik">
                Hücreyi sürükleyerek taşıyın, çift tıklayarak kilitleyin. Kilitli dersler
                yeniden üretimde yerinde kalır.
              </p>
            </>
          )}
        </Kart>
      )}

      {hucreler.length > 0 && id && <ProgramUyarilari timetableId={id} />}

      <GecmisCalistirmalar denemeler={denemeler.data ?? []} />

      {hucreler.length > 0 && (
        <Kart
          baslik="Yayın"
          aciklama="Yayınlanan program, girişe gerek kalmadan bir bağlantı üzerinden görüntülenebilir."
          sag={<Globe className="h-4 w-4 text-murekkep-silik" />}
        >
          {program.public_token ? (
            <div className="flex flex-wrap items-center gap-2">
              <code className="min-w-0 flex-1 truncate rounded-lg bg-yuzey-alt px-3 py-2 text-sm">
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
