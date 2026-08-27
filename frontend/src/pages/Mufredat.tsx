/** Şube bazında ders yükü: hangi şubede hangi ders, kaç saat, hangi öğretmenle. */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";

import {
  Alan, BosDurum, Buton, Girdi, Kart, Kutu, Secim, Tablo, Uyari, Yukleniyor,
} from "../components/ui";
import { get } from "../lib/api";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import type { Ders, Gun, MufredatSatiri, Ogretmen, Sube } from "../lib/types";

const BOS = {
  subject_id: 0,
  teacher_id: 0,
  weekly_hours: 4,
  block_size: 1,
  max_per_day: 2,
};

export default function Mufredat() {
  const subeler = useListe<Sube>("subeler", "/sections");
  const dersler = useListe<Ders>("dersler", "/subjects");
  const ogretmenler = useListe<Ogretmen>("ogretmenler", "/teachers");
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });

  const [subeId, setSubeId] = useState<number | null>(null);
  const secili = subeId ?? subeler.data?.[0]?.id ?? null;

  const mufredat = useQuery({
    queryKey: ["mufredat", secili],
    queryFn: () => get<MufredatSatiri[]>(`/curriculum?section_id=${secili}`),
    enabled: secili !== null,
  });
  const kaynak = useKaynak<any, MufredatSatiri>(`mufredat`, "/curriculum");

  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<MufredatSatiri | null>(null);
  const [form, setForm] = useState(BOS);

  const haftalikSlot = useMemo(
    () =>
      (izgara.data ?? [])
        .filter((g) => g.is_active)
        .reduce((t, g) => t + g.periods.filter((p) => !p.is_break).length, 0),
    [izgara.data],
  );
  const toplam = (mufredat.data ?? []).reduce((t, m) => t + m.weekly_hours, 0);

  function ac(m?: MufredatSatiri) {
    setDuzenlenen(m ?? null);
    setForm(
      m
        ? {
            subject_id: m.subject_id,
            teacher_id: m.teacher_id,
            weekly_hours: m.weekly_hours,
            block_size: m.block_size,
            max_per_day: m.max_per_day,
          }
        : {
            ...BOS,
            subject_id: dersler.data?.[0]?.id ?? 0,
            teacher_id: ogretmenler.data?.[0]?.id ?? 0,
          },
    );
    setAcik(true);
  }

  async function kaydet(e: React.FormEvent) {
    e.preventDefault();
    if (secili === null) return;
    const veri = { ...form, section_id: secili };
    if (duzenlenen) await kaynak.guncelle.mutateAsync({ id: duzenlenen.id, veri });
    else await kaynak.ekle.mutateAsync(veri);
    await mufredat.refetch();
    setAcik(false);
  }

  const hata = hataMetni(kaynak.ekle, kaynak.guncelle, kaynak.sil);
  const hazir = subeler.data?.length && dersler.data?.length && ogretmenler.data?.length;

  return (
    <div className="space-y-5">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Müfredat</h1>
          <p className="text-sm text-slate-500">
            Her şubenin haftalık ders yükü. Program bu tabloya göre üretilir.
          </p>
        </div>
        {hazir ? (
          <Buton onClick={() => ac()}>
            <Plus className="h-4 w-4" /> Ders ekle
          </Buton>
        ) : null}
      </header>

      {hata && <Uyari tur="hata">{hata}</Uyari>}

      {!hazir ? (
        <Kart>
          <BosDurum
            baslik="Önce tanımları tamamlayın"
            aciklama="Müfredat girebilmek için en az bir şube, bir ders ve bir öğretmen tanımlı olmalı."
          />
        </Kart>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            {subeler.data!.map((s) => (
              <button
                key={s.id}
                onClick={() => setSubeId(s.id)}
                className={
                  s.id === secili
                    ? "rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white"
                    : "rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                }
              >
                {s.name}
              </button>
            ))}
          </div>

          <Kart
            baslik={subeler.data!.find((s) => s.id === secili)?.name}
            aciklama={`Haftalık toplam ${toplam} saat · ızgarada ${haftalikSlot} ders saati var`}
            sag={
              toplam > haftalikSlot && haftalikSlot > 0 ? (
                <span className="rounded-md bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
                  {toplam - haftalikSlot} saat fazla
                </span>
              ) : null
            }
          >
            {mufredat.isLoading ? (
              <Yukleniyor />
            ) : !mufredat.data?.length ? (
              <BosDurum
                baslik="Bu şubede ders yok"
                aciklama="Şubeye okutulacak dersleri ve öğretmenlerini ekleyin."
                eylem={<Buton onClick={() => ac()}>Ders ekle</Buton>}
              />
            ) : (
              <Tablo
                basliklar={["Ders", "Öğretmen", "Haftalık", "Blok", "Günde en fazla", ""]}
              >
                {mufredat.data.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50">
                    <td className="px-3 py-2.5">
                      <span className="flex items-center gap-2.5">
                        <span
                          className="h-3 w-3 shrink-0 rounded-full"
                          style={{ background: m.subject.color }}
                        />
                        <span className="font-medium">{m.subject.name}</span>
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-slate-600">{m.teacher.full_name}</td>
                    <td className="px-3 py-2.5 text-slate-600">{m.weekly_hours} saat</td>
                    <td className="px-3 py-2.5 text-slate-600">
                      {m.block_size > 1 ? `${m.block_size}'li` : "tek"}
                    </td>
                    <td className="px-3 py-2.5 text-slate-600">{m.max_per_day}</td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="flex justify-end gap-1">
                        <Buton tur="sade" onClick={() => ac(m)} aria-label="Düzenle">
                          <Pencil className="h-4 w-4" />
                        </Buton>
                        <Buton
                          tur="sade"
                          onClick={async () => {
                            if (!confirm(`"${m.subject.name}" satırı silinsin mi?`)) return;
                            await kaynak.sil.mutateAsync(m.id);
                            mufredat.refetch();
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
        </>
      )}

      <Kutu
        acik={acik}
        kapat={() => setAcik(false)}
        baslik={duzenlenen ? "Müfredat satırını düzenle" : "Şubeye ders ekle"}
      >
        <form onSubmit={kaydet} className="space-y-4">
          <Alan etiket="Ders">
            <Secim
              value={form.subject_id}
              onChange={(e) => setForm({ ...form, subject_id: Number(e.target.value) })}
            >
              {dersler.data?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </Secim>
          </Alan>
          <Alan etiket="Öğretmen">
            <Secim
              value={form.teacher_id}
              onChange={(e) => setForm({ ...form, teacher_id: Number(e.target.value) })}
            >
              {ogretmenler.data?.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.full_name}
                  {o.branch ? ` · ${o.branch}` : ""}
                </option>
              ))}
            </Secim>
          </Alan>
          <div className="grid gap-4 sm:grid-cols-3">
            <Alan etiket="Haftalık saat">
              <Girdi
                required
                type="number"
                min={1}
                max={40}
                value={form.weekly_hours}
                onChange={(e) => setForm({ ...form, weekly_hours: Number(e.target.value) })}
              />
            </Alan>
            <Alan etiket="Blok boyu" ipucu="2 = çift ders">
              <Girdi
                required
                type="number"
                min={1}
                max={4}
                value={form.block_size}
                onChange={(e) => setForm({ ...form, block_size: Number(e.target.value) })}
              />
            </Alan>
            <Alan etiket="Günde en fazla">
              <Girdi
                required
                type="number"
                min={1}
                max={10}
                value={form.max_per_day}
                onChange={(e) => setForm({ ...form, max_per_day: Number(e.target.value) })}
              />
            </Alan>
          </div>
          <p className="text-xs text-slate-500">
            Blok boyu haftalık saatten büyük olamaz. Günlük sınır × gün sayısı, haftalık
            saati karşılamalıdır; aksi halde program yerleşmez.
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
    </div>
  );
}
