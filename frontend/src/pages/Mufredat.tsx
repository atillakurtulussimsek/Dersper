/** Şube bazında ders yükü: hangi şubede hangi ders, kaç saat, hangi öğretmenle. */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Copy, Download, Pencil, Plus, Trash2 } from "lucide-react";

import {
  Alan, BosDurum, Buton, Girdi, Kart, Kutu, Secim, Tablo, Uyari, Yukleniyor,
} from "../components/ui";
import GecmisDonemdenAktar from "../components/GecmisDonemdenAktar";
import MufredatKopyala from "../components/MufredatKopyala";
import { get } from "../lib/api";
import { desenCoz, desenEtiketi, desenOnerileri } from "../lib/bloklar";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import type { Ders, Gun, MufredatSatiri, Ogretmen, Sube } from "../lib/types";

const BOS = {
  subject_id: 0,
  teacher_id: 0,
  weekly_hours: 4,
  block_pattern: "",
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
  // Şube kendi saatlerini kısıtlamış olabilir; doluluk buna göre hesaplanır.
  const subeMusaitlik = useQuery({
    queryKey: ["sube-musaitlik", secili],
    queryFn: () =>
      get<{ period_id: number; state: string }[]>(`/sections/${secili}/availability`),
    enabled: secili !== null,
  });
  const kaynak = useKaynak<any, MufredatSatiri>(`mufredat`, "/curriculum");

  const [acik, setAcik] = useState(false);
  const [duzenlenen, setDuzenlenen] = useState<MufredatSatiri | null>(null);
  const [form, setForm] = useState(BOS);
  // Kopyalama kutusunda gösterilecek satırlar; boşsa kutu kapalı.
  const [kopyalanacak, setKopyalanacak] = useState<MufredatSatiri[] | null>(null);
  const [aktarimAcik, setAktarimAcik] = useState(false);

  const haftalikSlot = useMemo(
    () =>
      (izgara.data ?? [])
        .filter((g) => g.is_active)
        .reduce((t, g) => t + g.periods.filter((p) => !p.is_break).length, 0),
    [izgara.data],
  );
  const kapaliSaat = (subeMusaitlik.data ?? []).filter(
    (h) => h.state === "uygun_degil",
  ).length;
  const kullanilabilir = Math.max(0, haftalikSlot - kapaliSaat);
  const toplam = (mufredat.data ?? []).reduce((t, m) => t + m.weekly_hours, 0);

  const desen = desenCoz(form.block_pattern, form.weekly_hours);

  function ac(m?: MufredatSatiri) {
    setDuzenlenen(m ?? null);
    setForm(
      m
        ? {
            subject_id: m.subject_id,
            teacher_id: m.teacher_id,
            weekly_hours: m.weekly_hours,
            block_pattern: m.block_pattern,
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
        <div className="flex gap-2">
          <Buton tur="ikincil" onClick={() => setAktarimAcik(true)}>
            <Download className="h-4 w-4" /> Geçmiş dönemden aktar
          </Buton>
          {hazir ? (
            <Buton onClick={() => ac()}>
              <Plus className="h-4 w-4" /> Ders ekle
            </Buton>
          ) : null}
        </div>
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
            aciklama={
              kapaliSaat > 0
                ? `Haftalık toplam ${toplam} saat · şubeye ${kullanilabilir} saat açık ` +
                  `(${kapaliSaat} saat kapatılmış)`
                : `Haftalık toplam ${toplam} saat · ızgarada ${haftalikSlot} ders saati var`
            }
            sag={
              <div className="flex items-center gap-2">
                {toplam > kullanilabilir && kullanilabilir > 0 && (
                  <span className="rounded-md bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
                    {toplam - kullanilabilir} saat fazla
                  </span>
                )}
                {mufredat.data && mufredat.data.length > 0 && (
                  <Buton
                    tur="ikincil"
                    onClick={() => setKopyalanacak(mufredat.data!)}
                    title="Bu şubenin tüm müfredatını başka şubelere kopyala"
                  >
                    <Copy className="h-4 w-4" /> Müfredatı kopyala
                  </Buton>
                )}
              </div>
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
                basliklar={["Ders", "Öğretmen", "Haftalık", "Dağılım", "Günde en fazla", ""]}
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
                    <td className="px-3 py-2.5 text-slate-600">
                      <span className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 shrink-0 rounded-full"
                          style={{ background: m.teacher.color }}
                        />
                        {m.teacher.full_name}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-slate-600">{m.weekly_hours} saat</td>
                    <td className="px-3 py-2.5 font-mono text-xs text-slate-600">
                      {desenEtiketi(m.block_pattern, m.weekly_hours)}
                    </td>
                    <td className="px-3 py-2.5 text-slate-600">{m.max_per_day}</td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="flex justify-end gap-1">
                        <Buton
                          tur="sade"
                          onClick={() => setKopyalanacak([m])}
                          aria-label="Kopyala"
                          title="Bu dersi başka şubelere kopyala"
                        >
                          <Copy className="h-4 w-4" />
                        </Buton>
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

      {aktarimAcik && (
        <GecmisDonemdenAktar<MufredatSatiri>
          tur="curriculum"
          baslik="Geçmiş dönemden müfredat aktar"
          satirYazisi={(m) => ({
            ana: `${m.section.name} · ${m.subject.name}`,
            alt: `${m.weekly_hours} saat · ${m.teacher.full_name}`,
          })}
          tazelenecek={["mufredat", "mufredat-hepsi"]}
          kapat={() => {
            setAktarimAcik(false);
            mufredat.refetch();
          }}
        />
      )}

      {kopyalanacak && (
        <MufredatKopyala
          satirlar={kopyalanacak}
          hedefAdaylari={(subeler.data ?? []).filter((s) => s.id !== secili)}
          kapat={() => {
            setKopyalanacak(null);
            mufredat.refetch();
          }}
        />
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
          <div className="grid gap-4 sm:grid-cols-2">
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

          <Alan
            etiket="Ders dağılımı"
            ipucu="Haftalık saatin gün içinde nasıl bölüneceği. Boş bırakılırsa saatler tek tek dağıtılır."
            hata={desen.hata ?? undefined}
          >
            <Girdi
              value={form.block_pattern}
              onChange={(e) => setForm({ ...form, block_pattern: e.target.value })}
              placeholder={`örn. ${desenOnerileri(form.weekly_hours)[1] ?? "2+2+1"}`}
              className="font-mono"
            />
          </Alan>

          <div className="flex flex-wrap items-center gap-2">
            {desenOnerileri(form.weekly_hours).map((o) => (
              <button
                key={o}
                type="button"
                onClick={() => setForm({ ...form, block_pattern: o })}
                className={
                  form.block_pattern.replace(/[,\s]+/g, "+") === o
                    ? "rounded-lg bg-slate-900 px-2.5 py-1 font-mono text-xs text-white"
                    : "rounded-lg border border-slate-300 bg-white px-2.5 py-1 font-mono text-xs text-slate-700 hover:bg-slate-50"
                }
              >
                {o}
              </button>
            ))}
          </div>

          <p className="text-xs text-slate-500">
            <b>2+2+1</b>: iki gün çift ders, bir gün tek saat. <b>1+1+1+1+1</b>: beş ayrı
            saat. Blokların toplamı haftalık saate eşit olmalı; günlük sınır da bu
            dağılımı karşılamalıdır.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Buton tur="ikincil" type="button" onClick={() => setAcik(false)}>
              Vazgeç
            </Buton>
            <Buton
              type="submit"
              disabled={!desen.gecerli}
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
