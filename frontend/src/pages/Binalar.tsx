/** Binalar. Bazı kurumlar birden fazla binada ders yapar.
 *
 *  Şube kendi dersliğiyle bir binada durur; öğretmen ise binalar arasında
 *  gezer. Binalar birbirinden uzaksa gün içinde geçiş zordur — bu sayfadaki
 *  kural anahtarı açıkken bir öğretmenin bir günkü dersleri tek binada
 *  toplanır, hangi binanın hangi güne düşeceğine program karar verir.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Download, Pencil, Plus, Trash2 } from "lucide-react";

import {
  Alan, BosDurum, Buton, CokSatir, Girdi, Kart, Kutu, SayfaBasligi, Tablo,
  Uyari, Yukleniyor,
} from "../components/ui";
import GecmisDonemdenAktar from "../components/GecmisDonemdenAktar";
import { get, put } from "../lib/api";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import type { Bina, Donem, Sube } from "../lib/types";

const BOS = { name: "", short_code: "", notes: "", is_active: true };

export default function Binalar() {
  const qc = useQueryClient();
  const liste = useListe<Bina>("binalar", "/buildings");
  const subeler = useListe<Sube>("subeler", "/sections");
  const donemler = useQuery({ queryKey: ["donemler"], queryFn: () => get<Donem[]>("/terms") });
  const kaynak = useKaynak<any, Bina>("binalar", "/buildings");

  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<Bina | null>(null);
  const [form, setForm] = useState(BOS);
  const [aktarimAcik, setAktarimAcik] = useState(false);

  const aktifDonem = (donemler.data ?? []).find((d) => d.is_active);

  const kural = useMutation({
    mutationFn: (acikMi: boolean) =>
      put<Donem>(`/terms/${aktifDonem!.id}`, {
        name: aktifDonem!.name,
        starts_on: aktifDonem!.starts_on,
        ends_on: aktifDonem!.ends_on,
        block_building_switch: acikMi,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["donemler"] }),
  });

  function ac(b?: Bina) {
    setDuzenlenen(b ?? null);
    setForm(
      b
        ? {
            name: b.name,
            short_code: b.short_code ?? "",
            notes: b.notes ?? "",
            is_active: b.is_active,
          }
        : BOS,
    );
    setAcik(true);
  }

  async function kaydet(e: React.FormEvent) {
    e.preventDefault();
    const veri = {
      name: form.name,
      short_code: form.short_code || null,
      notes: form.notes || null,
      is_active: form.is_active,
    };
    if (duzenlenen) await kaynak.guncelle.mutateAsync({ id: duzenlenen.id, veri });
    else await kaynak.ekle.mutateAsync(veri);
    setAcik(false);
  }

  /** Bir binadaki şube sayısı — silmeden önce ne etkileneceğini göstermek için. */
  function subeSayisi(binaId: number): number {
    return (subeler.data ?? []).filter((s) => s.building_id === binaId).length;
  }

  const hata = hataMetni(kaynak.ekle, kaynak.guncelle, kaynak.sil);
  const binasiz = (subeler.data ?? []).filter((s) => s.building_id === null).length;

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Binalar"
        aciklama="Kurumun binaları. Şubeler dersliğiyle birlikte bir binada durur; bina tanımlamak yalnızca birden fazla binada ders yapan kurumlar için gereklidir."
        sag={
          <>
            <Buton tur="ikincil" onClick={() => setAktarimAcik(true)}>
              <Download className="h-4 w-4" /> Geçmiş dönemden aktar
            </Buton>
            <Buton onClick={() => ac()}>
              <Plus className="h-4 w-4" /> Bina ekle
            </Buton>
          </>
        }
      />

      {hata && <Uyari tur="hata">{hata}</Uyari>}

      <Kart>
        {liste.isLoading ? (
          <Yukleniyor />
        ) : !liste.data?.length ? (
          <BosDurum
            baslik="Bina tanımlı değil"
            aciklama="Tek binada ders yapıyorsanız bir şey yapmanıza gerek yok. Birden fazla binanız varsa ekleyin ve şubeleri binalarına bağlayın."
            eylem={<Buton onClick={() => ac()}>Bina ekle</Buton>}
          />
        ) : (
          <Tablo basliklar={["Bina", "Kısa kod", "Şube", "Not", "Durum", ""]}>
            {liste.data.map((b) => (
              <tr key={b.id} className="hover:bg-yuzey-alt">
                <td className="px-3 py-2.5 font-medium">{b.name}</td>
                <td className="px-3 py-2.5 font-mono text-xs text-murekkep-yumusak">
                  {b.short_code || "—"}
                </td>
                <td className="sayisal px-3 py-2.5 text-murekkep-silik">
                  {subeSayisi(b.id)}
                </td>
                <td className="max-w-64 truncate px-3 py-2.5 text-murekkep-silik">
                  {b.notes || "—"}
                </td>
                <td className="px-3 py-2.5 text-murekkep-silik">
                  {b.is_active ? "Aktif" : "Pasif"}
                </td>
                <td className="px-3 py-2.5 text-right">
                  <div className="flex justify-end gap-1">
                    <Buton tur="sade" onClick={() => ac(b)} aria-label="Düzenle">
                      <Pencil className="h-4 w-4" />
                    </Buton>
                    <Buton
                      tur="sade"
                      aria-label="Sil"
                      onClick={() => {
                        const n = subeSayisi(b.id);
                        const not = n
                          ? ` ${n} şube binasız kalacak (şubeler silinmez).`
                          : "";
                        if (confirm(`"${b.name}" silinsin mi?${not}`)) {
                          kaynak.sil.mutate(b.id);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-hata" />
                    </Buton>
                  </div>
                </td>
              </tr>
            ))}
          </Tablo>
        )}
      </Kart>

      {(liste.data?.length ?? 0) > 0 && aktifDonem && (
        <Kart
          baslik="Binalar arası geçiş"
          aciklama="Binalar birbirinden uzaksa öğretmenin gün içinde bina değiştirmesi zordur."
          sag={<Building2 className="h-4 w-4 text-murekkep-silik" />}
        >
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={aktifDonem.block_building_switch}
              disabled={kural.isPending}
              onChange={(e) => kural.mutate(e.target.checked)}
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
            <Uyari>
              {binasiz} şubenin binası seçilmemiş. Binasız şubeler bu kuralın dışında
              kalır — Şubeler sayfasından binalarını seçebilirsiniz.
            </Uyari>
          )}
          {kural.error && <Uyari tur="hata">{(kural.error as Error).message}</Uyari>}
        </Kart>
      )}

      {aktarimAcik && (
        <GecmisDonemdenAktar<Bina>
          tur="buildings"
          baslik="Geçmiş dönemden bina aktar"
          satirYazisi={(b) => ({ ana: b.name, alt: b.short_code ?? undefined })}
          tazelenecek={["binalar"]}
          kapat={() => setAktarimAcik(false)}
        />
      )}

      <Kutu
        acik={acik}
        kapat={() => setAcik(false)}
        baslik={duzenlenen ? "Binayı düzenle" : "Bina ekle"}
      >
        <form onSubmit={kaydet} className="space-y-4">
          <Alan etiket="Bina adı">
            <Girdi
              required
              autoFocus
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Ana Bina"
            />
          </Alan>
          <Alan etiket="Kısa kod" ipucu="Çıktılarda yer dar olduğunda kullanılır.">
            <Girdi
              maxLength={20}
              value={form.short_code}
              onChange={(e) => setForm({ ...form, short_code: e.target.value })}
              placeholder="A"
            />
          </Alan>
          <Alan etiket="Not" ipucu="Adres ya da binalar arası mesafe gibi notlar.">
            <CokSatir
              rows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </Alan>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="h-4 w-4 rounded border-cizgi-guclu"
            />
            Aktif
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <Buton tur="ikincil" type="button" onClick={() => setAcik(false)}>
              Vazgeç
            </Buton>
            <Buton
              type="submit"
              yukleniyor={kaynak.ekle.isPending || kaynak.guncelle.isPending}
            >
              Kaydet
            </Buton>
          </div>
        </form>
      </Kutu>
    </div>
  );
}
