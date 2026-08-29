import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";

import {
  Alan, BosDurum, Buton, Girdi, Kart, Kutu, Rozet, SayfaBasligi, Tablo,
  Uyari, Yukleniyor,
} from "../components/ui";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import type { Program, ProgramDurumu } from "../lib/types";

const DURUM: Record<ProgramDurumu, { etiket: string; tur: "notr" | "iyi" | "uyari" }> = {
  taslak: { etiket: "Taslak", tur: "notr" },
  uretildi: { etiket: "Üretildi", tur: "iyi" },
  yayinda: { etiket: "Yayında", tur: "uyari" },
};

export default function Programlar() {
  const navigate = useNavigate();
  const liste = useListe<Program>("programlar", "/timetables");
  const kaynak = useKaynak<{ name: string }, Program>("programlar", "/timetables");
  const [acik, setAcik] = useState(false);
  const [ad, setAd] = useState("");

  async function olustur(e: React.FormEvent) {
    e.preventDefault();
    const p = await kaynak.ekle.mutateAsync({ name: ad });
    setAcik(false);
    setAd("");
    navigate(`/programlar/${p.id}`);
  }

  const hata = hataMetni(kaynak.ekle, kaynak.sil);

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Ders Programları"
        aciklama="Birden çok program taslağı tutabilir, karşılaştırıp birini yayınlayabilirsiniz."
        sag={
          <Buton onClick={() => setAcik(true)}>
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
            eylem={<Buton onClick={() => setAcik(true)}>Yeni program</Buton>}
          />
        ) : (
          <Tablo basliklar={["Program", "Durum", "Oluşturulma", ""]}>
            {liste.data.map((p) => (
              <tr
                key={p.id}
                className="cursor-pointer hover:bg-yuzey-alt"
                onClick={() => navigate(`/programlar/${p.id}`)}
              >
                <td className="px-3 py-2.5 font-medium">{p.name}</td>
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
          <div className="flex justify-end gap-2">
            <Buton tur="ikincil" type="button" onClick={() => setAcik(false)}>
              Vazgeç
            </Buton>
            <Buton type="submit" yukleniyor={kaynak.ekle.isPending}>
              Oluştur
            </Buton>
          </div>
        </form>
      </Kutu>
    </div>
  );
}
