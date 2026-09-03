/** Sürüm geçmişi: programda yapılan her değişiklik.
 *
 *  Üretimler ve elle düzenlemeler aynı zincirde durur. Hiçbir sürüm silinmez —
 *  geri alıp başka yöne gitseniz de terk edilen dal listede kalır ve geri
 *  yüklenebilir.
 *
 *  Liste uzayabildiği için varsayılan olarak son birkaç sürüm gösterilir.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeftRight, ArrowRight, GitCompare, History, Lock, LockOpen, Minus, Play,
  Pencil, Plus, RotateCcw, Sparkles, X,
} from "lucide-react";
import clsx from "clsx";

import { Buton, Kart, Yukleniyor } from "./ui";
import { get } from "../lib/api";
import type { FarkDegisikligi, Surum, SurumFarki, SurumTuru } from "../lib/types";

const KISALTILMIS = 6;

const TUR: Record<SurumTuru, { etiket: string; Simge: typeof Play }> = {
  ilk: { etiket: "Başlangıç", Simge: Sparkles },
  uretim: { etiket: "Üretim", Simge: Play },
  elle: { etiket: "Elle", Simge: Pencil },
};

function zaman(iso: string): string {
  return new Date(iso).toLocaleString("tr-TR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

function konum(k: { gun: string; saat: string }): string {
  return `${k.gun} ${k.saat}`;
}

const FARK_TURU: Record<
  FarkDegisikligi["tur"],
  { etiket: string; Simge: typeof Plus; renk: string }
> = {
  tasindi: { etiket: "Taşındı", Simge: ArrowRight, renk: "text-murekkep" },
  cikti: { etiket: "Çıktı", Simge: Minus, renk: "text-hata" },
  eklendi: { etiket: "Eklendi", Simge: Plus, renk: "text-basari" },
  kilitlendi: { etiket: "Kilitlendi", Simge: Lock, renk: "text-murekkep-yumusak" },
  kilit_acildi: { etiket: "Kilit açıldı", Simge: LockOpen, renk: "text-murekkep-yumusak" },
};

/** Tek bir değişiklik satırı: ders, sonra nereden nereye. */
function FarkSatiri({ d }: { d: FarkDegisikligi }) {
  const { Simge, renk } = FARK_TURU[d.tur];
  return (
    <li className="flex items-start gap-2.5 py-1.5 text-sm">
      <Simge className={clsx("mt-0.5 h-3.5 w-3.5 shrink-0", renk)} />
      <span className="min-w-0 flex-1">
        <span className="font-medium text-murekkep">{d.sube} · {d.ders}</span>
        <span className="text-murekkep-silik"> · {d.ogretmen}</span>
        <span className="sayisal mt-0.5 block text-xs text-murekkep-yumusak">
          {d.tur === "tasindi" && d.kaynak && d.hedef && (
            <>{konum(d.kaynak)} <span className="text-murekkep-silik">→</span> {konum(d.hedef)}</>
          )}
          {d.tur === "cikti" && d.kaynak && <>{konum(d.kaynak)} → programdan çıktı</>}
          {d.tur === "eklendi" && d.hedef && <>programa girdi → {konum(d.hedef)}</>}
          {(d.tur === "kilitlendi" || d.tur === "kilit_acildi") && d.kaynak && (
            <>{konum(d.kaynak)} · {FARK_TURU[d.tur].etiket.toLocaleLowerCase("tr")}</>
          )}
        </span>
      </span>
    </li>
  );
}

/** İki sürüm arasındaki fark: özet sayımlar ve türe göre gruplanmış liste.
 *
 *  Sürüm geçmişi tek başına "ne zaman ne oldu"yu söyler; bu panel "neyin yeri
 *  değişti"yi söyler. Yeniden üretimden sonra hangi derslerin oynadığını
 *  görmenin başka yolu yok — çarşafı gözle karşılaştırmak dışında.
 */
function FarkPaneli({
  timetableId,
  a,
  b,
  degistir,
  kapat,
}: {
  timetableId: number;
  a: number;
  b: number;
  degistir: (a: number, b: number) => void;
  kapat: () => void;
}) {
  const fark = useQuery({
    queryKey: ["surum-farki", timetableId, a, b],
    queryFn: () => get<SurumFarki>(`/timetables/${timetableId}/versions/${a}/diff/${b}`),
  });

  const gruplar: { tur: FarkDegisikligi["tur"][]; baslik: string }[] = [
    { tur: ["tasindi"], baslik: "Taşınan" },
    { tur: ["cikti"], baslik: "Çıkan" },
    { tur: ["eklendi"], baslik: "Eklenen" },
    { tur: ["kilitlendi", "kilit_acildi"], baslik: "Kilit" },
  ];

  return (
    <div className="mb-3 rounded-lg border border-cizgi-guclu bg-yuzey-alt p-3">
      <div className="flex flex-wrap items-center gap-2">
        <GitCompare className="h-4 w-4 shrink-0 text-murekkep-silik" />
        <span className="sayisal font-mono text-sm font-medium text-murekkep">
          v{a} → v{b}
        </span>
        <Buton tur="sade" onClick={() => degistir(b, a)} title="Yönü çevir">
          <ArrowLeftRight className="h-3.5 w-3.5" />
        </Buton>
        {fark.data && (
          <span className="sayisal ml-auto flex flex-wrap gap-2 text-xs text-murekkep-silik">
            <span>{fark.data.ozet.tasindi} taşındı</span>
            <span>{fark.data.ozet.cikti} çıktı</span>
            <span>{fark.data.ozet.eklendi} eklendi</span>
            {fark.data.ozet.kilit > 0 && <span>{fark.data.ozet.kilit} kilit</span>}
            <span>· {fark.data.ozet.degisen_ders} ders</span>
          </span>
        )}
        <Buton tur="sade" onClick={kapat} aria-label="Kapat">
          <X className="h-4 w-4" />
        </Buton>
      </div>

      {fark.isLoading ? (
        <Yukleniyor metin="Fark hesaplanıyor…" />
      ) : fark.error ? (
        <p className="mt-2 text-sm text-hata">{(fark.error as Error).message}</p>
      ) : fark.data && fark.data.degisiklikler.length === 0 ? (
        <p className="mt-2 text-sm text-murekkep-silik">
          İki sürüm birebir aynı; hiçbir ders yer değiştirmemiş.
        </p>
      ) : fark.data ? (
        <div className="mt-2 grid gap-3 lg:grid-cols-2">
          {gruplar.map(({ tur, baslik }) => {
            const satirlar = fark.data!.degisiklikler.filter((d) => tur.includes(d.tur));
            if (!satirlar.length) return null;
            return (
              <div key={baslik}>
                <p className="text-2xs font-semibold uppercase tracking-[0.08em] text-murekkep-silik">
                  {baslik} · {satirlar.length}
                </p>
                <ul className="mt-1 divide-y divide-cizgi">
                  {satirlar.map((d, i) => (
                    <FarkSatiri key={`${d.entry_id}-${d.tur}-${i}`} d={d} />
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export default function SurumGecmisi({
  timetableId,
  surumler,
  yukleniyor,
  simdiki,
  don,
  bekliyor,
}: {
  timetableId: number;
  surumler: Surum[];
  yukleniyor: boolean;
  /** Programın şu an durduğu sürüm numarası. */
  simdiki: number | null;
  don: (number: number) => void;
  bekliyor: boolean;
}) {
  const [hepsi, setHepsi] = useState(false);
  // Karşılaştırılan çift; null = panel kapalı.
  const [fark, setFark] = useState<{ a: number; b: number } | null>(null);
  const gosterilen = hepsi ? surumler : surumler.slice(0, KISALTILMIS);

  return (
    <Kart
      baslik="Sürüm geçmişi"
      aciklama="Her değişiklik bir sürüm bırakır. İstediğiniz sürüme dönebilirsiniz; sonraki sürümler silinmez."
      sag={<History className="h-4 w-4 text-murekkep-silik" />}
      katlanir
      ozet={surumler.length ? `${surumler.length} sürüm` : undefined}
    >
      {yukleniyor ? (
        <Yukleniyor />
      ) : !surumler.length ? (
        <p className="text-sm text-murekkep-silik">Henüz sürüm yok.</p>
      ) : (
        <div className="space-y-1.5">
          {fark && (
            <FarkPaneli
              timetableId={timetableId}
              a={fark.a}
              b={fark.b}
              degistir={(a, b) => setFark({ a, b })}
              kapat={() => setFark(null)}
            />
          )}
          {gosterilen.map((s) => {
            const { etiket, Simge } = TUR[s.kind];
            const bu = s.number === simdiki;
            return (
              <div
                key={s.number}
                className={clsx(
                  "flex items-center gap-3 rounded-lg border px-3 py-2",
                  bu
                    ? "border-cizgi-guclu bg-yuzey-alt"
                    : "border-cizgi hover:bg-yuzey-alt",
                )}
              >
                <span className="sayisal shrink-0 font-mono text-xs text-murekkep-silik">
                  v{s.number}
                </span>
                <Simge className="h-3.5 w-3.5 shrink-0 text-murekkep-silik" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-murekkep">{s.label}</p>
                  <p className="sayisal text-xs text-murekkep-silik">
                    {etiket} · {s.placed} ders saati · {zaman(s.created_at)}
                  </p>
                </div>
                {bu ? (
                  <span className="shrink-0 rounded-md bg-murekkep px-2 py-0.5 text-xs font-medium text-uzeri">
                    şu an
                  </span>
                ) : (
                  <>
                    {simdiki != null && (
                      <Buton
                        tur="sade"
                        className="shrink-0"
                        onClick={() => setFark({ a: s.number, b: simdiki })}
                        title={`v${s.number} ile şu anki (v${simdiki}) arasındaki fark`}
                      >
                        <GitCompare className="h-4 w-4" />
                        <span className="hidden sm:inline">Fark</span>
                      </Buton>
                    )}
                    <Buton
                      tur="ikincil"
                      className="shrink-0"
                      disabled={bekliyor}
                      onClick={() => don(s.number)}
                      title={`v${s.number} sürümüne dön`}
                    >
                      <RotateCcw className="h-4 w-4" />
                      <span className="hidden sm:inline">Bu sürüme dön</span>
                    </Buton>
                  </>
                )}
              </div>
            );
          })}

          {surumler.length > KISALTILMIS && (
            <Buton tur="sade" onClick={() => setHepsi((h) => !h)}>
              {hepsi
                ? "Yalnızca son sürümleri göster"
                : `Tümünü göster (${surumler.length} sürüm)`}
            </Buton>
          )}
        </div>
      )}
    </Kart>
  );
}
