/** Kısıtlamalar: programı bağlayan kuralların tek yerden yönetimi.
 *
 *  Kurallar önceden ilgili ekranlara dağılmıştı (bina kuralı Binalar'da,
 *  çakışma ölçütü Zaman Izgarası'nda). Program üretimini etkileyen her şey
 *  burada durur; yeni kısıt türleri de buraya kart olarak eklenir.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlarmClock, Building2 } from "lucide-react";
import { Link } from "react-router-dom";

import { Kart, SayfaBasligi, Uyari, Yukleniyor } from "../components/ui";
import { get, put } from "../lib/api";
import { OLCUT_SECENEKLERI } from "../lib/cakisma";
import { useListe } from "../lib/hooks";
import type { Bina, CakismaOlcutu, Donem, Sube } from "../lib/types";

export default function Kisitlamalar() {
  const qc = useQueryClient();
  const donemler = useQuery({ queryKey: ["donemler"], queryFn: () => get<Donem[]>("/terms") });
  const subeler = useListe<Sube>("subeler", "/sections");
  const binalar = useListe<Bina>("binalar", "/buildings");
  const aktifDonem = (donemler.data ?? []).find((d) => d.is_active);

  // Dönem ayarı PUT tüm alanları yazar; bir kuralı değiştirirken öbürleri
  // olduğu gibi gönderilir.
  const ayar = useMutation({
    mutationFn: (yama: Partial<Pick<Donem, "block_building_switch" | "conflict_basis">>) =>
      put<Donem>(`/terms/${aktifDonem!.id}`, {
        name: aktifDonem!.name,
        starts_on: aktifDonem!.starts_on,
        ends_on: aktifDonem!.ends_on,
        block_building_switch: aktifDonem!.block_building_switch,
        conflict_basis: aktifDonem!.conflict_basis,
        section_order: aktifDonem!.section_order,
        ...yama,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["donemler"] }),
  });

  const binasiz = (subeler.data ?? []).filter((s) => s.building_id === null).length;
  const binaVar = (binalar.data?.length ?? 0) > 0;

  if (donemler.isLoading || !aktifDonem) return <Yukleniyor />;

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Kısıtlamalar"
        aciklama="Program üretimini ve elle düzenlemeyi bağlayan kurallar. Hepsi bu dönem için geçerlidir."
      />

      {ayar.error && <Uyari tur="hata">{(ayar.error as Error).message}</Uyari>}

      <Kart
        baslik="Binalar arası geçiş"
        aciklama="Binalar birbirinden uzaksa öğretmenin gün içinde bina değiştirmesi zordur."
        sag={<Building2 className="h-4 w-4 text-murekkep-silik" />}
      >
        {!binaVar ? (
          <p className="text-sm text-murekkep-silik">
            Bu dönemde bina tanımlı değil; kuralın bir etkisi olmaz.{" "}
            <Link to="/binalar" className="font-medium text-murekkep underline">
              Binalar
            </Link>{" "}
            sayfasından ekleyebilirsiniz.
          </p>
        ) : (
          <>
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={aktifDonem.block_building_switch}
                disabled={ayar.isPending}
                onChange={(e) => ayar.mutate({ block_building_switch: e.target.checked })}
                className="mt-0.5 h-4 w-4 rounded border-cizgi-guclu"
              />
              <span className="text-sm">
                <span className="font-medium text-murekkep">
                  Bir öğretmen bir günde tek binada ders versin
                </span>
                <span className="mt-0.5 block text-murekkep-silik">
                  Açıkken bir binanın dersleri bir güne, öbürününki başka güne toplanır;
                  hangi binanın hangi güne düşeceğine program karar verir. Program başka
                  türlü kurulamıyorsa kural esnetilir ve aşım uyarı olarak listelenir.
                </span>
              </span>
            </label>
            {binasiz > 0 && (
              <div className="mt-3">
                <Uyari>
                  {binasiz} şubenin binası seçilmemiş. Binasız şubeler bu kuralın dışında
                  kalır —{" "}
                  <Link to="/subeler" className="font-medium underline">
                    Şubeler
                  </Link>{" "}
                  sayfasından binalarını seçebilirsiniz.
                </Uyari>
              </div>
            )}
          </>
        )}
      </Kart>

      <Kart
        baslik="Çakışma neye göre ölçülsün?"
        aciklama="Bir şube ya da öğretmen aynı anda iki yerde olamaz. “Aynı an”ın ne demek olduğunu buradan seçersiniz; hem program üretimi hem elle düzenleme bu seçime uyar."
        sag={<AlarmClock className="h-4 w-4 text-murekkep-silik" />}
      >
        <div className="space-y-1.5">
          {OLCUT_SECENEKLERI.map((se) => (
            <label
              key={se.id}
              className={
                aktifDonem.conflict_basis === se.id
                  ? "flex cursor-pointer gap-2.5 rounded-lg border border-cizgi-guclu bg-yuzey-alt px-3 py-2"
                  : "flex cursor-pointer gap-2.5 rounded-lg border border-cizgi px-3 py-2 hover:bg-yuzey-alt"
              }
            >
              <input
                type="radio"
                name="cakisma-olcutu"
                checked={aktifDonem.conflict_basis === se.id}
                disabled={ayar.isPending}
                onChange={() => ayar.mutate({ conflict_basis: se.id as CakismaOlcutu })}
                className="mt-0.5 h-4 w-4 border-cizgi-guclu"
              />
              <span className="text-sm">
                <span className="font-medium text-murekkep">{se.etiket}</span>
                <span className="text-murekkep-silik"> · {se.ozet}</span>
                <span className="mt-0.5 block text-xs leading-relaxed text-murekkep-silik">
                  {se.aciklama}
                </span>
              </span>
            </label>
          ))}
        </div>
        <p className="mt-3 text-xs text-murekkep-silik">
          Saatler üst üste biniyorsa{" "}
          <Link to="/zaman-izgarasi" className="font-medium underline">
            Zaman Izgarası
          </Link>{" "}
          sayfası uyarır.
        </p>
      </Kart>
    </div>
  );
}
