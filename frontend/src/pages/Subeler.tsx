import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarCheck, Download, Pencil, Plus, Trash2 } from "lucide-react";

import {
  Alan, BosDurum, Buton, Girdi, Kart, Kutu, SayfaBasligi, Secim, Tablo, Uyari,
  Yukleniyor,
} from "../components/ui";
import GecmisDonemdenAktar from "../components/GecmisDonemdenAktar";
import MusaitlikMatrisi from "../components/MusaitlikMatrisi";
import { get } from "../lib/api";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import type { Bina, Gun, Sube } from "../lib/types";

const BOS = {
  name: "",
  grade_level: "" as number | "",
  student_count: "" as number | "",
  building_id: "" as number | "",
  is_active: true,
};

export default function Subeler() {
  const liste = useListe<Sube>("subeler", "/sections");
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const binalar = useListe<Bina>("binalar", "/buildings");
  const kaynak = useKaynak<any, Sube>("subeler", "/sections");
  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<Sube | null>(null);
  const [form, setForm] = useState(BOS);
  const [musaitlikIcin, setMusaitlikIcin] = useState<Sube | null>(null);
  const [aktarimAcik, setAktarimAcik] = useState(false);

  function ac(s?: Sube) {
    setDuzenlenen(s ?? null);
    setForm(
      s
        ? {
            name: s.name,
            grade_level: s.grade_level ?? "",
            student_count: s.student_count ?? "",
            building_id: s.building_id ?? "",
            is_active: s.is_active,
          }
        : BOS,
    );
    setAcik(true);
  }

  async function kaydet(e: React.FormEvent) {
    e.preventDefault();
    const veri = {
      name: form.name,
      grade_level: form.grade_level === "" ? null : Number(form.grade_level),
      student_count: form.student_count === "" ? null : Number(form.student_count),
      building_id: form.building_id === "" ? null : Number(form.building_id),
      is_active: form.is_active,
    };
    if (duzenlenen) await kaynak.guncelle.mutateAsync({ id: duzenlenen.id, veri });
    else await kaynak.ekle.mutateAsync(veri);
    setAcik(false);
  }

  const hata = hataMetni(kaynak.ekle, kaynak.guncelle, kaynak.sil);
  const binaVar = (binalar.data?.length ?? 0) > 0;

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Şubeler"
        aciklama="Programı yapılacak sınıf şubeleri ve ders görebilecekleri saatler."
        sag={
          <>
            <Buton tur="ikincil" onClick={() => setAktarimAcik(true)}>
              <Download className="h-4 w-4" /> Geçmiş dönemden aktar
            </Buton>
            <Buton onClick={() => ac()}>
              <Plus className="h-4 w-4" /> Şube ekle
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
            baslik="Henüz şube yok"
            aciklama="Programı hazırlanacak şubeleri ekleyin."
            eylem={<Buton onClick={() => ac()}>Şube ekle</Buton>}
          />
        ) : (
          <Tablo
            basliklar={[
              "Şube",
              ...(binaVar ? ["Bina"] : []),
              "Sınıf seviyesi", "Öğrenci", "Durum", "",
            ]}
          >
            {liste.data.map((s) => (
              <tr key={s.id} className="hover:bg-yuzey-alt">
                <td className="px-3 py-2.5 font-medium">{s.name}</td>
                {binaVar && (
                  <td className="px-3 py-2.5 text-murekkep-silik">
                    {binalar.data?.find((b) => b.id === s.building_id)?.name ?? "—"}
                  </td>
                )}
                <td className="px-3 py-2.5 text-murekkep-silik">{s.grade_level ?? "—"}</td>
                <td className="px-3 py-2.5 text-murekkep-silik">{s.student_count ?? "—"}</td>
                <td className="px-3 py-2.5 text-murekkep-silik">
                  {s.is_active ? "Aktif" : "Pasif"}
                </td>
                <td className="px-3 py-2.5 text-right">
                  <div className="flex justify-end gap-1">
                    <Buton
                      tur="sade"
                      onClick={() => setMusaitlikIcin(s)}
                      aria-label="Müsaitlik"
                      title="Ders saati kısıtları"
                    >
                      <CalendarCheck className="h-4 w-4" />
                    </Buton>
                    <Buton tur="sade" onClick={() => ac(s)} aria-label="Düzenle">
                      <Pencil className="h-4 w-4" />
                    </Buton>
                    <Buton
                      tur="sade"
                      onClick={() => {
                        if (confirm(`"${s.name}" şubesi ve ders atamaları silinsin mi?`))
                          kaynak.sil.mutate(s.id);
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

      <Kutu acik={acik} kapat={() => setAcik(false)} baslik={duzenlenen ? "Şubeyi düzenle" : "Şube ekle"}>
        <form onSubmit={kaydet} className="space-y-4">
          <Alan etiket="Şube adı">
            <Girdi
              required
              autoFocus
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="5-A"
            />
          </Alan>
          <div className="grid gap-4 sm:grid-cols-2">
            <Alan etiket="Sınıf seviyesi" ipucu="1–13 arası. İsteğe bağlı.">
              <Girdi
                type="number"
                min={1}
                max={13}
                value={form.grade_level}
                onChange={(e) =>
                  setForm({ ...form, grade_level: e.target.value === "" ? "" : Number(e.target.value) })
                }
              />
            </Alan>
            <Alan etiket="Öğrenci sayısı" ipucu="İsteğe bağlı.">
              <Girdi
                type="number"
                min={0}
                value={form.student_count}
                onChange={(e) =>
                  setForm({ ...form, student_count: e.target.value === "" ? "" : Number(e.target.value) })
                }
              />
            </Alan>
          </div>

          {/* Bina yalnızca birden fazla bina tanımlıysa sorulur; tek binalı
              kurumu boş bir seçimle meşgul etmenin anlamı yok. */}
          {(binalar.data?.length ?? 0) > 0 && (
            <Alan
              etiket="Bina"
              ipucu="Şubenin dersliğinin bulunduğu bina. Boş bırakılırsa bina kuralları bu şubeyi kısıtlamaz."
            >
              <Secim
                value={form.building_id}
                onChange={(e) =>
                  setForm({
                    ...form,
                    building_id: e.target.value === "" ? "" : Number(e.target.value),
                  })
                }
              >
                <option value="">Bina seçilmedi</option>
                {binalar.data?.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                    {b.is_active ? "" : " · pasif"}
                  </option>
                ))}
              </Secim>
            </Alan>
          )}

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="form-check-input h-4 w-4"
            />
            Aktif (pasif şubeler programa dahil edilmez)
          </label>
          <p className="text-xs text-murekkep-silik">
            Şubenin yalnızca sabah ya da yalnızca akşam ders görmesi gerekiyorsa,
            kaydettikten sonra listedeki takvim düğmesinden saatlerini sınırlayın.
          </p>
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
        <GecmisDonemdenAktar<Sube>
          tur="sections"
          baslik="Geçmiş dönemden şube aktar"
          satirYazisi={(s) => ({
            ana: s.name,
            alt: s.grade_level ? `${s.grade_level}. sınıf` : undefined,
          })}
          tazelenecek={["subeler"]}
          kapat={() => setAktarimAcik(false)}
        />
      )}

      {musaitlikIcin && (
        <MusaitlikMatrisi
          baslik={`${musaitlikIcin.name} · ders saatleri`}
          yol={`/sections/${musaitlikIcin.id}`}
          aciklama="Şubenin ders görebileceği saatleri işaretleyin. Sabahçı şubelerde öğleden sonrasını, akşamcı şubelerde sabahı kapatın."
          gunler={izgara.data ?? []}
          kopyaHedefleri={(liste.data ?? [])
            .filter((s) => s.id !== musaitlikIcin.id)
            .map((s) => ({ id: s.id, name: s.name }))}
          kapat={() => setMusaitlikIcin(null)}
        />
      )}
    </div>
  );
}
