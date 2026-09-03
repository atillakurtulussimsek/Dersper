import { useEffect, useState } from "react";
import {
  DndContext, PointerSensor, closestCenter, useDraggable, useDroppable,
  useSensor, useSensors, type DragEndEvent,
} from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownAZ, CalendarCheck, Download, GripVertical, Pencil, Plus, Trash2,
} from "lucide-react";
import clsx from "clsx";

import {
  Alan, BosDurum, Buton, Girdi, Kart, Kutu, SayfaBasligi, Secim, Tablo, Uyari,
  Yukleniyor,
} from "../components/ui";
import GecmisDonemdenAktar from "../components/GecmisDonemdenAktar";
import MusaitlikMatrisi from "../components/MusaitlikMatrisi";
import { get, put } from "../lib/api";
import { hataMetni, useKaynak, useListe } from "../lib/hooks";
import { SIRA_SECENEKLERI } from "../lib/siralama";
import type { Bina, Donem, Gun, Sube } from "../lib/types";

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

  // Sıralama: dönem ayarı "ad" ya da "elle". Elle kipinde satırlar sürüklenir,
  // taslak sıra burada durur, "Sırayı kaydet" sunucuya yazar.
  const qc = useQueryClient();
  const donemler = useQuery({ queryKey: ["donemler"], queryFn: () => get<Donem[]>("/terms") });
  const aktifDonem = (donemler.data ?? []).find((d) => d.is_active);
  const elle = aktifDonem?.section_order === "elle";
  const [taslakSira, setTaslakSira] = useState<number[] | null>(null);
  useEffect(() => setTaslakSira(null), [liste.data]);

  const sirayiDegistir = useMutation({
    mutationFn: (secilen: "ad" | "elle") =>
      put<Donem>(`/terms/${aktifDonem!.id}`, {
        name: aktifDonem!.name,
        starts_on: aktifDonem!.starts_on,
        ends_on: aktifDonem!.ends_on,
        block_building_switch: aktifDonem!.block_building_switch,
        conflict_basis: aktifDonem!.conflict_basis,
        section_order: secilen,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["donemler"] });
      qc.invalidateQueries({ queryKey: ["subeler"] });
    },
  });
  const sirayiKaydet = useMutation({
    mutationFn: (ids: number[]) => put<Sube[]>("/sections/order", { ids }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subeler"] });
      qc.invalidateQueries({ queryKey: ["donemler"] });
      setTaslakSira(null);
    },
  });

  const sirali: Sube[] = (() => {
    const kayitlar = liste.data ?? [];
    if (!taslakSira) return kayitlar;
    const harita = new Map(kayitlar.map((s) => [s.id, s]));
    return taslakSira.map((id) => harita.get(id)!).filter(Boolean);
  })();

  const sensorler = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));
  function surukleBitti(e: DragEndEvent) {
    if (!e.over || e.active.id === e.over.id) return;
    const ids = sirali.map((s) => s.id);
    const kaynak = ids.indexOf(Number(e.active.id));
    const hedef = ids.indexOf(Number(e.over.id));
    if (kaynak < 0 || hedef < 0) return;
    const yeni = [...ids];
    yeni.splice(hedef, 0, ...yeni.splice(kaynak, 1));
    setTaslakSira(yeni);
  }
  function kaydir(id: number, yon: -1 | 1) {
    const ids = sirali.map((s) => s.id);
    const i = ids.indexOf(id);
    const j = i + yon;
    if (i < 0 || j < 0 || j >= ids.length) return;
    const yeni = [...ids];
    [yeni[i], yeni[j]] = [yeni[j], yeni[i]];
    setTaslakSira(yeni);
  }

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

      {aktifDonem && (liste.data?.length ?? 0) > 1 && (
        <Kart
          baslik="Şubeler nasıl sıralansın?"
          aciklama="Bu sıra her yerde geçerli: listeler, ders atama şeritleri, program şeritleri, çarşaf ve çıktılar."
          sag={<ArrowDownAZ className="h-4 w-4 text-murekkep-silik" />}
        >
          <div className="grid gap-1.5 sm:grid-cols-2">
            {SIRA_SECENEKLERI.map((se) => (
              <label
                key={se.id}
                className={clsx(
                  "flex cursor-pointer gap-2.5 rounded-lg border px-3 py-2",
                  aktifDonem.section_order === se.id
                    ? "border-cizgi-guclu bg-yuzey-alt"
                    : "border-cizgi hover:bg-yuzey-alt",
                )}
              >
                <input
                  type="radio"
                  name="sube-sirasi"
                  checked={aktifDonem.section_order === se.id}
                  disabled={sirayiDegistir.isPending}
                  onChange={() => sirayiDegistir.mutate(se.id)}
                  className="mt-0.5 h-4 w-4 border-cizgi-guclu"
                />
                <span className="text-sm">
                  <span className="font-medium text-murekkep">{se.etiket}</span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-murekkep-silik">
                    {se.aciklama}
                  </span>
                </span>
              </label>
            ))}
          </div>
          {elle && (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs text-murekkep-silik">
                {taslakSira
                  ? "Sıra değişti, henüz kaydedilmedi."
                  : "Satırları tutamağından sürükleyin ya da tutamağa odaklanıp ok tuşlarını kullanın."}
              </span>
              <div className="flex gap-2">
                {taslakSira && (
                  <Buton tur="ikincil" onClick={() => setTaslakSira(null)}>
                    Vazgeç
                  </Buton>
                )}
                <Buton
                  disabled={!taslakSira}
                  yukleniyor={sirayiKaydet.isPending}
                  onClick={() => sirayiKaydet.mutate(sirali.map((s) => s.id))}
                >
                  Sırayı kaydet
                </Buton>
              </div>
            </div>
          )}
          {(sirayiDegistir.error || sirayiKaydet.error) && (
            <Uyari tur="hata">
              {((sirayiDegistir.error ?? sirayiKaydet.error) as Error).message}
            </Uyari>
          )}
        </Kart>
      )}

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
          <DndContext sensors={sensorler} collisionDetection={closestCenter} onDragEnd={surukleBitti}>
          <Tablo
            basliklar={[
              ...(elle ? [""] : []),
              "Şube",
              ...(binaVar ? ["Bina"] : []),
              "Sınıf seviyesi", "Öğrenci", "Durum", "",
            ]}
          >
            {sirali.map((s, i) => (
              <SubeSatiri key={s.id} id={s.id} surukle={elle}>
                {elle && (
                  <td className="w-8 px-1 py-2.5">
                    <Tutamak
                      id={s.id}
                      ilk={i === 0}
                      son={i === sirali.length - 1}
                      kaydir={(yon) => kaydir(s.id, yon)}
                    />
                  </td>
                )}
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
              </SubeSatiri>
            ))}
          </Tablo>
          </DndContext>
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
              className="h-4 w-4 rounded border-cizgi-guclu"
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


/** Sürüklenebilir tablo satırı: bırakma hedefi satırın kendisidir. */
function SubeSatiri({
  id,
  surukle,
  children,
}: {
  id: number;
  surukle: boolean;
  children: React.ReactNode;
}) {
  const { setNodeRef, isOver } = useDroppable({ id, disabled: !surukle });
  return (
    <tr
      ref={setNodeRef}
      className={clsx("hover:bg-yuzey-alt", isOver && "bg-yuzey-alt ring-1 ring-inset ring-cizgi-guclu")}
    >
      {children}
    </tr>
  );
}

/** Sürükleme tutamağı; klavyede yukarı/aşağı ok da işler. */
function Tutamak({
  id,
  ilk,
  son,
  kaydir,
}: {
  id: number;
  ilk: boolean;
  son: boolean;
  kaydir: (yon: -1 | 1) => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id });
  return (
    <button
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      type="button"
      title="Sürükleyerek taşıyın — yukarı/aşağı ok tuşları da çalışır"
      onKeyDown={(e) => {
        if (e.key === "ArrowUp" && !ilk) {
          e.preventDefault();
          kaydir(-1);
        } else if (e.key === "ArrowDown" && !son) {
          e.preventDefault();
          kaydir(1);
        }
      }}
      className={clsx(
        "cursor-grab rounded-md p-1 text-murekkep-silik hover:bg-yuzey-alt hover:text-murekkep-yumusak active:cursor-grabbing",
        isDragging && "opacity-40",
      )}
    >
      <GripVertical className="h-4 w-4" />
    </button>
  );
}
