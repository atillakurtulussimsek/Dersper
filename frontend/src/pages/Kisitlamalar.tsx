/** Kısıtlamalar: programı bağlayan kuralların tek yerden yönetimi.
 *
 *  Kurallar önceden ilgili ekranlara dağılmıştı (bina kuralı Binalar'da,
 *  çakışma ölçütü Zaman Izgarası'nda). Program üretimini etkileyen her şey
 *  burada durur; yeni kısıt türleri de buraya kart olarak eklenir.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlarmClock, Building2, Merge, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Alan, Buton, Girdi, Kart, SayfaBasligi, Secim, Uyari, Yukleniyor } from "../components/ui";
import { del, get, post, put } from "../lib/api";
import { OLCUT_SECENEKLERI } from "../lib/cakisma";
import { useListe } from "../lib/hooks";
import type {
  Bina, BirlestirmeCifti, BirlestirmeKurali, CakismaOlcutu, Donem, Gun, Sube,
} from "../lib/types";

/** Şube birleştirme kuralları: "9-A ile 9-B, Cumartesi, tam 4 saat".
 *  Hangi dersin ortak okutulacağını program üretimi seçer: iki şubede aynı
 *  öğretmenin verdiği aynı dersler eşlenir, toplam tam kuralın saati kadar
 *  ortak saat konur. */
function SubeBirlestirme({ subeler }: { subeler: Sube[] }) {
  const qc = useQueryClient();
  const kurallar = useQuery({
    queryKey: ["birlestirme"],
    queryFn: () => get<BirlestirmeKurali[]>("/merge-rules"),
  });
  const gunler = useQuery({ queryKey: ["timegrid"], queryFn: () => get<Gun[]>("/timegrid") });
  const aktifGunler = (gunler.data ?? []).filter((g) => g.is_active);

  const [a, setA] = useState<number | "">("");
  const [b, setB] = useState<number | "">("");
  const [secilenGunler, setSecilenGunler] = useState<number[]>([]);
  const [saat, setSaat] = useState(1);

  const onIzleme = useQuery({
    queryKey: ["birlestirme-onizleme", a, b],
    queryFn: () =>
      get<{ pairs: BirlestirmeCifti[]; max_hours: number }>(
        `/merge-rules/preview?section_a_id=${a}&section_b_id=${b}`,
      ),
    enabled: a !== "" && b !== "" && a !== b,
  });

  const tazele = () => qc.invalidateQueries({ queryKey: ["birlestirme"] });
  const ekle = useMutation({
    mutationFn: () =>
      post<BirlestirmeKurali>("/merge-rules", {
        section_a_id: a, section_b_id: b, hours: saat, day_indexes: secilenGunler,
      }),
    onSuccess: () => {
      tazele();
      setA(""); setB(""); setSecilenGunler([]); setSaat(1);
    },
  });
  const sil = useMutation({
    mutationFn: (id: number) => del(`/merge-rules/${id}`),
    onSuccess: tazele,
  });

  const enFazla = onIzleme.data?.max_hours ?? 0;
  const gunDegistir = (i: number) =>
    setSecilenGunler((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i].sort()));
  const gonderilebilir =
    a !== "" && b !== "" && a !== b && secilenGunler.length > 0 && saat >= 1 && saat <= enFazla;

  return (
    <Kart
      baslik="Şube birleştirme"
      aciklama="İki şube seçilen günlerde tam bu kadar saat birlikte ders görür. Hangi dersin ortak okutulacağını program üretimi seçer: iki şubede aynı öğretmenin verdiği aynı dersler eşlenir, programın kurulmasını sağlayan dağılım bulunur. Ortak saat iki dersin haftalık saatinden birer düşer."
      sag={<Merge className="h-4 w-4 text-murekkep-silik" />}
    >
      {(kurallar.data ?? []).length > 0 && (
        <ul className="mb-5 divide-y divide-cizgi rounded-lg border border-cizgi">
          {kurallar.data!.map((k) => (
            <li key={k.id} className="flex items-start gap-3 px-4 py-3">
              <div className="min-w-0 flex-1 text-sm">
                <p className="font-medium text-murekkep">
                  {k.section_a_name} + {k.section_b_name} · {k.day_names.join(", ")} · tam {k.hours} saat
                </p>
                <p className="mt-0.5 text-xs text-murekkep-silik">
                  Eşleşen dersler:{" "}
                  {k.pairs.length
                    ? k.pairs.map((c) => `${c.subject_name} (${c.teacher_name}, en çok ${c.max_hours})`).join(" · ")
                    : "yok — kural uygulanamaz"}
                </p>
              </div>
              <Buton tur="sade" onClick={() => sil.mutate(k.id)} yukleniyor={sil.isPending}
                     title="Kuralı kaldır" className="shrink-0">
                <Trash2 className="h-4 w-4" />
              </Buton>
            </li>
          ))}
        </ul>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <Alan etiket="Birinci şube">
          <Secim value={a} onChange={(e) => setA(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Seçin</option>
            {subeler.map((s) => (
              <option key={s.id} value={s.id} disabled={s.id === b}>{s.name}</option>
            ))}
          </Secim>
        </Alan>
        <Alan etiket="İkinci şube">
          <Secim value={b} onChange={(e) => setB(e.target.value ? Number(e.target.value) : "")}>
            <option value="">Seçin</option>
            {subeler.map((s) => (
              <option key={s.id} value={s.id} disabled={s.id === a}>{s.name}</option>
            ))}
          </Secim>
        </Alan>
        <Alan etiket="Birleştirilebilecek günler">
          <div className="flex flex-wrap gap-2 pt-1">
            {aktifGunler.map((g) => (
              <label key={g.id} className={
                secilenGunler.includes(g.index)
                  ? "cursor-pointer rounded-lg border border-cizgi-guclu bg-yuzey-alt px-2.5 py-1 text-sm text-murekkep"
                  : "cursor-pointer rounded-lg border border-cizgi px-2.5 py-1 text-sm text-murekkep-yumusak hover:bg-yuzey-alt"
              }>
                <input type="checkbox" className="sr-only" checked={secilenGunler.includes(g.index)}
                       onChange={() => gunDegistir(g.index)} />
                {g.name}
              </label>
            ))}
          </div>
        </Alan>
        <Alan
          etiket="Ortak ders saati (tam)"
          ipucu={
            onIzleme.data
              ? onIzleme.data.pairs.length
                ? `En çok ${enFazla} saat: ${onIzleme.data.pairs.map((c) => `${c.subject_name} ${c.max_hours}`).join(", ")}`
                : "Bu iki şubede aynı öğretmenin verdiği ortak ders yok."
              : "İki şubeyi seçince eşleşen dersler burada görünür."
          }
        >
          <Girdi type="number" min={1} max={Math.max(1, enFazla)} value={saat}
                 onChange={(e) => setSaat(Number(e.target.value))} className="w-28" />
        </Alan>
      </div>
      {ekle.error && <div className="mt-3"><Uyari tur="hata">{(ekle.error as Error).message}</Uyari></div>}
      <div className="mt-4">
        <Buton onClick={() => ekle.mutate()} disabled={!gonderilebilir} yukleniyor={ekle.isPending}>
          Kuralı ekle
        </Buton>
      </div>
      <p className="mt-3 text-xs text-murekkep-silik">
        Kural bir sonraki üretimde geçerli olur. Ortak saatler programda “9-A + 9-B” olarak görünür.
        Sonsuz moddaki yerel arama motoru bu kuralı bilmez ve kural varken devre dışı kalır.
      </p>
    </Kart>
  );
}

export default function Kisitlamalar() {
  const qc = useQueryClient();
  const donemler = useQuery({ queryKey: ["donemler"], queryFn: () => get<Donem[]>("/terms") });
  const subeler = useListe<Sube>("subeler", "/sections");
  const binalar = useListe<Bina>("binalar", "/buildings");
  const aktifDonem = (donemler.data ?? []).find((d) => d.is_active);

  // Dönem ayarı PUT tüm alanları yazar; bir kuralı değiştirirken öbürleri
  // olduğu gibi gönderilir.
  const ayar = useMutation({
    mutationFn: (yama: Partial<Pick<Donem, "block_building_switch" | "conflict_basis">>) =>
      put<Donem>(`/terms/${aktifDonem!.id}`, {
        name: aktifDonem!.name,
        starts_on: aktifDonem!.starts_on,
        ends_on: aktifDonem!.ends_on,
        block_building_switch: aktifDonem!.block_building_switch,
        conflict_basis: aktifDonem!.conflict_basis,
        section_order: aktifDonem!.section_order,
        ...yama,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["donemler"] }),
  });

  const binasiz = (subeler.data ?? []).filter((s) => s.building_id === null).length;
  const binaVar = (binalar.data?.length ?? 0) > 0;

  if (donemler.isLoading || !aktifDonem) return <Yukleniyor />;

  return (
    <div className="space-y-5">
      <SayfaBasligi
        baslik="Kısıtlamalar"
        aciklama="Program üretimini ve elle düzenlemeyi bağlayan kurallar. Hepsi bu dönem için geçerlidir."
      />

      {ayar.error && <Uyari tur="hata">{(ayar.error as Error).message}</Uyari>}

      <SubeBirlestirme subeler={(subeler.data ?? []).filter((s) => s.is_active)} />

      <Kart
        baslik="Binalar arası geçiş"
        aciklama="Binalar birbirinden uzaksa öğretmenin gün içinde bina değiştirmesi zordur."
        sag={<Building2 className="h-4 w-4 text-murekkep-silik" />}
      >
        {!binaVar ? (
          <p className="text-sm text-murekkep-silik">
            Bu dönemde bina tanımlı değil; kuralın bir etkisi olmaz.{" "}
            <Link to="/binalar" className="font-medium text-murekkep underline">
              Binalar
            </Link>{" "}
            sayfasından ekleyebilirsiniz.
          </p>
        ) : (
          <>
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                checked={aktifDonem.block_building_switch}
                disabled={ayar.isPending}
                onChange={(e) => ayar.mutate({ block_building_switch: e.target.checked })}
                className="mt-0.5 h-4 w-4 rounded border-cizgi-guclu"
              />
              <span className="text-sm">
                <span className="font-medium text-murekkep">
                  Bir öğretmen bir günde tek binada ders versin
                </span>
                <span className="mt-0.5 block text-murekkep-silik">
                  Açıkken bir binanın dersleri bir güne, öbürününki başka güne toplanır;
                  hangi binanın hangi güne düşeceğine program karar verir. Program başka
                  türlü kurulamıyorsa kural esnetilir ve aşım uyarı olarak listelenir.
                </span>
              </span>
            </label>
            {binasiz > 0 && (
              <div className="mt-3">
                <Uyari>
                  {binasiz} şubenin binası seçilmemiş. Binasız şubeler bu kuralın dışında
                  kalır —{" "}
                  <Link to="/subeler" className="font-medium underline">
                    Şubeler
                  </Link>{" "}
                  sayfasından binalarını seçebilirsiniz.
                </Uyari>
              </div>
            )}
          </>
        )}
      </Kart>

      <Kart
        baslik="Çakışma neye göre ölçülsün?"
        aciklama="Bir şube ya da öğretmen aynı anda iki yerde olamaz. “Aynı an”ın ne demek olduğunu buradan seçersiniz; hem program üretimi hem elle düzenleme bu seçime uyar."
        sag={<AlarmClock className="h-4 w-4 text-murekkep-silik" />}
      >
        <div className="space-y-1.5">
          {OLCUT_SECENEKLERI.map((se) => (
            <label
              key={se.id}
              className={
                aktifDonem.conflict_basis === se.id
                  ? "flex cursor-pointer gap-2.5 rounded-lg border border-cizgi-guclu bg-yuzey-alt px-3 py-2"
                  : "flex cursor-pointer gap-2.5 rounded-lg border border-cizgi px-3 py-2 hover:bg-yuzey-alt"
              }
            >
              <input
                type="radio"
                name="cakisma-olcutu"
                checked={aktifDonem.conflict_basis === se.id}
                disabled={ayar.isPending}
                onChange={() => ayar.mutate({ conflict_basis: se.id as CakismaOlcutu })}
                className="mt-0.5 h-4 w-4 border-cizgi-guclu"
              />
              <span className="text-sm">
                <span className="font-medium text-murekkep">{se.etiket}</span>
                <span className="text-murekkep-silik"> · {se.ozet}</span>
                <span className="mt-0.5 block text-xs leading-relaxed text-murekkep-silik">
                  {se.aciklama}
                </span>
              </span>
            </label>
          ))}
        </div>
        <p className="mt-3 text-xs text-murekkep-silik">
          Saatler üst üste biniyorsa{" "}
          <Link to="/zaman-izgarasi" className="font-medium underline">
            Zaman Izgarası
          </Link>{" "}
          sayfası uyarır.
        </p>
      </Kart>
    </div>
  );
}
