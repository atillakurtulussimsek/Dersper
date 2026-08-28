/** Geçmiş bir dönemdeki kayıtları listeler, seçilenleri aktif döneme aktarır.
 *  Öğretmen, ders, şube ve müfredat ekranlarında aynı bileşen kullanılır. */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { Buton, Kutu, Secim, Uyari, Yukleniyor } from "./ui";
import { get, post } from "../lib/api";
import type { AktarimSonucu, Donem } from "../lib/types";

export type AktarimTuru = "teachers" | "subjects" | "sections" | "curriculum";

export default function GecmisDonemdenAktar<T extends { id: number }>({
  tur,
  baslik,
  satirYazisi,
  tazelenecek,
  kapat,
}: {
  tur: AktarimTuru;
  baslik: string;
  /** Listede tek satırın nasıl görüneceği. */
  satirYazisi: (kayit: T) => { ana: string; alt?: string };
  /** Aktarım sonrası tazelenecek sorgu anahtarları. */
  tazelenecek: string[];
  kapat: () => void;
}) {
  const qc = useQueryClient();
  const [kaynakId, setKaynakId] = useState<number | null>(null);
  const [secili, setSecili] = useState<number[]>([]);
  const [sonuc, setSonuc] = useState<AktarimSonucu | null>(null);

  const donemler = useQuery({ queryKey: ["donemler"], queryFn: () => get<Donem[]>("/terms") });
  const gecmis = (donemler.data ?? []).filter((d) => !d.is_active);

  useEffect(() => {
    if (kaynakId === null && gecmis.length) setKaynakId(gecmis[0].id);
  }, [gecmis, kaynakId]);

  const kayitlar = useQuery({
    queryKey: ["aktarilabilir", tur, kaynakId],
    queryFn: () => get<T[]>(`/${tur}/import/${kaynakId}`),
    enabled: kaynakId !== null,
  });

  const aktar = useMutation({
    mutationFn: () =>
      post<AktarimSonucu>(`/${tur}/import`, { term_id: kaynakId, ids: secili }),
    onSuccess: (veri) => {
      setSonuc(veri);
      setSecili([]);
      for (const anahtar of tazelenecek) qc.invalidateQueries({ queryKey: [anahtar] });
    },
  });

  const liste = kayitlar.data ?? [];
  const hepsiSecili = secili.length === liste.length && liste.length > 0;

  return (
    <Kutu acik kapat={kapat} baslik={baslik}>
      <div className="space-y-4">
        {sonuc ? (
          <>
            {sonuc.imported > 0 && (
              <Uyari tur="basari">
                {sonuc.imported} kayıt bu döneme aktarıldı. Kopyalar bağımsızdır;
                burada düzenlemeniz geçmiş dönemi etkilemez.
              </Uyari>
            )}
            {sonuc.skipped.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-sm font-medium text-slate-700">
                  {sonuc.skipped.length} kayıt atlandı:
                </p>
                <ul className="max-h-48 space-y-1 overflow-y-auto text-sm text-slate-600">
                  {sonuc.skipped.map((s, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-slate-400">•</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!sonuc.imported && !sonuc.skipped.length && (
              <Uyari>Aktarılacak kayıt seçilmedi.</Uyari>
            )}
            <div className="flex justify-end gap-2">
              <Buton tur="ikincil" onClick={() => setSonuc(null)}>
                Yeniden aktar
              </Buton>
              <Buton onClick={kapat}>Kapat</Buton>
            </div>
          </>
        ) : !gecmis.length ? (
          <>
            <Uyari tur="hata">
              Aktarılacak başka dönem yok. Dönemler sayfasından geçmiş dönemleri
              görebilirsiniz.
            </Uyari>
            <div className="flex justify-end">
              <Buton tur="ikincil" onClick={kapat}>
                Kapat
              </Buton>
            </div>
          </>
        ) : (
          <>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">
                Kaynak dönem
              </span>
              <Secim
                value={kaynakId ?? ""}
                onChange={(e) => {
                  setKaynakId(Number(e.target.value));
                  setSecili([]);
                }}
              >
                {gecmis.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </Secim>
            </label>

            {kayitlar.isLoading ? (
              <Yukleniyor />
            ) : !liste.length ? (
              <Uyari>Bu dönemde aktarılacak kayıt yok.</Uyari>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">
                    {liste.length} kayıt · {secili.length} seçili
                  </span>
                  <Buton
                    tur="sade"
                    onClick={() => setSecili(hepsiSecili ? [] : liste.map((k) => k.id))}
                  >
                    {hepsiSecili ? "Hiçbirini seçme" : "Hepsini seç"}
                  </Buton>
                </div>

                <div className="max-h-72 space-y-0.5 overflow-y-auto rounded-lg border border-slate-200 p-2">
                  {liste.map((k) => {
                    const { ana, alt } = satirYazisi(k);
                    return (
                      <label
                        key={k.id}
                        className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm hover:bg-slate-50"
                      >
                        <input
                          type="checkbox"
                          checked={secili.includes(k.id)}
                          onChange={() =>
                            setSecili((s) =>
                              s.includes(k.id)
                                ? s.filter((x) => x !== k.id)
                                : [...s, k.id],
                            )
                          }
                          className="h-4 w-4 shrink-0 rounded border-slate-300"
                        />
                        <span className="min-w-0 flex-1 truncate font-medium text-slate-800">
                          {ana}
                        </span>
                        {alt && (
                          <span className="shrink-0 text-xs text-slate-500">{alt}</span>
                        )}
                      </label>
                    );
                  })}
                </div>
              </>
            )}

            {aktar.error && <Uyari tur="hata">{(aktar.error as Error).message}</Uyari>}

            <div className="flex justify-end gap-2">
              <Buton tur="ikincil" onClick={kapat}>
                Vazgeç
              </Buton>
              <Buton
                onClick={() => aktar.mutate()}
                disabled={!secili.length}
                yukleniyor={aktar.isPending}
              >
                <Download className="h-4 w-4" />
                {secili.length ? `${secili.length} kaydı aktar` : "Aktar"}
              </Buton>
            </div>
          </>
        )}
      </div>
    </Kutu>
  );
}
