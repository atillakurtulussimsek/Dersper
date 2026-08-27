import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarCheck, Pencil, Plus, Trash2, Wand2 } from "lucide-react";

import MusaitlikMatrisi from "../components/MusaitlikMatrisi";
import {
  Alan, BosDurum, Buton, CokSatir, Girdi, Kart, Kutu, Tablo, Uyari, Yukleniyor,
} from "../components/ui";
import { get } from "../lib/api";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import { ogretmenKoduOner } from "../lib/kisaltma";
import type { Gun, Ogretmen } from "../lib/types";

const BOS = {
  full_name: "",
  short_code: "",
  branch: "",
  max_daily_hours: "" as number | "",
  notes: "",
  is_active: true,
};

export default function Ogretmenler() {
  const liste = useListe<Ogretmen>("ogretmenler", "/teachers");
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const kaynak = useKaynak<any, Ogretmen>("ogretmenler", "/teachers");

  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<Ogretmen | null>(null);
  const [form, setForm] = useState(BOS);
  const [musaitlikIcin, setMusaitlikIcin] = useState<Ogretmen | null>(null);
  // Kullanıcı kısa kodu elle değiştirdiyse ad yazdıkça üzerine yazmayız.
  const [kodElle, setKodElle] = useState(false);

  /** Düzenlenen öğretmen dışındaki kayıtlı kodlar — çakışmayı önlemek için. */
  function baskaKodlar(): string[] {
    return (liste.data ?? [])
      .filter((o) => o.id !== duzenlenen?.id && o.short_code)
      .map((o) => o.short_code!);
  }

  function onerilenKod(ad: string): string {
    return ogretmenKoduOner(ad, baskaKodlar());
  }

  /** Ad soyad değişince kısa kodu da önerilenle günceller. */
  function adiDegistir(ad: string) {
    setForm((f) => ({
      ...f,
      full_name: ad,
      short_code: kodElle ? f.short_code : onerilenKod(ad),
    }));
  }

  function ac(o?: Ogretmen) {
    setDuzenlenen(o ?? null);
    setKodElle(Boolean(o?.short_code));
    setForm(
      o
        ? {
            full_name: o.full_name,
            short_code: o.short_code ?? "",
            branch: o.branch ?? "",
            max_daily_hours: o.max_daily_hours ?? "",
            notes: o.notes ?? "",
            is_active: o.is_active,
          }
        : BOS,
    );
    setAcik(true);
  }

  async function kaydet(e: React.FormEvent) {
    e.preventDefault();
    const veri = {
      full_name: form.full_name,
      short_code: form.short_code || null,
      branch: form.branch || null,
      max_daily_hours: form.max_daily_hours === "" ? null : Number(form.max_daily_hours),
      notes: form.notes || null,
      is_active: form.is_active,
    };
    if (duzenlenen) await kaynak.guncelle.mutateAsync({ id: duzenlenen.id, veri });
    else await kaynak.ekle.mutateAsync(veri);
    setAcik(false);
  }

  const hata = hataMetni(kaynak.ekle, kaynak.guncelle, kaynak.sil);

  return (
    <div className="space-y-5">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Öğretmenler</h1>
          <p className="text-sm text-slate-500">
            Öğretmen kadrosu ve her öğretmenin haftalık müsaitlik durumu.
          </p>
        </div>
        <Buton onClick={() => ac()}>
          <Plus className="h-4 w-4" /> Öğretmen ekle
        </Buton>
      </header>

      {hata && <Uyari tur="hata">{hata}</Uyari>}

      <Kart>
        {liste.isLoading ? (
          <Yukleniyor />
        ) : !liste.data?.length ? (
          <BosDurum
            baslik="Henüz öğretmen yok"
            aciklama="Program üretebilmek için önce öğretmen kadrosunu girin."
            eylem={<Buton onClick={() => ac()}>Öğretmen ekle</Buton>}
          />
        ) : (
          <Tablo basliklar={["Ad soyad", "Branş", "Kısa kod", "Günlük en fazla", "Durum", ""]}>
            {liste.data.map((o) => (
              <tr key={o.id} className="hover:bg-slate-50">
                <td className="px-3 py-2.5 font-medium">{o.full_name}</td>
                <td className="px-3 py-2.5 text-slate-500">{o.branch || "—"}</td>
                <td className="px-3 py-2.5 text-slate-500">{o.short_code || "—"}</td>
                <td className="px-3 py-2.5 text-slate-500">
                  {o.max_daily_hours ? `${o.max_daily_hours} saat` : "—"}
                </td>
                <td className="px-3 py-2.5 text-slate-500">
                  {o.is_active ? "Aktif" : "Pasif"}
                </td>
                <td className="px-3 py-2.5 text-right">
                  <div className="flex justify-end gap-1">
                    <Buton
                      tur="sade"
                      onClick={() => setMusaitlikIcin(o)}
                      aria-label="Müsaitlik"
                      title="Müsaitlik matrisi"
                    >
                      <CalendarCheck className="h-4 w-4" />
                    </Buton>
                    <Buton tur="sade" onClick={() => ac(o)} aria-label="Düzenle">
                      <Pencil className="h-4 w-4" />
                    </Buton>
                    <Buton
                      tur="sade"
                      onClick={() => {
                        if (confirm(`"${o.full_name}" silinsin mi?`)) kaynak.sil.mutate(o.id);
                      }}
                      aria-label="Sil"
                    >
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Buton>
                  </div>
                </td>
              </tr>
            ))}
          </Tablo>
        )}
      </Kart>

      <Kutu
        acik={acik}
        kapat={() => setAcik(false)}
        baslik={duzenlenen ? "Öğretmeni düzenle" : "Öğretmen ekle"}
      >
        <form onSubmit={kaydet} className="space-y-4">
          <Alan etiket="Ad soyad">
            <Girdi
              required
              autoFocus
              value={form.full_name}
              onChange={(e) => adiDegistir(e.target.value)}
              placeholder="Ayşe Yılmaz"
            />
          </Alan>
          <div className="grid gap-4 sm:grid-cols-2">
            <Alan etiket="Branş">
              <Girdi
                value={form.branch}
                onChange={(e) => setForm({ ...form, branch: e.target.value })}
                placeholder="Matematik"
              />
            </Alan>
            <Alan
              etiket="Kısa kod"
              ipucu={kodElle ? undefined : "Ad soyaddan otomatik türetiliyor."}
            >
              <div className="flex gap-2">
                <Girdi
                  maxLength={20}
                  value={form.short_code}
                  onChange={(e) => {
                    setKodElle(true);
                    setForm({ ...form, short_code: e.target.value });
                  }}
                  placeholder="AY"
                />
                <Buton
                  tur="ikincil"
                  type="button"
                  title="Ad soyaddan yeniden türet"
                  disabled={!form.full_name.trim()}
                  onClick={() => {
                    setKodElle(false);
                    setForm((f) => ({ ...f, short_code: onerilenKod(f.full_name) }));
                  }}
                >
                  <Wand2 className="h-4 w-4" />
                </Buton>
              </div>
            </Alan>
          </div>
          <Alan
            etiket="Günde en fazla ders saati"
            ipucu="Boş bırakılırsa sınır uygulanmaz."
          >
            <Girdi
              type="number"
              min={1}
              max={20}
              value={form.max_daily_hours}
              onChange={(e) =>
                setForm({
                  ...form,
                  max_daily_hours: e.target.value === "" ? "" : Number(e.target.value),
                })
              }
            />
          </Alan>
          <Alan etiket="Not">
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
              className="h-4 w-4 rounded border-slate-300"
            />
            Aktif (pasif öğretmenler programa dahil edilmez)
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <Buton tur="ikincil" type="button" onClick={() => setAcik(false)}>
              Vazgeç
            </Buton>
            <Buton type="submit" yukleniyor={kaynak.ekle.isPending || kaynak.guncelle.isPending}>
              Kaydet
            </Buton>
          </div>
        </form>
      </Kutu>

      {musaitlikIcin && (
        <MusaitlikMatrisi
          ogretmen={musaitlikIcin}
          gunler={izgara.data ?? []}
          kapat={() => setMusaitlikIcin(null)}
        />
      )}
    </div>
  );
}
