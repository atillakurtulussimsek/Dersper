import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarCheck, Download, Pencil, Plus, Trash2, Wand2 } from "lucide-react";

import GecmisDonemdenAktar from "../components/GecmisDonemdenAktar";
import RenkSecici from "../components/RenkSecici";
import MusaitlikMatrisi from "../components/MusaitlikMatrisi";
import {
  Alan, BosDurum, Buton, CokSatir, Girdi, Kart, Kutu, SayfaBasligi, Secim, Tablo,
  Uyari, Yukleniyor,
} from "../components/ui";
import { get } from "../lib/api";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import { ogretmenKoduOner } from "../lib/kisaltma";
import { rastgeleRenk, VARSAYILAN_RENK } from "../lib/renkler";
import type { Gun, Ogretmen } from "../lib/types";

const BOS = {
  full_name: "",
  short_code: "",
  branch: "",
  max_daily_hours: "" as number | "",
  max_days: "" as number | "",
  notes: "",
  color: VARSAYILAN_RENK,
  is_active: true,
};

/** 4.5 -> "4,5". Kullanıcı gün sayısını virgüllü okur. */
function gunMetni(gun: number): string {
  return String(gun).replace(".", ",");
}

/** Sınır olarak seçilebilecek gün sayıları: yarım adımlarla, hafta boyunca. */
function gunSecenekleri(gunSayisi: number): number[] {
  const secenekler: number[] = [];
  for (let g = 0.5; g <= gunSayisi; g += 0.5) secenekler.push(g);
  return secenekler;
}

export default function Ogretmenler() {
  const liste = useListe<Ogretmen>("ogretmenler", "/teachers");
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const kaynak = useKaynak<any, Ogretmen>("ogretmenler", "/teachers");

  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<Ogretmen | null>(null);
  const [form, setForm] = useState(BOS);
  const [musaitlikIcin, setMusaitlikIcin] = useState<Ogretmen | null>(null);
  const [aktarimAcik, setAktarimAcik] = useState(false);
  // Kullanıcı kısa kodu elle değiştirdiyse ad yazdıkça üzerine yazmayız.
  const [kodElle, setKodElle] = useState(false);
  // Yeni kayıtta renk rastgele atanır; kullanıcı isterse elle seçer.
  const [renkRastgele, setRenkRastgele] = useState(true);

  const acikGunler = (izgara.data ?? []).filter((g) => g.is_active);
  const acikGunSayisi = acikGunler.length || 5;
  const ogleArasiVar = acikGunler.some((g) => g.periods.some((p) => p.is_lunch));

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

  /** Bu dönemde kullanılan renkler — rastgele seçim bunlardan kaçınır. */
  function kullanilanRenkler(haric?: number): string[] {
    return (liste.data ?? []).filter((o) => o.id !== haric).map((o) => o.color);
  }

  function ac(o?: Ogretmen) {
    setDuzenlenen(o ?? null);
    setKodElle(Boolean(o?.short_code));
    setRenkRastgele(!o);
    setForm(
      o
        ? {
            full_name: o.full_name,
            short_code: o.short_code ?? "",
            branch: o.branch ?? "",
            max_daily_hours: o.max_daily_hours ?? "",
            max_days: o.max_days ?? "",
            notes: o.notes ?? "",
            color: o.color,
            is_active: o.is_active,
          }
        : { ...BOS, color: rastgeleRenk(kullanilanRenkler()) },
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
      max_days: form.max_days === "" ? null : Number(form.max_days),
      notes: form.notes || null,
      color: form.color,
      is_active: form.is_active,
    };
    if (duzenlenen) await kaynak.guncelle.mutateAsync({ id: duzenlenen.id, veri });
    else await kaynak.ekle.mutateAsync(veri);
    setAcik(false);
  }

  const hata = hataMetni(kaynak.ekle, kaynak.guncelle, kaynak.sil);

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Öğretmenler"
        aciklama="Öğretmen kadrosu ve her öğretmenin haftalık müsaitlik durumu."
        sag={
          <>
            <Buton tur="ikincil" onClick={() => setAktarimAcik(true)}>
              <Download className="h-4 w-4" /> Geçmiş dönemden aktar
            </Buton>
            <Buton onClick={() => ac()}>
              <Plus className="h-4 w-4" /> Öğretmen ekle
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
            baslik="Henüz öğretmen yok"
            aciklama="Program üretebilmek için önce öğretmen kadrosunu girin. Geçmiş bir dönem varsa kadroyu oradan aktarabilirsiniz."
            eylem={
              <div className="flex gap-2">
                <Buton tur="ikincil" onClick={() => setAktarimAcik(true)}>
                  Geçmiş dönemden aktar
                </Buton>
                <Buton onClick={() => ac()}>Öğretmen ekle</Buton>
              </div>
            }
          />
        ) : (
          <Tablo basliklar={["Ad soyad", "Branş", "Kısa kod", "Günlük en fazla", "Haftalık gün", "Durum", ""]}>
            {liste.data.map((o) => (
              <tr key={o.id} className="hover:bg-yuzey-alt">
                <td className="px-3 py-2.5">
                  <span className="flex items-center gap-2.5">
                    <span
                      className="h-3 w-3 shrink-0 rounded-full"
                      style={{ background: o.color }}
                    />
                    <span className="font-medium">{o.full_name}</span>
                  </span>
                </td>
                <td className="px-3 py-2.5 text-murekkep-silik">{o.branch || "—"}</td>
                <td className="px-3 py-2.5 font-mono text-xs text-murekkep-yumusak">{o.short_code || "—"}</td>
                <td className="sayisal px-3 py-2.5 text-murekkep-silik">
                  {o.max_daily_hours ? `${o.max_daily_hours} saat` : "—"}
                </td>
                <td className="sayisal px-3 py-2.5 text-murekkep-silik">
                  {o.max_days ? `${gunMetni(o.max_days)} gün` : "—"}
                </td>
                <td className="px-3 py-2.5 text-murekkep-silik">
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
                      <Trash2 className="h-4 w-4 text-hata" />
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
          <Alan
            etiket="Haftada en fazla gün"
            ipucu={
              ogleArasiVar
                ? "Boş bırakılırsa sınır yok. Hangi günlerin kullanılacağına program karar verir; yarım gün ızgaradaki öğle arasına göre belirlenir."
                : "Boş bırakılırsa sınır yok. Izgarada öğle arası tanımlı olmadığı için yarım günler gün ortasından bölünür — gerçek öğle arasını Zaman Izgarası'nda işaretleyebilirsiniz."
            }
          >
            <Secim
              value={form.max_days}
              onChange={(e) =>
                setForm({
                  ...form,
                  max_days: e.target.value === "" ? "" : Number(e.target.value),
                })
              }
            >
              <option value="">Sınır yok</option>
              {gunSecenekleri(acikGunSayisi).map((g) => (
                <option key={g} value={g}>
                  {gunMetni(g)} gün
                </option>
              ))}
            </Secim>
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
              className="form-check-input h-4 w-4"
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

      {aktarimAcik && (
        <GecmisDonemdenAktar<Ogretmen>
          tur="teachers"
          baslik="Geçmiş dönemden öğretmen aktar"
          satirYazisi={(o) => ({ ana: o.full_name, alt: o.branch ?? undefined })}
          tazelenecek={["ogretmenler"]}
          kapat={() => setAktarimAcik(false)}
        />
      )}

      {musaitlikIcin && (
        <MusaitlikMatrisi
          baslik={`${musaitlikIcin.full_name} · müsaitlik`}
          yol={`/teachers/${musaitlikIcin.id}`}
          aciklama="Öğretmenin derse girebileceği saatleri işaretleyin."
          gunler={izgara.data ?? []}
          kapat={() => setMusaitlikIcin(null)}
        />
      )}
    </div>
  );
}
