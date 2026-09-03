/** Dönem yönetimi: oluşturma, adlandırma, geçiş, silme ve geri alma. */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Pencil, Plus, RotateCcw, Trash2 } from "lucide-react";

import {
  Alan, Buton, Girdi, Kart, Kutu, Rozet, SayfaBasligi, Tablo, Uyari,
  Yukleniyor,
} from "../components/ui";
import { del, get, post, put } from "../lib/api";
import type { Donem } from "../lib/types";

const BOS = { name: "", starts_on: "", ends_on: "" };

/** Kopyanın özeti: sunucunun döndüğü sayımlar, okunur adlarıyla. */
const KOPYA_ETIKETLERI: [string, string][] = [
  ["gun", "gün"],
  ["ders_saati", "ders saati"],
  ["bina", "bina"],
  ["ogretmen", "öğretmen"],
  ["ders", "ders"],
  ["sube", "şube"],
  ["mufredat", "ders ataması"],
];

interface KopyaSonucu {
  term: Donem;
  copied: Record<string, number>;
}

const SAYAC_ETIKETLERI: [string, string][] = [
  ["ders_saati", "gün"],
  ["ogretmen", "öğretmen"],
  ["ders", "ders"],
  ["sube", "şube"],
  ["mufredat", "müfredat"],
  ["program", "program"],
];

export default function Donemler() {
  const qc = useQueryClient();
  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<Donem | null>(null);
  const [form, setForm] = useState(BOS);
  const [silinmisGoster, setSilinmisGoster] = useState(false);
  // Dönem kopyası: kaynak dönem, yeni ad/tarih ve kopya aktif olsun mu.
  const [kopyaKaynak, setKopyaKaynak] = useState<Donem | null>(null);
  const [kopyaForm, setKopyaForm] = useState({ ...BOS, activate: true });
  const [kopyaSonuc, setKopyaSonuc] = useState<KopyaSonucu | null>(null);

  const donemler = useQuery({ queryKey: ["donemler"], queryFn: () => get<Donem[]>("/terms") });
  const silinmisler = useQuery({
    queryKey: ["donemler-silinmis"],
    queryFn: () => get<Donem[]>("/terms/deleted"),
    enabled: silinmisGoster,
  });

  const tazele = () => {
    qc.invalidateQueries({ queryKey: ["donemler"] });
    qc.invalidateQueries({ queryKey: ["donemler-silinmis"] });
  };

  const kaydet = useMutation({
    mutationFn: () => {
      const govde = {
        name: form.name,
        starts_on: form.starts_on || null,
        ends_on: form.ends_on || null,
      };
      return duzenlenen
        ? put<Donem>(`/terms/${duzenlenen.id}`, govde)
        : post<Donem>("/terms", govde);
    },
    onSuccess: () => {
      // Yeni dönem aktif olur; önbellekteki veri artık geçersiz.
      qc.resetQueries();
      setAcik(false);
    },
  });

  const kopyala = useMutation({
    mutationFn: () =>
      post<KopyaSonucu>(`/terms/${kopyaKaynak!.id}/copy`, {
        name: kopyaForm.name,
        starts_on: kopyaForm.starts_on || null,
        ends_on: kopyaForm.ends_on || null,
        activate: kopyaForm.activate,
      }),
    onSuccess: (sonuc) => {
      setKopyaSonuc(sonuc);
      setKopyaKaynak(null);
      // Kopya aktif olduysa ekrandaki her şey başka döneme ait.
      if (sonuc.term.is_active) qc.resetQueries();
      else tazele();
    },
  });

  function kopyaAc(d: Donem) {
    setKopyaKaynak(d);
    setKopyaSonuc(null);
    setKopyaForm({ name: `${d.name} (kopya)`, starts_on: "", ends_on: "", activate: true });
  }

  const sec = useMutation({
    mutationFn: (id: number) => post<Donem>(`/terms/${id}/activate`),
    onSuccess: () => qc.resetQueries(),
  });

  const sil = useMutation({
    mutationFn: (id: number) => del(`/terms/${id}`),
    onSuccess: () => qc.resetQueries(),
  });

  const geriAl = useMutation({
    mutationFn: (id: number) => post<Donem>(`/terms/${id}/restore`),
    onSuccess: tazele,
  });

  function ac(d?: Donem) {
    setDuzenlenen(d ?? null);
    setForm(
      d
        ? { name: d.name, starts_on: d.starts_on ?? "", ends_on: d.ends_on ?? "" }
        : BOS,
    );
    setAcik(true);
  }

  function ozet(d: Donem): string {
    const parcalar = SAYAC_ETIKETLERI.filter(([k]) => (d.counts[k] ?? 0) > 0).map(
      ([k, etiket]) => `${d.counts[k]} ${etiket}`,
    );
    return parcalar.length ? parcalar.join(" · ") : "boş";
  }

  const hata = [kaydet, sec, sil, geriAl].find((m) => m.error)?.error as Error | undefined;

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Dönemler"
        aciklama="Her dönem kendi zaman ızgarası, öğretmenleri, dersleri, şubeleri ve programlarıyla bağımsızdır."
        sag={
          <Buton onClick={() => ac()}>
            <Plus className="h-4 w-4" /> Yeni dönem
          </Buton>
        }
      />

      {hata && <Uyari tur="hata">{hata.message}</Uyari>}

      <Uyari>
        Yeni dönem <b>boş</b> başlar. Eskisinin devamı olacaksa dönemi <b>kopyalayın</b>:
        ızgara, binalar, öğretmenler, dersler, şubeler ve ders atamaları müsaitlik ve
        ayarlarıyla birlikte gelir; programlar gelmez. Tek tek seçmek isterseniz tanım
        ekranlarındaki <b>“Geçmiş dönemden aktar”</b> düğmesi duruyor.
      </Uyari>

      {kopyaSonuc && (
        <Uyari tur="basari">
          <b>{kopyaSonuc.term.name}</b> oluşturuldu
          {kopyaSonuc.term.is_active ? " ve aktif dönem yapıldı" : ""}. Kopyalanan:{" "}
          {KOPYA_ETIKETLERI
            .filter(([k]) => (kopyaSonuc.copied[k] ?? 0) > 0)
            .map(([k, ad]) => `${kopyaSonuc.copied[k]} ${ad}`)
            .join(", ")}
          .
        </Uyari>
      )}

      <Kart>
        {donemler.isLoading ? (
          <Yukleniyor />
        ) : (
          <Tablo basliklar={["Dönem", "Tarih", "İçerik", ""]}>
            {donemler.data?.map((d) => (
              <tr key={d.id} className="hover:bg-yuzey-alt">
                <td className="px-3 py-2.5">
                  <span className="flex items-center gap-2">
                    <span className="font-medium">{d.name}</span>
                    {d.is_active && <Rozet tur="iyi">Aktif</Rozet>}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-murekkep-silik">
                  {d.starts_on || d.ends_on
                    ? `${d.starts_on ?? "…"} → ${d.ends_on ?? "…"}`
                    : "—"}
                </td>
                <td className="px-3 py-2.5 text-murekkep-silik">{ozet(d)}</td>
                <td className="px-3 py-2.5 text-right">
                  <div className="flex justify-end gap-1">
                    {!d.is_active && (
                      <Buton
                        tur="ikincil"
                        className="whitespace-nowrap"
                        onClick={() => sec.mutate(d.id)}
                      >
                        <Check className="h-4 w-4" /> Bu döneme geç
                      </Buton>
                    )}
                    <Buton
                      tur="sade"
                      onClick={() => kopyaAc(d)}
                      aria-label="Kopyala"
                      title="Dönemin tamamını yeni bir döneme kopyala"
                    >
                      <Copy className="h-4 w-4" />
                    </Buton>
                    <Buton tur="sade" onClick={() => ac(d)} aria-label="Düzenle">
                      <Pencil className="h-4 w-4" />
                    </Buton>
                    <Buton
                      tur="sade"
                      aria-label="Sil"
                      onClick={() => {
                        if (
                          confirm(
                            `"${d.name}" dönemi gizlensin mi?\n\n` +
                              "Verisi silinmez; istediğiniz zaman geri alabilirsiniz.",
                          )
                        )
                          sil.mutate(d.id);
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

      <Kart
        baslik="Silinen dönemler"
        aciklama="Silinen dönemlerin verisi saklanır; geri alındığında olduğu gibi döner."
        sag={
          <Buton tur="ikincil" onClick={() => setSilinmisGoster((g) => !g)}>
            {silinmisGoster ? "Gizle" : "Göster"}
          </Buton>
        }
      >
        {!silinmisGoster ? (
          <p className="text-sm text-murekkep-silik">
            Hiçbir veri kalıcı olarak silinmez. Listeyi görmek için “Göster”e basın.
          </p>
        ) : silinmisler.isLoading ? (
          <Yukleniyor />
        ) : !silinmisler.data?.length ? (
          <p className="text-sm text-murekkep-silik">Silinmiş dönem yok.</p>
        ) : (
          <Tablo basliklar={["Dönem", "İçerik", ""]}>
            {silinmisler.data.map((d) => (
              <tr key={d.id} className="hover:bg-yuzey-alt">
                <td className="px-3 py-2.5 font-medium text-murekkep-yumusak">{d.name}</td>
                <td className="px-3 py-2.5 text-murekkep-silik">{ozet(d)}</td>
                <td className="px-3 py-2.5 text-right">
                  <Buton tur="ikincil" onClick={() => geriAl.mutate(d.id)}>
                    <RotateCcw className="h-4 w-4" /> Geri al
                  </Buton>
                </td>
              </tr>
            ))}
          </Tablo>
        )}
      </Kart>

      <Kutu
        acik={acik}
        kapat={() => setAcik(false)}
        baslik={duzenlenen ? "Dönemi düzenle" : "Yeni dönem"}
      >
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            kaydet.mutate();
          }}
        >
          {!duzenlenen && (
            <Uyari>
              Yeni dönem boş açılır ve hemen aktif olur. Tanımları geçmiş dönemden
              aktarabilirsiniz.
            </Uyari>
          )}
          <Alan etiket="Dönem adı">
            <Girdi
              required
              autoFocus
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="2027-2028 Güz Dönemi"
            />
          </Alan>
          <div className="grid gap-4 sm:grid-cols-2">
            <Alan etiket="Başlangıç" ipucu="İsteğe bağlı">
              <Girdi
                type="date"
                value={form.starts_on}
                onChange={(e) => setForm({ ...form, starts_on: e.target.value })}
              />
            </Alan>
            <Alan etiket="Bitiş" ipucu="İsteğe bağlı">
              <Girdi
                type="date"
                value={form.ends_on}
                onChange={(e) => setForm({ ...form, ends_on: e.target.value })}
              />
            </Alan>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Buton tur="ikincil" type="button" onClick={() => setAcik(false)}>
              Vazgeç
            </Buton>
            <Buton type="submit" yukleniyor={kaydet.isPending}>
              {duzenlenen ? "Kaydet" : "Dönemi oluştur"}
            </Buton>
          </div>
        </form>
      </Kutu>

      <Kutu
        acik={kopyaKaynak !== null}
        kapat={() => setKopyaKaynak(null)}
        baslik={`Dönemi kopyala: ${kopyaKaynak?.name ?? ""}`}
      >
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            kopyala.mutate();
          }}
        >
          <Uyari>
            Zaman ızgarası, binalar, öğretmenler ve şubeler (müsaitlikleriyle), dersler,
            ders atamaları (birleşikler dahil) ve dönem ayarları yeni döneme kopyalanır.
            Ders programları kopyalanmaz; yeni dönemde yeniden üretilir. Kaynak dönem
            olduğu gibi kalır.
          </Uyari>
          <Alan etiket="Yeni dönemin adı">
            <Girdi
              required
              autoFocus
              value={kopyaForm.name}
              onChange={(e) => setKopyaForm({ ...kopyaForm, name: e.target.value })}
            />
          </Alan>
          <div className="grid gap-4 sm:grid-cols-2">
            <Alan etiket="Başlangıç" ipucu="İsteğe bağlı">
              <Girdi
                type="date"
                value={kopyaForm.starts_on}
                onChange={(e) => setKopyaForm({ ...kopyaForm, starts_on: e.target.value })}
              />
            </Alan>
            <Alan etiket="Bitiş" ipucu="İsteğe bağlı">
              <Girdi
                type="date"
                value={kopyaForm.ends_on}
                onChange={(e) => setKopyaForm({ ...kopyaForm, ends_on: e.target.value })}
              />
            </Alan>
          </div>
          <label className="flex cursor-pointer items-center gap-2.5 text-sm">
            <input
              type="checkbox"
              checked={kopyaForm.activate}
              onChange={(e) => setKopyaForm({ ...kopyaForm, activate: e.target.checked })}
              className="h-4 w-4 rounded border-cizgi-guclu"
            />
            <span className="text-murekkep">Kopyayı hemen çalışılan dönem yap</span>
          </label>
          {kopyala.error && <Uyari tur="hata">{(kopyala.error as Error).message}</Uyari>}
          <div className="flex justify-end gap-2 pt-2">
            <Buton tur="ikincil" type="button" onClick={() => setKopyaKaynak(null)}>
              Vazgeç
            </Buton>
            <Buton type="submit" yukleniyor={kopyala.isPending}>
              <Copy className="h-4 w-4" /> Kopyala
            </Buton>
          </div>
        </form>
      </Kutu>
    </div>
  );
}
