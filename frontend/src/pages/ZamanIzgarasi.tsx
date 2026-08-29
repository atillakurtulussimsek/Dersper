/** Günler ve ders saatleri. Ders saati sayısı güne göre değişebilir. */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Coffee, Download, Minus, Plus, UtensilsCrossed } from "lucide-react";

import {
  Buton, Girdi, Kart, Kutu, SayfaBasligi, Secim, Uyari, Yukleniyor,
} from "../components/ui";
import { get, post, put } from "../lib/api";
import type { DersSaati, Donem, Gun } from "../lib/types";

type TaslakSaat = Omit<DersSaati, "id" | "day_id">;
type TaslakGun = { index: number; name: string; is_active: boolean; periods: TaslakSaat[] };

function yeniSaat(index: number): TaslakSaat {
  return {
    index, name: `${index + 1}. ders`, start_time: null, end_time: null,
    is_break: false, is_lunch: false,
  };
}

export default function ZamanIzgarasi() {
  const qc = useQueryClient();
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const [taslak, setTaslak] = useState<TaslakGun[]>([]);
  const [aktarimAcik, setAktarimAcik] = useState(false);
  const [kaynakId, setKaynakId] = useState<number | null>(null);

  const donemler = useQuery({ queryKey: ["donemler"], queryFn: () => get<Donem[]>("/terms") });
  const gecmis = (donemler.data ?? []).filter((d) => !d.is_active);

  const izgarayiAktar = useMutation({
    mutationFn: () => post<Gun[]>(`/timegrid/import/${kaynakId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["timegrid"] });
      setAktarimAcik(false);
    },
  });

  useEffect(() => {
    if (!izgara.data) return;
    setTaslak(
      izgara.data.map((g) => ({
        index: g.index,
        name: g.name,
        is_active: g.is_active,
        periods: g.periods
          .slice()
          .sort((a, b) => a.index - b.index)
          .map(({ index, name, start_time, end_time, is_break, is_lunch }) => ({
            index, name, start_time, end_time, is_break, is_lunch,
          })),
      })),
    );
  }, [izgara.data]);

  const kaydet = useMutation({
    mutationFn: () => put<Gun[]>("/timegrid", taslak),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timegrid"] }),
  });

  function gunuDegistir(index: number, yama: Partial<TaslakGun>) {
    setTaslak((t) => t.map((g) => (g.index === index ? { ...g, ...yama } : g)));
  }

  function saatEkle(gunIndex: number) {
    setTaslak((t) =>
      t.map((g) =>
        g.index === gunIndex ? { ...g, periods: [...g.periods, yeniSaat(g.periods.length)] } : g,
      ),
    );
  }

  function saatCikar(gunIndex: number) {
    setTaslak((t) =>
      t.map((g) => (g.index === gunIndex ? { ...g, periods: g.periods.slice(0, -1) } : g)),
    );
  }

  function saatiDegistir(gunIndex: number, saatIndex: number, yama: Partial<TaslakSaat>) {
    setTaslak((t) =>
      t.map((g) =>
        g.index === gunIndex
          ? {
              ...g,
              periods: g.periods.map((p, i) => (i === saatIndex ? { ...p, ...yama } : p)),
            }
          : g,
      ),
    );
  }

  /** Öğle arası günde tek olabilir: yenisi işaretlenince eskisi bırakılır.
   *  Öğle arasına ders konmadığı için teneffüs de olur. */
  function ogleArasiniDegistir(gunIndex: number, saatIndex: number) {
    setTaslak((t) =>
      t.map((g) => {
        if (g.index !== gunIndex) return g;
        const acilacak = !g.periods[saatIndex].is_lunch;
        return {
          ...g,
          periods: g.periods.map((p, i) =>
            i === saatIndex
              ? { ...p, is_lunch: acilacak, is_break: acilacak ? true : p.is_break }
              : { ...p, is_lunch: false },
          ),
        };
      }),
    );
  }

  const toplam = taslak
    .filter((g) => g.is_active)
    .reduce((t, g) => t + g.periods.filter((p) => !p.is_break).length, 0);

  if (izgara.isLoading) return <Yukleniyor />;

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Zaman Izgarası"
        aciklama="Hangi günlerde kaç ders saati olduğu. Teneffüse ders yerleştirilmez; öğle arası ayrıca günü sabah ve öğleden sonra diye böler."
        sag={
          <>
    <Buton
                tur="ikincil"
                onClick={() => {
                  setKaynakId(gecmis[0]?.id ?? null);
                  setAktarimAcik(true);
                }}
              >
                <Download className="h-4 w-4" /> Geçmiş dönemden aktar
              </Buton>
              <Buton onClick={() => kaydet.mutate()} yukleniyor={kaydet.isPending}>
                Kaydet
              </Buton>
          </>
        }
      />

      {kaydet.error && <Uyari tur="hata">{(kaydet.error as Error).message}</Uyari>}
      {kaydet.isSuccess && !kaydet.isPending && (
        <Uyari tur="basari">Zaman ızgarası kaydedildi.</Uyari>
      )}

      <Uyari>
        Haftada toplam <b>{toplam}</b> ders saati tanımlı. Yerleşmiş bir ders programı
        varken ızgara değiştirilemez; önce programı silmeniz gerekir.
      </Uyari>

      <Kutu
        acik={aktarimAcik}
        kapat={() => setAktarimAcik(false)}
        baslik="Geçmiş dönemden zaman ızgarası aktar"
      >
        <div className="space-y-4">
          <Uyari tur="hata">
            Bu dönemin mevcut zaman ızgarası <b>tamamen değiştirilir</b>. Yerleşmiş bir
            ders programı varsa işlem reddedilir.
          </Uyari>
          {!gecmis.length ? (
            <Uyari>Aktarılacak başka dönem yok.</Uyari>
          ) : (
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-murekkep-yumusak">
                Kaynak dönem
              </span>
              <Secim
                value={kaynakId ?? ""}
                onChange={(e) => setKaynakId(Number(e.target.value))}
              >
                {gecmis.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} · {d.counts.ders_saati ?? 0} gün
                  </option>
                ))}
              </Secim>
            </label>
          )}
          {izgarayiAktar.error && (
            <Uyari tur="hata">{(izgarayiAktar.error as Error).message}</Uyari>
          )}
          <div className="flex justify-end gap-2">
            <Buton tur="ikincil" onClick={() => setAktarimAcik(false)}>
              Vazgeç
            </Buton>
            <Buton
              tur="tehlike"
              disabled={!kaynakId}
              yukleniyor={izgarayiAktar.isPending}
              onClick={() => izgarayiAktar.mutate()}
            >
              Izgarayı değiştir
            </Buton>
          </div>
        </div>
      </Kutu>

      <div className="grid gap-4 lg:grid-cols-2">
        {taslak.map((g) => (
          <Kart
            key={g.index}
            baslik={g.name}
            aciklama={
              g.is_active
                ? `${g.periods.filter((p) => !p.is_break).length} ders · ${
                    g.periods.filter((p) => p.is_break).length
                  } teneffüs${g.periods.some((p) => p.is_lunch) ? " · öğle arası var" : ""}`
                : "Bu gün kapalı"
            }
            sag={
              <label className="flex items-center gap-2 text-sm text-murekkep-yumusak">
                <input
                  type="checkbox"
                  checked={g.is_active}
                  onChange={(e) => gunuDegistir(g.index, { is_active: e.target.checked })}
                  className="h-4 w-4 rounded border-cizgi-guclu"
                />
                Açık
              </label>
            }
          >
            {!g.is_active ? (
              <p className="text-sm text-murekkep-silik">Kapalı günlere ders yerleştirilmez.</p>
            ) : (
              <div className="space-y-2">
                {g.periods.map((p, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="w-6 text-right text-xs text-murekkep-silik">{i + 1}</span>
                    <Girdi
                      value={p.name}
                      onChange={(e) => saatiDegistir(g.index, i, { name: e.target.value })}
                      className="flex-1"
                    />
                    <Girdi
                      type="time"
                      value={p.start_time?.slice(0, 5) ?? ""}
                      onChange={(e) =>
                        saatiDegistir(g.index, i, { start_time: e.target.value || null })
                      }
                      className="w-28"
                    />
                    <Girdi
                      type="time"
                      value={p.end_time?.slice(0, 5) ?? ""}
                      onChange={(e) =>
                        saatiDegistir(g.index, i, { end_time: e.target.value || null })
                      }
                      className="w-28"
                    />
                    <button
                      type="button"
                      title={p.is_break ? "Teneffüs — ders konmaz" : "Ders saati"}
                      onClick={() =>
                        saatiDegistir(g.index, i, {
                          is_break: !p.is_break,
                          // Öğle arası zaten teneffüstür; teneffüsü kapatmak
                          // öğle arasını da kaldırır.
                          is_lunch: p.is_break ? false : p.is_lunch,
                        })
                      }
                      className={`rounded-lg border p-2 ${
                        p.is_break
                          ? "border-uyari/25 bg-uyari-zemin text-uyari"
                          : "border-cizgi-guclu bg-yuzey text-murekkep-silik hover:bg-yuzey-alt"
                      }`}
                    >
                      <Coffee className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      title={
                        p.is_lunch
                          ? "Öğle arası — günü sabah ve öğleden sonra diye böler"
                          : "Öğle arası yap"
                      }
                      onClick={() => ogleArasiniDegistir(g.index, i)}
                      className={`rounded-lg border p-2 ${
                        p.is_lunch
                          ? "border-cizgi-guclu bg-murekkep text-uzeri"
                          : "border-cizgi-guclu bg-yuzey text-murekkep-silik hover:bg-yuzey-alt"
                      }`}
                    >
                      <UtensilsCrossed className="h-4 w-4" />
                    </button>
                  </div>
                ))}

                <div className="flex gap-2 pt-1">
                  <Buton tur="ikincil" onClick={() => saatEkle(g.index)}>
                    <Plus className="h-4 w-4" /> Saat ekle
                  </Buton>
                  <Buton
                    tur="ikincil"
                    onClick={() => saatCikar(g.index)}
                    disabled={!g.periods.length}
                  >
                    <Minus className="h-4 w-4" /> Sondakini sil
                  </Buton>
                </div>
              </div>
            )}
          </Kart>
        ))}
      </div>
    </div>
  );
}
