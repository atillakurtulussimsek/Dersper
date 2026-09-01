/** Tek bir ders programı: üretim, ızgara, elle düzenleme, çıktı, yayın.
 *
 *  Sürükleme bağlamı (DndContext) burada durur, ızgaranın içinde değil:
 *  bekleyenler rafı da aynı bağlamı paylaşmalı ki ders ızgaradan rafa, raftan
 *  ızgaraya sürüklenebilsin.
 */
import { useMemo, useState } from "react";
import {
  DndContext, DragOverlay, PointerSensor, useSensor, useSensors,
  type DragEndEvent, type DragStartEvent,
} from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { Copy, Globe, Play, Redo2, Undo2 } from "lucide-react";

import BekleyenDersler from "../components/BekleyenDersler";
import CarsafIzgarasi from "../components/CarsafIzgarasi";
import GecmisCalistirmalar from "../components/GecmisCalistirmalar";
import ProgramAracCubugu, { type Duzen } from "../components/ProgramAracCubugu";
import ProgramIzgarasi, { HucreIcerigi, type Bakis } from "../components/ProgramIzgarasi";
import ProgramUyarilari from "../components/ProgramUyarilari";
import SurumGecmisi from "../components/SurumGecmisi";
import TaniRaporu from "../components/TaniRaporu";
import UretimIzleme from "../components/UretimIzleme";
import { Buton, Kart, Rozet, Uyari, Yukleniyor } from "../components/ui";
import { get, jetonuAl, patch, post } from "../lib/api";
import { BOSLUK_SECENEKLERI } from "../lib/bosluk";
import { bloklariCikar } from "../lib/hucreler";
import { dersZemini } from "../lib/renkler";
import type {
  BekleyenBlok, BoslukPolitikasi, Deneme, Gun, Hedef, Hucre, Izgara,
  KapaliSaatler, Program, Suruklenen, Sube, Surum,
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
  const [suruklenen, setSuruklenen] = useState<Suruklenen | null>(null);

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
  const bekleyenler = useQuery({
    queryKey: ["bekleyenler", id],
    queryFn: () => get<BekleyenBlok[]>(`/timetables/${id}/pending`),
  });
  const surumler = useQuery({
    queryKey: ["surumler", id],
    queryFn: () => get<Surum[]>(`/timetables/${id}/versions`),
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

  /** Elle yapılan her düzenleme aynı sonucu doğurur: ızgara tazelenir,
   *  uyarılar ve bekleyenler yeniden hesaplanır. */
  function duzenlemeSonucu(veri: Izgara) {
    setHata(null);
    qc.setQueryData(["izgara", id], veri);
    qc.invalidateQueries({ queryKey: ["uyarilar", id] });
    qc.invalidateQueries({ queryKey: ["bekleyenler", id] });
    qc.invalidateQueries({ queryKey: ["surumler", id] });
    // Hedef değerlendirmeleri artık eskidi.
    qc.removeQueries({ queryKey: ["hedefler", id] });
  }

  const tasi = useMutation({
    mutationFn: ({ atama, saat }: { atama: number; saat: number }) =>
      patch<Izgara>(`/timetables/${id}/assignments/${atama}`, { period_id: saat }),
    onSuccess: duzenlemeSonucu,
    onError: (e: Error) => setHata(e.message),
  });

  const izgaradanAl = useMutation({
    mutationFn: (atama: number) =>
      post<Izgara>(`/timetables/${id}/assignments/${atama}/unplace`),
    onSuccess: duzenlemeSonucu,
    onError: (e: Error) => setHata(e.message),
  });

  const yerlestir = useMutation({
    mutationFn: (v: { entryId: number; saat: number; uzunluk: number }) =>
      post<Izgara>(`/timetables/${id}/place`, {
        curriculum_entry_id: v.entryId, period_id: v.saat, uzunluk: v.uzunluk,
      }),
    onSuccess: duzenlemeSonucu,
    onError: (e: Error) => setHata(e.message),
  });

  const geriAl = useMutation({
    mutationFn: (yon: "undo" | "redo") => post<Izgara>(`/timetables/${id}/${yon}`),
    onSuccess: duzenlemeSonucu,
    onError: (e: Error) => setHata(e.message),
  });

  const kilitle = useMutation({
    mutationFn: (atama: number) =>
      post<Izgara>(`/timetables/${id}/assignments/${atama}/lock`),
    onSuccess: duzenlemeSonucu,
  });

  const politikaDegistir = useMutation({
    mutationFn: (gap_policy: BoslukPolitikasi) =>
      patch<Program>(`/timetables/${id}`, { gap_policy }),
    onSuccess: () => {
      setHata(null);
      qc.invalidateQueries({ queryKey: ["izgara", id] });
      qc.invalidateQueries({ queryKey: ["programlar"] });
    },
    onError: (e: Error) => setHata(e.message),
  });

  const surumeDon = useMutation({
    mutationFn: (number: number) =>
      post<Izgara>(`/timetables/${id}/versions/${number}/restore`),
    onSuccess: duzenlemeSonucu,
    onError: (e: Error) => setHata(e.message),
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
    qc.invalidateQueries({ queryKey: ["surumler", id] });
    qc.invalidateQueries({ queryKey: ["bekleyenler", id] });
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


  // --- Elle düzenleme: sürükleme ---

  // Küçük eşik: hücreye tıklayıp kilitlemek sürükleme sayılmasın.
  const sensorler = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );
  const bloklar = useMemo(() => bloklariCikar(hucreler), [hucreler]);

  /** Sürüklenen öğeyi tanımlayan sorgu dizesi; hedefleri sunucuya bu sorar. */
  const hedefSorgusu =
    suruklenen === null
      ? null
      : suruklenen.tur === "hucre"
        ? `assignment_id=${suruklenen.assignmentId}`
        : `curriculum_entry_id=${suruklenen.entryId}&uzunluk=${suruklenen.uzunluk}`;

  const hedefSorgu = useQuery({
    queryKey: ["hedefler", id, hedefSorgusu],
    queryFn: () => get<Hedef[]>(`/timetables/${id}/targets?${hedefSorgusu}`),
    enabled: hedefSorgusu !== null,
    // Kurallar sunucuda tek yerde; aynı dersi tekrar sürüklerken yeniden
    // sormamak için kısa süre saklanır, her düzenlemede temizlenir.
    staleTime: 60_000,
  });
  const hedefler = useMemo(() => {
    const harita = new Map<number, Hedef>();
    for (const h of hedefSorgu.data ?? []) harita.set(h.period_id, h);
    return harita;
  }, [hedefSorgu.data]);

  function suruklemeBasladi(e: DragStartEvent) {
    const kimlik = String(e.active.id);
    if (kimlik.startsWith("h:")) {
      const atama = Number(kimlik.slice(2));
      const blok = bloklar.get(atama) ?? [];
      setSuruklenen({ tur: "hucre", assignmentId: atama, hucreler: blok });
      return;
    }
    const [, entryId, uzunluk] = kimlik.split(":");
    const blok = (bekleyenler.data ?? []).find(
      (b) => b.curriculum_entry_id === Number(entryId) && b.uzunluk === Number(uzunluk),
    );
    if (!blok) return;
    setSuruklenen({
      tur: "bekleyen",
      entryId: Number(entryId),
      uzunluk: Number(uzunluk),
      etiket: `${blok.subject_name} · ${blok.section_name}`,
      renk: blok.subject_color,
    });
  }

  function suruklemeBitti(e: DragEndEvent) {
    const kaynak = suruklenen;
    setSuruklenen(null);
    if (!kaynak || !e.over) return;
    const hedef = String(e.over.id);

    if (hedef === "raf") {
      if (kaynak.tur === "hucre") izgaradanAl.mutate(kaynak.assignmentId);
      return;
    }
    if (!hedef.startsWith("s:")) return;
    const saat = Number(hedef.slice(2));
    if (kaynak.tur === "hucre") {
      tasi.mutate({ atama: kaynak.assignmentId, saat });
    } else {
      yerlestir.mutate({ entryId: kaynak.entryId, saat, uzunluk: kaynak.uzunluk });
    }
  }

  const duzenlemeSuruyor =
    tasi.isPending || izgaradanAl.isPending || yerlestir.isPending ||
    geriAl.isPending || surumeDon.isPending;

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
    <DndContext
      sensors={sensorler}
      onDragStart={suruklemeBasladi}
      onDragEnd={suruklemeBitti}
      onDragCancel={() => setSuruklenen(null)}
    >
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
            {izgaraSorgu.data?.version != null && (
              <span className="sayisal font-mono text-murekkep-silik">
                · v{izgaraSorgu.data.version}
              </span>
            )}
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
        <div className="flex shrink-0 items-center gap-1.5">
        {hucreler.length > 0 && (
          <>
            <Buton
              tur="ikincil"
              title="Son elle düzenlemeyi geri al"
              aria-label="Geri al"
              disabled={!izgaraSorgu.data?.can_undo || duzenlemeSuruyor}
              onClick={() => geriAl.mutate("undo")}
            >
              <Undo2 className="h-4 w-4" />
              <span className="hidden sm:inline">Geri al</span>
            </Buton>
            <Buton
              tur="ikincil"
              title="Geri alınanı yeniden uygula"
              aria-label="İleri al"
              disabled={!izgaraSorgu.data?.can_redo || duzenlemeSuruyor}
              onClick={() => geriAl.mutate("redo")}
            >
              <Redo2 className="h-4 w-4" />
            </Buton>
          </>
        )}
        <select
          value={program.gap_policy}
          disabled={Boolean(surenUretim) || politikaDegistir.isPending}
          onChange={(e) => politikaDegistir.mutate(e.target.value as BoslukPolitikasi)}
          title="Öğretmen boşlukları — bir sonraki üretimde geçerli olur"
          className="shrink-0 rounded-lg border border-cizgi-guclu bg-yuzey px-2.5 py-2 text-sm text-murekkep-yumusak"
        >
          {BOSLUK_SECENEKLERI.map((se) => (
            <option key={se.id} value={se.id}>
              Boşluk: {se.etiket}
            </option>
          ))}
        </select>
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
        </div>
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
                  duzenlenebilir
                  hedefler={hedefler}
                  suruklenen={suruklenen}
                  kilitle={(atama) => kilitle.mutate(atama)}
                />
              )}
              <p className="mt-3 text-xs text-murekkep-silik">
                Hücreyi sürükleyerek taşıyın — blok bütün taşınır. Dolu bir hücreye
                bırakmak iki dersi yer değiştirir. Aşağıdaki rafa bırakmak dersi
                programdan çıkarır. Çift tıklamak kilitler; kilitli dersler yeniden
                üretimde yerinde kalır.
              </p>
            </>
          )}
        </Kart>
      )}

      {duzen === "ayri" && (hucreler.length > 0 || (bekleyenler.data ?? []).length > 0) && (
        <BekleyenDersler
          bloklar={bekleyenler.data ?? []}
          suruklenen={suruklenen}
        />
      )}

      {hucreler.length > 0 && id && <ProgramUyarilari timetableId={id} />}

      <SurumGecmisi
        surumler={surumler.data ?? []}
        yukleniyor={surumler.isLoading}
        simdiki={izgaraSorgu.data?.version ?? null}
        don={(number) => surumeDon.mutate(number)}
        bekliyor={duzenlemeSuruyor}
      />

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

      {/* Sürüklenen şey imlecin peşinde: hangi dersin taşındığı hep görünür. */}
      <DragOverlay dropAnimation={null}>
        {suruklenen?.tur === "hucre" && suruklenen.hucreler[0] && (
          <div className="h-14 w-36 rounded-md shadow-lg">
            <HucreIcerigi hucre={suruklenen.hucreler[0]} bakis={bakis} />
            {suruklenen.hucreler.length > 1 && (
              <span className="sayisal mt-1 block rounded bg-murekkep px-1.5 py-0.5 text-center font-mono text-[10px] text-uzeri">
                {suruklenen.hucreler.length} saatlik blok
              </span>
            )}
          </div>
        )}
        {suruklenen?.tur === "bekleyen" && (
          <div
            className="w-40 rounded-md px-2 py-1.5 shadow-lg"
            style={dersZemini(suruklenen.renk)}
          >
            <span className="block truncate text-[12px] font-semibold text-murekkep">
              {suruklenen.etiket}
            </span>
            <span className="sayisal font-mono text-[10px] text-murekkep-yumusak">
              {suruklenen.uzunluk} saat
            </span>
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
