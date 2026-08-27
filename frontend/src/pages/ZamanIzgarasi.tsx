/** Günler ve ders saatleri. Ders saati sayısı güne göre değişebilir. */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Coffee, Minus, Plus } from "lucide-react";

import { Buton, Girdi, Kart, Uyari, Yukleniyor } from "../components/ui";
import { get, put } from "../lib/api";
import type { DersSaati, Gun } from "../lib/types";

type TaslakSaat = Omit<DersSaati, "id" | "day_id">;
type TaslakGun = { index: number; name: string; is_active: boolean; periods: TaslakSaat[] };

function yeniSaat(index: number): TaslakSaat {
  return { index, name: `${index + 1}. ders`, start_time: null, end_time: null, is_break: false };
}

export default function ZamanIzgarasi() {
  const qc = useQueryClient();
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const [taslak, setTaslak] = useState<TaslakGun[]>([]);

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
          .map(({ index, name, start_time, end_time, is_break }) => ({
            index, name, start_time, end_time, is_break,
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

  const toplam = taslak
    .filter((g) => g.is_active)
    .reduce((t, g) => t + g.periods.filter((p) => !p.is_break).length, 0);

  if (izgara.isLoading) return <Yukleniyor />;

  return (
    <div className="space-y-5">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Zaman Izgarası</h1>
          <p className="text-sm text-slate-500">
            Hangi günlerde kaç ders saati olduğu. Teneffüs olarak işaretlenen saatlere
            ders yerleştirilmez.
          </p>
        </div>
        <Buton onClick={() => kaydet.mutate()} yukleniyor={kaydet.isPending}>
          Kaydet
        </Buton>
      </header>

      {kaydet.error && <Uyari tur="hata">{(kaydet.error as Error).message}</Uyari>}
      {kaydet.isSuccess && !kaydet.isPending && (
        <Uyari tur="basari">Zaman ızgarası kaydedildi.</Uyari>
      )}

      <Uyari>
        Haftada toplam <b>{toplam}</b> ders saati tanımlı. Yerleşmiş bir ders programı
        varken ızgara değiştirilemez; önce programı silmeniz gerekir.
      </Uyari>

      <div className="grid gap-4 lg:grid-cols-2">
        {taslak.map((g) => (
          <Kart
            key={g.index}
            baslik={g.name}
            aciklama={
              g.is_active
                ? `${g.periods.filter((p) => !p.is_break).length} ders · ${
                    g.periods.filter((p) => p.is_break).length
                  } teneffüs`
                : "Bu gün kapalı"
            }
            sag={
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={g.is_active}
                  onChange={(e) => gunuDegistir(g.index, { is_active: e.target.checked })}
                  className="h-4 w-4 rounded border-slate-300"
                />
                Açık
              </label>
            }
          >
            {!g.is_active ? (
              <p className="text-sm text-slate-400">Kapalı günlere ders yerleştirilmez.</p>
            ) : (
              <div className="space-y-2">
                {g.periods.map((p, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="w-6 text-right text-xs text-slate-400">{i + 1}</span>
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
                      title={p.is_break ? "Teneffüs" : "Ders saati"}
                      onClick={() => saatiDegistir(g.index, i, { is_break: !p.is_break })}
                      className={`rounded-lg border p-2 ${
                        p.is_break
                          ? "border-amber-300 bg-amber-100 text-amber-700"
                          : "border-slate-300 bg-white text-slate-400 hover:bg-slate-50"
                      }`}
                    >
                      <Coffee className="h-4 w-4" />
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
