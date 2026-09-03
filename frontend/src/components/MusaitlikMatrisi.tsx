/** Müsaitlik matrisi. Hem öğretmenler hem şubeler için kullanılır:
 *  hangi ders saatlerinin kapalı, hangilerinin tercih edildiği işaretlenir.
 *  Hücreye tıklanarak ya da basılı tutup sürüklenerek boyanır. */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";

import { Copy } from "lucide-react";

import { Buton, Kutu, Uyari, Yukleniyor } from "./ui";
import { get, post, put } from "../lib/api";
import type { Gun, Musaitlik } from "../lib/types";

type Hucreler = Record<number, Musaitlik>;

const SIRA: Musaitlik[] = ["uygun", "uygun_degil", "tercih"];

const STIL: Record<Musaitlik, string> = {
  uygun: "bg-yuzey hover:bg-yuzey-alt text-murekkep-silik",
  uygun_degil: "bg-hata/85 text-uzeri hover:bg-hata",
  tercih: "bg-basari/85 text-uzeri hover:bg-basari",
};

const ISARET: Record<Musaitlik, string> = {
  uygun: "",
  uygun_degil: "✕",
  tercih: "★",
};

export type KopyaSozleri = {
  tekil: string;        // "şube"
  cogul: string;        // "şubeler"
  cogulIlgi: string;    // "şubelerin"
  cogulYonelme: string; // "şubelere"
  tekilIlgi: string;    // "şubenin"
  tekilYonelme: string; // "şubeye"
};

export const SUBE_SOZLERI: KopyaSozleri = {
  tekil: "şube", cogul: "şubeler", cogulIlgi: "şubelerin", cogulYonelme: "şubelere",
  tekilIlgi: "şubenin", tekilYonelme: "şubeye",
};

export const OGRETMEN_SOZLERI: KopyaSozleri = {
  tekil: "öğretmen", cogul: "öğretmenler", cogulIlgi: "öğretmenlerin",
  cogulYonelme: "öğretmenlere", tekilIlgi: "öğretmenin", tekilYonelme: "öğretmene",
};

export default function MusaitlikMatrisi({
  baslik,
  yol,
  aciklama,
  gunler,
  kapat,
  kopyaHedefleri,
  kopyaAlani = "section_ids",
  kopyaSozleri = SUBE_SOZLERI,
}: {
  /** Kutunun başlığı, örn. "Ayşe Yılmaz · müsaitlik" */
  baslik: string;
  /** Müsaitlik ucu, örn. "/teachers/3" ya da "/sections/7" */
  yol: string;
  aciklama: string;
  gunler: Gun[];
  kapat: () => void;
  /** Verilirse tabloyu başka kayıtlara kopyalama seçeneği açılır. */
  kopyaHedefleri?: { id: number; name: string }[];
  /** Kopya isteğindeki alan adı; şube için varsayılan, öğretmende "teacher_ids". */
  kopyaAlani?: "section_ids" | "teacher_ids";
  /** Hedeflerin adı, gereken çekimleriyle — ek yapıştırmak Türkçede
   *  ünlü/ünsüz uyumunu bozar ("öğretmenye"). */
  kopyaSozleri?: KopyaSozleri;
}) {
  const qc = useQueryClient();
  const [kopyaModu, setKopyaModu] = useState(false);
  const [hedefler, setHedefler] = useState<number[]>([]);
  const [kopyaSonucu, setKopyaSonucu] = useState<string | null>(null);
  const [hucreler, setHucreler] = useState<Hucreler>({});
  const [suruklu, setSuruklu] = useState<Musaitlik | null>(null);

  const kayitli = useQuery({
    queryKey: ["musaitlik", yol],
    queryFn: () => get<{ period_id: number; state: Musaitlik }[]>(`${yol}/availability`),
  });

  useEffect(() => {
    if (!kayitli.data) return;
    const m: Hucreler = {};
    for (const h of kayitli.data) m[h.period_id] = h.state;
    setHucreler(m);
  }, [kayitli.data]);

  const kaydetIstegi = () =>
    put(`${yol}/availability`, {
      cells: Object.entries(hucreler).map(([period_id, state]) => ({
        period_id: Number(period_id),
        state,
      })),
    });

  const kaydet = useMutation({
    mutationFn: kaydetIstegi,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["musaitlik", yol] });
      kapat();
    },
  });

  /** Önce bu tabloyu kaydeder, sonra seçili hedeflere aynen yazar. */
  const kopyala = useMutation({
    mutationFn: async () => {
      await kaydetIstegi();
      return post<{ copied_to: string[]; cells: number }>(
        `${yol}/availability/copy`,
        { [kopyaAlani]: hedefler },
      );
    },
    onSuccess: (veri) => {
      qc.invalidateQueries({ queryKey: ["musaitlik"] });
      setKopyaSonucu(
        `${veri.copied_to.join(", ")} — ${veri.copied_to.length} ${kopyaSozleri.tekilYonelme} kopyalandı ` +
          `(${veri.cells} işaretli saat). Önceki planları silindi.`,
      );
      setHedefler([]);
      setKopyaModu(false);
    },
  });

  const aktifGunler = gunler.filter((g) => g.is_active);
  const enFazla = Math.max(
    0,
    ...aktifGunler.map((g) => Math.max(0, ...g.periods.map((p) => p.index + 1))),
  );

  function durum(periodId: number): Musaitlik {
    return hucreler[periodId] ?? "uygun";
  }

  function cevir(periodId: number) {
    const sonraki = SIRA[(SIRA.indexOf(durum(periodId)) + 1) % SIRA.length];
    setHucreler((h) => ({ ...h, [periodId]: sonraki }));
    setSuruklu(sonraki);
  }

  function boya(periodId: number) {
    if (suruklu === null) return;
    setHucreler((h) => ({ ...h, [periodId]: suruklu }));
  }

  return (
    <Kutu acik kapat={kapat} baslik={baslik}>
      <div className="space-y-4" onMouseUp={() => setSuruklu(null)} onMouseLeave={() => setSuruklu(null)}>
        <Uyari>
          {aciklama} Hücreye tıklayarak durumu değiştirin: boş = uygun,{" "}
          <b>✕</b> = uygun değil, <b>★</b> = tercih edilen saat. Basılı tutup
          sürükleyerek toplu işaretleyebilirsiniz.
        </Uyari>

        {kayitli.isLoading ? (
          <Yukleniyor />
        ) : !aktifGunler.length ? (
          <Uyari tur="hata">
            Zaman ızgarası tanımlı değil. Önce Zaman Izgarası sayfasından günleri ve
            ders saatlerini tanımlayın.
          </Uyari>
        ) : (
          <div className="overflow-x-auto">
            <table className="border-collapse select-none">
              <thead>
                <tr>
                  <th className="px-2 py-1" />
                  {aktifGunler.map((g) => (
                    <th key={g.id} className="px-2 py-1 text-xs font-medium text-murekkep-yumusak">
                      {g.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: enFazla }, (_, i) => (
                  <tr key={i}>
                    <th className="pr-2 text-right text-xs font-medium text-murekkep-silik">
                      {i + 1}.
                    </th>
                    {aktifGunler.map((g) => {
                      const p = g.periods.find((x) => x.index === i);
                      if (!p)
                        return <td key={g.id} className="h-8 w-16 bg-yuzey-alt" />;
                      if (p.is_break)
                        return (
                          <td
                            key={g.id}
                            className="h-8 w-16 border border-cizgi bg-yuzey-alt text-center text-[10px] text-murekkep-silik"
                          >
                            tnf
                          </td>
                        );
                      const d = durum(p.id);
                      return (
                        <td key={g.id} className="p-0">
                          <button
                            type="button"
                            onMouseDown={() => cevir(p.id)}
                            onMouseEnter={() => boya(p.id)}
                            className={clsx(
                              "h-8 w-16 border border-cizgi text-xs transition-colors",
                              STIL[d],
                            )}
                            title={p.name}
                          >
                            {ISARET[d]}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {kopyaSonucu && <Uyari tur="basari">{kopyaSonucu}</Uyari>}

        {kopyaModu && kopyaHedefleri && (
          <div className="space-y-3 rounded-lg border border-cizgi p-4">
            <Uyari tur="hata">
              Seçtiğiniz {kopyaSozleri.cogulIlgi} mevcut müsaitlik tablosu <b>tamamen silinir</b> ve
              yerine bu tablo yazılır. Birleştirme yapılmaz.
            </Uyari>

            {!kopyaHedefleri.length ? (
              <p className="text-sm text-murekkep-silik">Kopyalanacak başka {kopyaSozleri.tekil} yok.</p>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-murekkep-yumusak">Hedef {kopyaSozleri.cogul}</span>
                  <Buton
                    tur="sade"
                    onClick={() =>
                      setHedefler(
                        hedefler.length === kopyaHedefleri.length
                          ? []
                          : kopyaHedefleri.map((h) => h.id),
                      )
                    }
                  >
                    {hedefler.length === kopyaHedefleri.length
                      ? "Hiçbirini seçme"
                      : "Hepsini seç"}
                  </Buton>
                </div>
                <div className="max-h-40 space-y-1 overflow-y-auto">
                  {kopyaHedefleri.map((h) => (
                    <label
                      key={h.id}
                      className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm hover:bg-yuzey-alt"
                    >
                      <input
                        type="checkbox"
                        checked={hedefler.includes(h.id)}
                        onChange={() =>
                          setHedefler((s) =>
                            s.includes(h.id) ? s.filter((x) => x !== h.id) : [...s, h.id],
                          )
                        }
                        className="h-4 w-4 rounded border-cizgi-guclu"
                      />
                      {h.name}
                    </label>
                  ))}
                </div>
              </>
            )}

            {kopyala.error && <Uyari tur="hata">{(kopyala.error as Error).message}</Uyari>}

            <div className="flex justify-end gap-2">
              <Buton tur="ikincil" onClick={() => setKopyaModu(false)}>
                Vazgeç
              </Buton>
              <Buton
                tur="tehlike"
                disabled={!hedefler.length}
                yukleniyor={kopyala.isPending}
                onClick={() => kopyala.mutate()}
              >
                {hedefler.length} {kopyaSozleri.tekilIlgi} planını değiştir
              </Buton>
            </div>
          </div>
        )}

        {kaydet.error && <Uyari tur="hata">{(kaydet.error as Error).message}</Uyari>}

        <div className="flex flex-wrap justify-end gap-2 pt-2">
          {kopyaHedefleri && !kopyaModu && (
            <Buton
              tur="ikincil"
              className="mr-auto"
              onClick={() => {
                setKopyaSonucu(null);
                setKopyaModu(true);
              }}
            >
              <Copy className="h-4 w-4" /> Başka {kopyaSozleri.cogulYonelme} kopyala
            </Buton>
          )}
          <Buton tur="ikincil" onClick={kapat}>
            Vazgeç
          </Buton>
          <Buton onClick={() => kaydet.mutate()} yukleniyor={kaydet.isPending}>
            Kaydet
          </Buton>
        </div>
      </div>
    </Kutu>
  );
}
