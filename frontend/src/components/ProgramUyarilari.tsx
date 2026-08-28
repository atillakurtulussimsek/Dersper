/** Yerleşimdeki uyarılar.
 *
 *  Program başka türlü tamamlanamadığında çözücü günlük ders tekrar sınırını
 *  esnetebilir; bu durumda program başarılı sayılır ama esnetilen yerler burada
 *  listelenir. Kullanıcı isterse elle düzeltir, isterse "görmezden gel" der;
 *  gizlenen uyarı o program için bir daha gösterilmez.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, EyeOff, RotateCcw } from "lucide-react";

import { Buton, Kart, Uyari } from "./ui";
import { del, get, post } from "../lib/api";
import type { ProgramUyarisi } from "../lib/types";

function UyariSatiri({
  uyari,
  eylem,
  bekliyor,
}: {
  uyari: ProgramUyarisi;
  eylem: () => void;
  bekliyor: boolean;
}) {
  const gizli = uyari.ignored;
  return (
    <div
      className={
        gizli
          ? "flex items-start gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3"
          : "flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3"
      }
    >
      <AlertTriangle
        className={`mt-0.5 h-4 w-4 shrink-0 ${gizli ? "text-slate-400" : "text-amber-600"}`}
      />
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-medium ${gizli ? "text-slate-600" : "text-amber-900"}`}>
          {uyari.baslik}
        </p>
        <p className={`mt-0.5 text-sm ${gizli ? "text-slate-500" : "text-amber-800"}`}>
          {uyari.detay}
        </p>
      </div>
      <Buton
        tur="sade"
        onClick={eylem}
        yukleniyor={bekliyor}
        className="shrink-0 whitespace-nowrap"
        title={gizli ? "Uyarıyı yeniden göster" : "Bu uyarıyı bu program için gizle"}
      >
        {gizli ? (
          <>
            <RotateCcw className="h-4 w-4" /> Geri getir
          </>
        ) : (
          <>
            <EyeOff className="h-4 w-4" /> Görmezden gel
          </>
        )}
      </Buton>
    </div>
  );
}

export default function ProgramUyarilari({ timetableId }: { timetableId: string }) {
  const qc = useQueryClient();
  const [gizliGoster, setGizliGoster] = useState(false);

  const uyarilar = useQuery({
    queryKey: ["uyarilar", timetableId],
    queryFn: () => get<ProgramUyarisi[]>(`/timetables/${timetableId}/warnings`),
  });

  const degistir = useMutation({
    mutationFn: async ({ key, gizle }: { key: string; gizle: boolean }) => {
      if (gizle) {
        await post<ProgramUyarisi[]>(`/timetables/${timetableId}/warnings/ignore`, { key });
      } else {
        await del(`/timetables/${timetableId}/warnings/ignore/${encodeURIComponent(key)}`);
      }
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["uyarilar", timetableId] }),
  });

  const hepsi = uyarilar.data ?? [];
  const acik = hepsi.filter((u) => !u.ignored);
  const gizli = hepsi.filter((u) => u.ignored);

  if (!hepsi.length) return null;

  return (
    <Kart
      baslik="Uyarılar"
      aciklama="Program tamamlandı, ama aşağıdaki noktalarda kural esnetildi. Düzeltmek isteğe bağlıdır."
      sag={
        gizli.length > 0 ? (
          <Buton tur="ikincil" onClick={() => setGizliGoster((g) => !g)}>
            {gizliGoster ? "Gizlenenleri sakla" : `${gizli.length} gizli uyarı`}
          </Buton>
        ) : null
      }
    >
      <div className="space-y-2">
        {acik.length === 0 && !gizliGoster && (
          <Uyari tur="basari">
            Açık uyarı yok. {gizli.length} uyarı gizlenmiş durumda.
          </Uyari>
        )}

        {acik.map((u) => (
          <UyariSatiri
            key={u.key}
            uyari={u}
            bekliyor={degistir.isPending && degistir.variables?.key === u.key}
            eylem={() => degistir.mutate({ key: u.key, gizle: true })}
          />
        ))}

        {gizliGoster &&
          gizli.map((u) => (
            <UyariSatiri
              key={u.key}
              uyari={u}
              bekliyor={degistir.isPending && degistir.variables?.key === u.key}
              eylem={() => degistir.mutate({ key: u.key, gizle: false })}
            />
          ))}

        {degistir.error && <Uyari tur="hata">{(degistir.error as Error).message}</Uyari>}

        {acik.length > 0 && (
          <p className="pt-1 text-xs text-slate-500">
            Düzeltmek için ilgili hücreyi yukarıdaki ızgarada başka bir saate
            sürükleyebilir ya da Ders Atamaları'ndan günlük sınırı değiştirebilirsiniz.
          </p>
        )}
      </div>
    </Kart>
  );
}
