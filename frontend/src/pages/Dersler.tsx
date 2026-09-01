import { useState } from "react";
import { Download, Pencil, Plus, Trash2, Wand2 } from "lucide-react";

import GecmisDonemdenAktar from "../components/GecmisDonemdenAktar";
import RenkSecici from "../components/RenkSecici";
import {
  Alan, BosDurum, Buton, Girdi, Kart, Kutu, SayfaBasligi, Tablo, Uyari,
  Yukleniyor,
} from "../components/ui";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import { kisaltmaOner } from "../lib/kisaltma";
import { rastgeleRenk, VARSAYILAN_RENK } from "../lib/renkler";
import type { Ders } from "../lib/types";

const BOS = { name: "", short_code: "", color: VARSAYILAN_RENK, is_active: true };

export default function Dersler() {
  const liste = useListe<Ders>("dersler", "/subjects");
  const kaynak = useKaynak<typeof BOS, Ders>("dersler", "/subjects");
  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<Ders | null>(null);
  const [form, setForm] = useState(BOS);
  const [aktarimAcik, setAktarimAcik] = useState(false);
  // Kullanıcı kısa kodu elle değiştirdiyse ad yazdıkça üzerine yazmayız.
  const [kodElle, setKodElle] = useState(false);
  // Yeni kayıtta renk rastgele atanır; kullanıcı isterse elle seçer.
  const [renkRastgele, setRenkRastgele] = useState(true);

  /** Ders adı değişince kısa kodu da önerilenle günceller. */
  function adiDegistir(ad: string) {
    setForm((f) => ({ ...f, name: ad, short_code: kodElle ? f.short_code : kisaltmaOner(ad) }));
  }

  /** Bu dönemde kullanılan renkler — rastgele seçim bunlardan kaçınır. */
  function kullanilanRenkler(haric?: number): string[] {
    return (liste.data ?? []).filter((d) => d.id !== haric).map((d) => d.color);
  }

  function ac(ders?: Ders) {
    setDuzenlenen(ders ?? null);
    setKodElle(Boolean(ders?.short_code));
    setRenkRastgele(!ders);
    setForm(
      ders
        ? {
            name: ders.name,
            short_code: ders.short_code ?? "",
            color: ders.color,
            is_active: ders.is_active,
          }
        : { ...BOS, color: rastgeleRenk(kullanilanRenkler()) },
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
      <SayfaBasligi
        baslik="Dersler"
        aciklama="Okulda okutulan ders adları. Renkler program ızgarasında kullanılır."
        sag={
          <>
            <Buton tur="ikincil" onClick={() => setAktarimAcik(true)}>
              <Download className="h-4 w-4" /> Geçmiş dönemden aktar
            </Buton>
            <Buton onClick={() => ac()}>
              <Plus className="h-4 w-4" /> Ders ekle
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
            baslik="Henüz ders yok"
            aciklama="Matematik, Türkçe, Fen Bilimleri gibi dersleri ekleyerek başlayın."
            eylem={<Buton onClick={() => ac()}>Ders ekle</Buton>}
          />
        ) : (
          <Tablo basliklar={["Ders", "Kısa kod", "Durum", ""]}>
            {liste.data.map((d) => (
              <tr key={d.id} className="hover:bg-yuzey-alt">
                <td className="px-3 py-2.5">
                  <span className="flex items-center gap-2.5">
                    <span
                      className="h-3 w-3 shrink-0 rounded-full"
                      style={{ background: d.color }}
                    />
                    <span className="font-medium">{d.name}</span>
                  </span>
                </td>
                <td className="px-3 py-2.5 font-mono text-xs text-murekkep-yumusak">{d.short_code || "—"}</td>
                <td className="px-3 py-2.5 text-murekkep-silik">
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
                      <Trash2 className="h-4 w-4 text-hata" />
                    </Buton>
                  </div>
                </td>
              </tr>
            ))}
          </Tablo>
        )}
      </Kart>

      {aktarimAcik && (
        <GecmisDonemdenAktar<Ders>
          tur="subjects"
          baslik="Geçmiş dönemden ders aktar"
          satirYazisi={(d) => ({ ana: d.name, alt: d.short_code ?? undefined })}
          tazelenecek={["dersler"]}
          kapat={() => setAktarimAcik(false)}
        />
      )}

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
          <Alan
            etiket="Renk"
            ipucu={
              renkRastgele
                ? "Rastgele atandı. Düğmeye basarak yeniden karabilir, paletten elle de seçebilirsiniz."
                : "Elle seçildi."
            }
          >
            <RenkSecici
              deger={form.color}
              degistir={(renk) => setForm({ ...form, color: renk })}
              rastgele={renkRastgele}
              rastgeleDegistir={setRenkRastgele}
              kullanilanlar={kullanilanRenkler(duzenlenen?.id)}
            />
          </Alan>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="form-check-input h-4 w-4"
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
