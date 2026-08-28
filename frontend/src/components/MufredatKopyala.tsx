/** Seçili müfredat satırlarını başka şubelere kopyalar.
 *  Yalnızca şube değişir; öğretmen, saat, dağılım ve günlük sınır aynı kalır. */
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Copy } from "lucide-react";

import { Buton, Kutu, Uyari } from "./ui";
import { post } from "../lib/api";
import type { MufredatSatiri, Sube } from "../lib/types";

interface Sonuc {
  created: MufredatSatiri[];
  skipped: string[];
}

export default function MufredatKopyala({
  satirlar,
  hedefAdaylari,
  kapat,
}: {
  /** Kopyalanacak satırlar. Tek ders ya da şubenin tüm müfredatı olabilir. */
  satirlar: MufredatSatiri[];
  /** Kaynak şube dışındaki şubeler. */
  hedefAdaylari: Sube[];
  kapat: () => void;
}) {
  const qc = useQueryClient();
  const [secili, setSecili] = useState<number[]>([]);
  const [sonuc, setSonuc] = useState<Sonuc | null>(null);

  const kopyala = useMutation({
    mutationFn: () =>
      post<Sonuc>("/curriculum/copy", {
        entry_ids: satirlar.map((s) => s.id),
        section_ids: secili,
      }),
    onSuccess: (veri) => {
      setSonuc(veri);
      qc.invalidateQueries({ queryKey: ["mufredat"] });
      qc.invalidateQueries({ queryKey: ["mufredat-hepsi"] });
    },
  });

  function degistir(id: number) {
    setSecili((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  const hepsiSecili = secili.length === hedefAdaylari.length && hedefAdaylari.length > 0;

  return (
    <Kutu
      acik
      kapat={kapat}
      baslik={
        satirlar.length === 1
          ? `"${satirlar[0].subject.name}" dersini kopyala`
          : `${satirlar.length} satırlık müfredatı kopyala`
      }
    >
      <div className="space-y-4">
        {sonuc ? (
          <>
            {sonuc.created.length > 0 && (
              <Uyari tur="basari">
                {sonuc.created.length} satır kopyalandı. Kopyalar bağımsızdır; hedef
                şubelerde ayrı ayrı düzenleyebilirsiniz.
              </Uyari>
            )}
            {sonuc.skipped.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-sm font-medium text-slate-700">
                  {sonuc.skipped.length} satır atlandı:
                </p>
                <ul className="space-y-1 text-sm text-slate-600">
                  {sonuc.skipped.map((s, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-slate-400">•</span>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {!sonuc.created.length && !sonuc.skipped.length && (
              <Uyari>Kopyalanacak bir şey bulunamadı.</Uyari>
            )}
            <div className="flex justify-end">
              <Buton onClick={kapat}>Kapat</Buton>
            </div>
          </>
        ) : (
          <>
            <Uyari>
              Kopyalanacak: <b>{satirlar.map((s) => s.subject.name).join(", ")}</b>.
              Hedef şubede aynı ders zaten varsa o satır atlanır.
            </Uyari>

            {!hedefAdaylari.length ? (
              <Uyari tur="hata">
                Kopyalanacak başka şube yok. Önce Şubeler sayfasından şube ekleyin.
              </Uyari>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-700">Hedef şubeler</span>
                  <Buton
                    tur="sade"
                    onClick={() =>
                      setSecili(hepsiSecili ? [] : hedefAdaylari.map((s) => s.id))
                    }
                  >
                    {hepsiSecili ? "Hiçbirini seçme" : "Hepsini seç"}
                  </Buton>
                </div>

                <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
                  {hedefAdaylari.map((s) => (
                    <label
                      key={s.id}
                      className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm hover:bg-slate-50"
                    >
                      <input
                        type="checkbox"
                        checked={secili.includes(s.id)}
                        onChange={() => degistir(s.id)}
                        className="h-4 w-4 rounded border-slate-300"
                      />
                      <span className="font-medium">{s.name}</span>
                      {!s.is_active && <span className="text-xs text-slate-400">pasif</span>}
                    </label>
                  ))}
                </div>
              </>
            )}

            {kopyala.error && <Uyari tur="hata">{(kopyala.error as Error).message}</Uyari>}

            <div className="flex justify-end gap-2 pt-1">
              <Buton tur="ikincil" onClick={kapat}>
                Vazgeç
              </Buton>
              <Buton
                onClick={() => kopyala.mutate()}
                disabled={!secili.length}
                yukleniyor={kopyala.isPending}
              >
                <Copy className="h-4 w-4" />
                {secili.length ? `${secili.length} şubeye kopyala` : "Kopyala"}
              </Buton>
            </div>
          </>
        )}
      </div>
    </Kutu>
  );
}
