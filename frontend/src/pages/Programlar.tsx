import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";

import {
  Alan, BosDurum, Buton, Girdi, Kart, Kutu, Rozet, SayfaBasligi, Tablo,
  Uyari, Yukleniyor,
} from "../components/ui";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import type { Program, ProgramDurumu, Sube } from "../lib/types";

const DURUM: Record<ProgramDurumu, { etiket: string; tur: "notr" | "iyi" | "uyari" }> = {
  taslak: { etiket: "Taslak", tur: "notr" },
  uretildi: { etiket: "Üretildi", tur: "iyi" },
  yayinda: { etiket: "Yayında", tur: "uyari" },
};

export default function Programlar() {
  const navigate = useNavigate();
  const liste = useListe<Program>("programlar", "/timetables");
  const subeler = useListe<Sube>("subeler", "/sections");
  const kaynak = useKaynak<{ name: string; section_ids: number[] | null }, Program>(
    "programlar",
    "/timetables",
  );
  const [acik, setAcik] = useState(false);
  const [ad, setAd] = useState("");
  const [secili, setSecili] = useState<number[]>([]);

  const adaylar = subeler.data ?? [];
  const hepsiSecili = adaylar.length > 0 && secili.length === adaylar.length;

  function ac() {
    // Olağan durum tüm şubelerdir; seçim yalnızca daraltmak içindir.
    setSecili(adaylar.map((s) => s.id));
    setAcik(true);
  }

  function degistir(id: number) {
    setSecili((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  async function olustur(e: React.FormEvent) {
    e.preventDefault();
    const p = await kaynak.ekle.mutateAsync({
      name: ad,
      // Hepsi seçiliyse "tüm şubeler" olarak kaydedilir; sonradan eklenen
      // şubeler de programa girer.
      section_ids: hepsiSecili ? null : secili,
    });
    setAcik(false);
    setAd("");
    navigate(`/programlar/${p.id}`);
  }

  function kapsamMetni(p: Program) {
    if (p.section_ids === null) return "Tüm şubeler";
    const adlar = p.section_ids
      .map((id) => adaylar.find((s) => s.id === id)?.name)
      .filter(Boolean);
    return adlar.length ? adlar.join(", ") : `${p.section_ids.length} şube`;
  }

  const hata = hataMetni(kaynak.ekle, kaynak.sil);

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Ders Programları"
        aciklama="Birden çok program taslağı tutabilir, karşılaştırıp birini yayınlayabilirsiniz."
        sag={
          <Buton onClick={ac}>
            <Plus className="h-4 w-4" /> Yeni program
          </Buton>
        }
      />

      {hata && <Uyari tur="hata">{hata}</Uyari>}

      <Kart>
        {liste.isLoading ? (
          <Yukleniyor />
        ) : !liste.data?.length ? (
          <BosDurum
            baslik="Henüz program yok"
            aciklama="Yeni bir program oluşturup otomatik üretimi başlatın."
            eylem={<Buton onClick={ac}>Yeni program</Buton>}
          />
        ) : (
          <Tablo basliklar={["Program", "Şubeler", "Durum", "Oluşturulma", ""]}>
            {liste.data.map((p) => (
              <tr
                key={p.id}
                className="cursor-pointer hover:bg-yuzey-alt"
                onClick={() => navigate(`/programlar/${p.id}`)}
              >
                <td className="px-3 py-2.5 font-medium">{p.name}</td>
                <td className="max-w-64 truncate px-3 py-2.5 text-murekkep-silik">
                  {kapsamMetni(p)}
                </td>
                <td className="px-3 py-2.5">
                  <Rozet tur={DURUM[p.status].tur}>{DURUM[p.status].etiket}</Rozet>
                </td>
                <td className="px-3 py-2.5 text-murekkep-silik">
                  {new Date(p.created_at).toLocaleString("tr-TR")}
                </td>
                <td className="px-3 py-2.5 text-right">
                  <Buton
                    tur="sade"
                    aria-label="Sil"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`"${p.name}" programı silinsin mi?`)) kaynak.sil.mutate(p.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4 text-hata" />
                  </Buton>
                </td>
              </tr>
            ))}
          </Tablo>
        )}
      </Kart>

      <Kutu acik={acik} kapat={() => setAcik(false)} baslik="Yeni ders programı">
        <form onSubmit={olustur} className="space-y-4">
          <Alan etiket="Program adı">
            <Girdi
              required
              autoFocus
              value={ad}
              onChange={(e) => setAd(e.target.value)}
              placeholder="2026-2027 Güz Dönemi"
            />
          </Alan>

          <Alan etiket="Programa dahil şubeler">
            {!adaylar.length ? (
              <Uyari>Bu dönemde şube yok. Önce Şubeler sayfasından şube ekleyin.</Uyari>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-murekkep-silik">
                    {hepsiSecili
                      ? "Tüm şubeler dahil."
                      : `${secili.length} / ${adaylar.length} şube seçili.`}
                  </span>
                  <Buton
                    tur="sade"
                    type="button"
                    onClick={() =>
                      setSecili(hepsiSecili ? [] : adaylar.map((s) => s.id))
                    }
                  >
                    {hepsiSecili ? "Hiçbirini seçme" : "Hepsini seç"}
                  </Buton>
                </div>
                <div className="max-h-56 space-y-1 overflow-y-auto rounded-lg border border-cizgi p-2">
                  {adaylar.map((s) => (
                    <label
                      key={s.id}
                      className="flex cursor-pointer items-center gap-2.5 rounded-md px-2 py-1.5 text-sm hover:bg-yuzey-alt"
                    >
                      <input
                        type="checkbox"
                        checked={secili.includes(s.id)}
                        onChange={() => degistir(s.id)}
                        className="h-4 w-4 rounded border-cizgi-guclu"
                      />
                      <span className="font-medium">{s.name}</span>
                      {!s.is_active && (
                        <span className="text-xs text-murekkep-silik">pasif</span>
                      )}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </Alan>

          <div className="flex justify-end gap-2">
            <Buton tur="ikincil" type="button" onClick={() => setAcik(false)}>
              Vazgeç
            </Buton>
            <Buton
              type="submit"
              disabled={!secili.length}
              yukleniyor={kaynak.ekle.isPending}
            >
              Oluştur
            </Buton>
          </div>
        </form>
      </Kutu>
    </div>
  );
}
