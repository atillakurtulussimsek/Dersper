/** Ders atamaları: hangi şubede hangi ders, kaç saat, hangi öğretmenle.
 *
 *  Aynı tabloya iki taraftan bakılabilir: ŞUBE bakışında bir şubenin dersleri,
 *  ÖĞRETMEN bakışında bir öğretmenin hangi şubelerde neyi okuttuğu listelenir.
 *  Atama her iki taraftan da yapılabilir — kayıt aynı kayıttır, yalnızca hangi
 *  alanın önceden dolu geldiği değişir.
 *
 *  Bir derse birden fazla öğretmen girebilir — aynı ders, farklı öğretmenle
 *  ikinci kez atanabilir (örneğin İngilizce'nin 2 saati bir, 2 saati başka
 *  öğretmende). Engellenen yalnızca birebir aynı şube–ders–öğretmen tekrarıdır.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Copy, Download, Pencil, Plus, Trash2 } from "lucide-react";

import {
  Alan, BosDurum, Buton, Girdi, Kart, Kutu, SayfaBasligi, Secim, Tablo,
  Uyari, Yukleniyor,
} from "../components/ui";
import GecmisDonemdenAktar from "../components/GecmisDonemdenAktar";
import MufredatKopyala from "../components/MufredatKopyala";
import { get } from "../lib/api";
import { desenCoz, desenEtiketi, desenOnerileri } from "../lib/bloklar";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import type { Ders, Gun, MufredatSatiri, Ogretmen, Sube } from "../lib/types";

const BOS = {
  section_id: 0,
  subject_id: 0,
  teacher_id: 0,
  weekly_hours: 4,
  block_pattern: "",
  max_per_day: 2,
};

type Bakis = "sube" | "ogretmen";

export default function DersAtamalari() {
  const subeler = useListe<Sube>("subeler", "/sections");
  const dersler = useListe<Ders>("dersler", "/subjects");
  const ogretmenler = useListe<Ogretmen>("ogretmenler", "/teachers");
  const izgara = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });

  const [bakis, setBakis] = useState<Bakis>("sube");
  const [subeId, setSubeId] = useState<number | null>(null);
  const [ogretmenId, setOgretmenId] = useState<number | null>(null);
  const seciliSube = subeId ?? subeler.data?.[0]?.id ?? null;
  const seciliOgretmen = ogretmenId ?? ogretmenler.data?.[0]?.id ?? null;
  // Listenin süzüldüğü kayıt — bakışa göre şube ya da öğretmen.
  const secili = bakis === "sube" ? seciliSube : seciliOgretmen;

  const mufredat = useQuery({
    queryKey: ["mufredat", bakis, secili],
    queryFn: () =>
      get<MufredatSatiri[]>(
        `/curriculum?${bakis === "sube" ? "section_id" : "teacher_id"}=${secili}`,
      ),
    enabled: secili !== null,
  });
  // Seçili kayıt kendi saatlerini kısıtlamış olabilir; doluluk buna göre
  // hesaplanır. Şube de öğretmen de aynı matrisi kullanıyor.
  const musaitlik = useQuery({
    queryKey: ["musaitlik", bakis, secili],
    queryFn: () =>
      get<{ period_id: number; state: string }[]>(
        `/${bakis === "sube" ? "sections" : "teachers"}/${secili}/availability`,
      ),
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
  const kapaliSaat = (musaitlik.data ?? []).filter(
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
            section_id: m.section_id,
            subject_id: m.subject_id,
            teacher_id: m.teacher_id,
            weekly_hours: m.weekly_hours,
            block_pattern: m.block_pattern,
            max_per_day: m.max_per_day,
          }
        : {
            ...BOS,
            // Hangi bakıştaysanız o taraf hazır gelir; öbürü seçilir.
            section_id: seciliSube ?? subeler.data?.[0]?.id ?? 0,
            teacher_id:
              bakis === "ogretmen"
                ? (seciliOgretmen ?? 0)
                : (ogretmenler.data?.[0]?.id ?? 0),
            subject_id: dersler.data?.[0]?.id ?? 0,
          },
    );
    setAcik(true);
  }

  async function kaydet(e: React.FormEvent) {
    e.preventDefault();
    if (!form.section_id || !form.teacher_id) return;
    if (duzenlenen) await kaynak.guncelle.mutateAsync({ id: duzenlenen.id, veri: form });
    else await kaynak.ekle.mutateAsync(form);
    await mufredat.refetch();
    setAcik(false);
  }

  const hata = hataMetni(kaynak.ekle, kaynak.guncelle, kaynak.sil);
  const hazir = subeler.data?.length && dersler.data?.length && ogretmenler.data?.length;

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Ders Atamaları"
        aciklama="Hangi şubede hangi dersi kimin, kaç saat okutacağı. Program bu tabloya göre üretilir."
        sag={
          <>
            <Buton tur="ikincil" onClick={() => setAktarimAcik(true)}>
              <Download className="h-4 w-4" /> Geçmiş dönemden aktar
            </Buton>
            {hazir ? (
              <Buton onClick={() => ac()}>
                <Plus className="h-4 w-4" /> Ders ata
              </Buton>
            ) : null}
          </>
        }
      />

      {hata && <Uyari tur="hata">{hata}</Uyari>}

      {!hazir ? (
        <Kart>
          <BosDurum
            baslik="Önce tanımları tamamlayın"
            aciklama="Ders ataması yapabilmek için en az bir şube, bir ders ve bir öğretmen tanımlı olmalı."
          />
        </Kart>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex shrink-0 rounded-lg border border-cizgi-guclu bg-yuzey p-0.5">
              {([["sube", "Şube"], ["ogretmen", "Öğretmen"]] as const).map(
                ([deger, etiket]) => (
                  <button
                    key={deger}
                    onClick={() => setBakis(deger)}
                    className={
                      bakis === deger
                        ? "rounded-md bg-vurgu px-2.5 py-1 text-xs font-medium text-uzeri"
                        : "rounded-md px-2.5 py-1 text-xs font-medium text-murekkep-yumusak hover:bg-yuzey-alt"
                    }
                  >
                    {etiket}
                  </button>
                ),
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {bakis === "sube"
                ? subeler.data!.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => setSubeId(s.id)}
                      className={
                        s.id === secili
                          ? "rounded-lg bg-vurgu px-3 py-1.5 text-sm font-medium text-uzeri"
                          : "rounded-lg border border-cizgi-guclu bg-yuzey px-3 py-1.5 text-sm text-murekkep-yumusak hover:bg-yuzey-alt"
                      }
                    >
                      {s.name}
                    </button>
                  ))
                : ogretmenler.data!.map((o) => (
                    <button
                      key={o.id}
                      onClick={() => setOgretmenId(o.id)}
                      className={
                        o.id === secili
                          ? "flex items-center gap-2 rounded-lg bg-vurgu px-3 py-1.5 text-sm font-medium text-uzeri"
                          : "flex items-center gap-2 rounded-lg border border-cizgi-guclu bg-yuzey px-3 py-1.5 text-sm text-murekkep-yumusak hover:bg-yuzey-alt"
                      }
                    >
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ background: o.color }}
                      />
                      {o.full_name}
                    </button>
                  ))}
            </div>
          </div>

          <Kart
            baslik={
              bakis === "sube"
                ? subeler.data!.find((s) => s.id === secili)?.name
                : ogretmenler.data!.find((o) => o.id === secili)?.full_name
            }
            aciklama={
              kapaliSaat > 0
                ? `Haftalık toplam ${toplam} saat · ` +
                  `${bakis === "sube" ? "şubeye" : "öğretmene"} ${kullanilabilir} saat açık ` +
                  `(${kapaliSaat} saat kapatılmış)`
                : `Haftalık toplam ${toplam} saat · ızgarada ${haftalikSlot} ders saati var`
            }
            sag={
              <div className="flex items-center gap-2">
                {toplam > kullanilabilir && kullanilabilir > 0 && (
                  <span className="rounded-md bg-hata-zemin px-2 py-1 text-xs font-medium text-hata">
                    {toplam - kullanilabilir} saat fazla
                  </span>
                )}
                {bakis === "sube" && mufredat.data && mufredat.data.length > 0 && (
                  <Buton
                    tur="ikincil"
                    onClick={() => setKopyalanacak(mufredat.data!)}
                    title="Bu şubenin tüm atamalarını başka şubelere kopyala"
                  >
                    <Copy className="h-4 w-4" /> Atamaları kopyala
                  </Buton>
                )}
              </div>
            }
          >
            {mufredat.isLoading ? (
              <Yukleniyor />
            ) : !mufredat.data?.length ? (
              <BosDurum
                baslik={
                  bakis === "sube"
                    ? "Bu şubede ders ataması yok"
                    : "Bu öğretmene ders atanmamış"
                }
                aciklama={
                  bakis === "sube"
                    ? "Şubeye okutulacak dersleri ve öğretmenlerini ekleyin."
                    : "Öğretmenin hangi şubede neyi okutacağını ekleyin."
                }
                eylem={<Buton onClick={() => ac()}>Ders ata</Buton>}
              />
            ) : (
              <Tablo
                basliklar={[
                  "Ders",
                  bakis === "sube" ? "Öğretmen" : "Şube",
                  "Haftalık", "Dağılım", "Günde en fazla", "",
                ]}
              >
                {mufredat.data.map((m) => (
                  <tr key={m.id} className="hover:bg-yuzey-alt">
                    <td className="px-3 py-2.5">
                      <span className="flex items-center gap-2.5">
                        <span
                          className="h-3 w-3 shrink-0 rounded-full"
                          style={{ background: m.subject.color }}
                        />
                        <span className="font-medium">{m.subject.name}</span>
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-murekkep-yumusak">
                      {bakis === "sube" ? (
                        <span className="flex items-center gap-2">
                          <span
                            className="h-2.5 w-2.5 shrink-0 rounded-full"
                            style={{ background: m.teacher.color }}
                          />
                          {m.teacher.full_name}
                        </span>
                      ) : (
                        <span className="font-medium text-murekkep">
                          {m.section.name}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-murekkep-yumusak">{m.weekly_hours} saat</td>
                    <td className="px-3 py-2.5 font-mono text-xs text-murekkep-yumusak">
                      {desenEtiketi(m.block_pattern, m.weekly_hours)}
                    </td>
                    <td className="px-3 py-2.5 text-murekkep-yumusak">{m.max_per_day}</td>
                    <td className="px-3 py-2.5 text-right">
                      <div className="flex justify-end gap-1">
                        {bakis === "sube" && (
                          <Buton
                            tur="sade"
                            onClick={() => setKopyalanacak([m])}
                            aria-label="Kopyala"
                            title="Bu dersi başka şubelere kopyala"
                          >
                            <Copy className="h-4 w-4" />
                          </Buton>
                        )}
                        <Buton tur="sade" onClick={() => ac(m)} aria-label="Düzenle">
                          <Pencil className="h-4 w-4" />
                        </Buton>
                        <Buton
                          tur="sade"
                          onClick={async () => {
                            if (
                              !confirm(
                                `"${m.subject.name} · ${m.teacher.full_name}" ataması silinsin mi?`,
                              )
                            )
                              return;
                            await kaynak.sil.mutateAsync(m.id);
                            mufredat.refetch();
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
        </>
      )}

      {aktarimAcik && (
        <GecmisDonemdenAktar<MufredatSatiri>
          tur="curriculum"
          baslik="Geçmiş dönemden ders ataması aktar"
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
          hedefAdaylari={(subeler.data ?? []).filter((s) => s.id !== seciliSube)}
          kapat={() => {
            setKopyalanacak(null);
            mufredat.refetch();
          }}
        />
      )}

      <Kutu
        acik={acik}
        kapat={() => setAcik(false)}
        baslik={duzenlenen ? "Ders atamasını düzenle" : "Ders ata"}
      >
        <form onSubmit={kaydet} className="space-y-4">
          {/* Şube ve öğretmen ikisi de burada seçilir; hangi bakıştaysanız o
              taraf hazır gelir. Böylece atama iki taraftan da yapılabiliyor. */}
          <Alan etiket="Şube">
            <Secim
              value={form.section_id}
              onChange={(e) => setForm({ ...form, section_id: Number(e.target.value) })}
            >
              {subeler.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                  {s.is_active ? "" : " · pasif"}
                </option>
              ))}
            </Secim>
          </Alan>

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
          <p className="-mt-2 text-xs text-murekkep-silik">
            Aynı dersi farklı öğretmenlerle birden çok kez atayabilirsiniz; saatler
            öğretmenler arasında bölünür.
          </p>

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
                    ? "rounded-lg bg-vurgu px-2.5 py-1 font-mono text-xs text-uzeri"
                    : "rounded-lg border border-cizgi-guclu bg-yuzey px-2.5 py-1 font-mono text-xs text-murekkep-yumusak hover:bg-yuzey-alt"
                }
              >
                {o}
              </button>
            ))}
          </div>

          <p className="text-xs text-murekkep-silik">
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
