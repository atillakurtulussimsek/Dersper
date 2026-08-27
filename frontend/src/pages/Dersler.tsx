import { useState } from "react";
import { Pencil, Plus, Trash2, Wand2 } from "lucide-react";

import {
  Alan, BosDurum, Buton, Girdi, Kart, Kutu, Tablo, Uyari, Yukleniyor,
} from "../components/ui";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import { kisaltmaOner } from "../lib/kisaltma";
import type { Ders } from "../lib/types";

const RENKLER = [
  "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
  "#3b82f6", "#8b5cf6", "#ec4899", "#64748b", "#0ea5e9",
];

const BOS = { name: "", short_code: "", color: RENKLER[8], is_active: true };

export default function Dersler() {
  const liste = useListe<Ders>("dersler", "/subjects");
  const kaynak = useKaynak<typeof BOS, Ders>("dersler", "/subjects");
  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<Ders | null>(null);
  const [form, setForm] = useState(BOS);
  // Kullanıcı kısa kodu elle değiştirdiyse ad yazdıkça üzerine yazmayız.
  const [kodElle, setKodElle] = useState(false);

  /** Ders adı değişince kısa kodu da önerilenle günceller. */
  function adiDegistir(ad: string) {
    setForm((f) => ({ ...f, name: ad, short_code: kodElle ? f.short_code : kisaltmaOner(ad) }));
  }

  function ac(ders?: Ders) {
    setDuzenlenen(ders ?? null);
    setKodElle(Boolean(ders?.short_code));
    setForm(
      ders
        ? {
            name: ders.name,
            short_code: ders.short_code ?? "",
            color: ders.color,
            is_active: ders.is_active,
          }
        : BOS,
    );
    setAcik(true);
  }

  async function kaydet(e: React.FormEvent) {
    e.preventDefault();
    const veri = { ...form, short_code: form.short_code || null } as any;
    if (duzenlenen) await kaynak.guncelle.mutateAsync({ id: duzenlenen.id, veri });
    else await kaynak.ekle.mutateAsync(veri);
    setAcik(false);
  }

  const hata = hataMetni(kaynak.ekle, kaynak.guncelle, kaynak.sil);

  return (
    <div className="space-y-5">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Dersler</h1>
          <p className="text-sm text-slate-500">
            Okulda okutulan ders adları. Renkler program ızgarasında kullanılır.
          </p>
        </div>
        <Buton onClick={() => ac()}>
          <Plus className="h-4 w-4" /> Ders ekle
        </Buton>
      </header>

      {hata && <Uyari tur="hata">{hata}</Uyari>}

      <Kart>
        {liste.isLoading ? (
          <Yukleniyor />
        ) : !liste.data?.length ? (
          <BosDurum
            baslik="Henüz ders yok"
            aciklama="Matematik, Türkçe, Fen Bilimleri gibi dersleri ekleyerek başlayın."
            eylem={<Buton onClick={() => ac()}>Ders ekle</Buton>}
          />
        ) : (
          <Tablo basliklar={["Ders", "Kısa kod", "Durum", ""]}>
            {liste.data.map((d) => (
              <tr key={d.id} className="hover:bg-slate-50">
                <td className="px-3 py-2.5">
                  <span className="flex items-center gap-2.5">
                    <span
                      className="h-3 w-3 shrink-0 rounded-full"
                      style={{ background: d.color }}
                    />
                    <span className="font-medium">{d.name}</span>
                  </span>
                </td>
                <td className="px-3 py-2.5 text-slate-500">{d.short_code || "—"}</td>
                <td className="px-3 py-2.5 text-slate-500">
                  {d.is_active ? "Aktif" : "Pasif"}
                </td>
                <td className="px-3 py-2.5 text-right">
                  <div className="flex justify-end gap-1">
                    <Buton tur="sade" onClick={() => ac(d)} aria-label="Düzenle">
                      <Pencil className="h-4 w-4" />
                    </Buton>
                    <Buton
                      tur="sade"
                      onClick={() => {
                        if (confirm(`"${d.name}" dersi silinsin mi?`))
                          kaynak.sil.mutate(d.id);
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

      <Kutu acik={acik} kapat={() => setAcik(false)} baslik={duzenlenen ? "Dersi düzenle" : "Ders ekle"}>
        <form onSubmit={kaydet} className="space-y-4">
          <Alan etiket="Ders adı">
            <Girdi
              required
              autoFocus
              value={form.name}
              onChange={(e) => adiDegistir(e.target.value)}
              placeholder="Matematik"
            />
          </Alan>
          <Alan
            etiket="Kısa kod"
            ipucu={
              kodElle
                ? "Izgarada dar alanlarda kullanılır. Sihirbaz düğmesi önerilen kodu geri getirir."
                : "Ders adından otomatik türetiliyor. Yazarak değiştirebilirsiniz."
            }
          >
            <div className="flex gap-2">
              <Girdi
                maxLength={20}
                value={form.short_code}
                onChange={(e) => {
                  setKodElle(true);
                  setForm({ ...form, short_code: e.target.value });
                }}
                placeholder="MAT"
              />
              <Buton
                tur="ikincil"
                type="button"
                title="Ders adından yeniden türet"
                disabled={!form.name.trim()}
                onClick={() => {
                  setKodElle(false);
                  setForm((f) => ({ ...f, short_code: kisaltmaOner(f.name) }));
                }}
              >
                <Wand2 className="h-4 w-4" />
              </Buton>
            </div>
          </Alan>
          <Alan etiket="Renk">
            <div className="flex flex-wrap gap-2">
              {RENKLER.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setForm({ ...form, color: r })}
                  style={{ background: r }}
                  className={`h-8 w-8 rounded-full ring-offset-2 transition ${
                    form.color === r ? "ring-2 ring-slate-900" : ""
                  }`}
                  aria-label={`Renk ${r}`}
                />
              ))}
            </div>
          </Alan>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="h-4 w-4 rounded border-slate-300"
            />
            Aktif (pasif dersler programa dahil edilmez)
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
    </div>
  );
}
