/** Haftalık program tablosu. Şube ya da öğretmen bakışıyla çizilir.
 *
 *  Sütunlar eşit genişlikte sabitlenir (`table-fixed`) ve hücre metinleri
 *  kırpılır; böylece gün sayısı ne olursa olsun tablo ekrana sığar.
 *
 *  Elle düzenleme burada yapılır ama sürükleme bağlamı (DndContext) dışarıda,
 *  `ProgramDetay`ta durur: bekleyenler rafı da aynı bağlamı paylaşmalı ki ders
 *  ızgaradan rafa, raftan ızgaraya sürüklenebilsin.
 *
 *  Sürüklenen şey blok bütünüdür. Sürükleme başlayınca sunucudan gelen
 *  değerlendirmeye göre konabilecek saatler belirginleşir, konamayacaklar
 *  soluklaşır ve nedeni hücrenin ipucunda yazar.
 */
import { useDraggable, useDroppable } from "@dnd-kit/core";
import { Lock } from "lucide-react";
import clsx from "clsx";

import { bloklariCikar } from "../lib/hucreler";
import { dersZemini } from "../lib/renkler";
import type { DersSaati, Gun, Hedef, Hucre, Suruklenen } from "../lib/types";

export type Bakis = "sube" | "ogretmen";

/** Hücrenin alt satırı: şube bakışında öğretmen, öğretmen bakışında şube. */
function altSatir(hucre: Hucre, bakis: Bakis): string {
  return bakis === "sube" ? hucre.teacher_name : hucre.section_name;
}

export function HucreIcerigi({ hucre, bakis }: { hucre: Hucre; bakis: Bakis }) {
  return (
    <div
      className="flex h-full w-full flex-col justify-center overflow-hidden rounded-md px-1.5 py-1 text-center"
      style={dersZemini(hucre.subject_color)}
    >
      <span className="flex items-center justify-center gap-1 truncate text-[12px] font-semibold leading-tight text-murekkep">
        {hucre.is_locked && <Lock className="h-2.5 w-2.5 shrink-0 text-murekkep-silik" />}
        <span className="truncate">{hucre.subject_name}</span>
      </span>
      {/* Alt satır (öğretmen ya da şube) `murekkep-silik` değil `yumusak`:
        * hücre zemini kullanıcının ders rengiyle boyandığı için silik ton koyu
        * temada 3.2:1'e kadar düşüyordu. Yumuşak ton en kötü durumda 5.7:1. */}
      <span className="truncate text-[10.5px] leading-tight text-murekkep-yumusak">
        {altSatir(hucre, bakis)}
      </span>
    </div>
  );
}

function Surukle({
  hucre,
  bakis,
  blokBoyu,
  kilitle,
  suruklenenMi,
}: {
  hucre: Hucre;
  bakis: Bakis;
  blokBoyu: number;
  kilitle?: (id: number) => void;
  suruklenenMi: boolean;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `h:${hucre.assignment_id}`,
    disabled: hucre.is_locked,
  });

  const kim = altSatir(hucre, bakis);
  const blokNotu = blokBoyu > 1 ? ` · ${blokBoyu} saatlik blok birlikte taşınır` : "";

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onDoubleClick={() => kilitle?.(hucre.assignment_id)}
      title={
        hucre.is_locked
          ? `${hucre.subject_name} · ${kim} — kilitli, çift tıklayarak açın`
          : `${hucre.subject_name} · ${kim}${blokNotu} — sürükleyerek taşıyın, çift tıklayarak kilitleyin`
      }
      className={clsx(
        "h-full w-full transition-opacity",
        hucre.is_locked
          ? "cursor-default rounded-md ring-1 ring-inset ring-cizgi-guclu"
          : "cursor-grab active:cursor-grabbing",
        (isDragging || suruklenenMi) && "opacity-30",
      )}
    >
      <HucreIcerigi hucre={hucre} bakis={bakis} />
    </div>
  );
}

function Hedefli({
  periodId,
  bos,
  degerlendirme,
  suruklemeVar,
  children,
}: {
  periodId: number;
  bos: boolean;
  degerlendirme?: Hedef;
  suruklemeVar: boolean;
  children: React.ReactNode;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: `s:${periodId}` });
  // Sürükleme sürerken: uygun hedefler belirgin, uygunsuzlar soluk.
  const isaretle = suruklemeVar && degerlendirme !== undefined;
  const uygun = degerlendirme?.uygun ?? true;

  return (
    <td
      ref={setNodeRef}
      title={isaretle && !uygun ? (degerlendirme?.neden ?? undefined) : undefined}
      className={clsx(
        "h-14 border border-cizgi p-0.5 align-middle transition-colors",
        bos && "bg-yuzey-alt/60",
        isaretle && uygun && "bg-basari-zemin",
        isaretle && !uygun && "opacity-40",
        isOver && uygun && "bg-murekkep/10 ring-2 ring-inset ring-cizgi-guclu",
        isOver && !uygun && "ring-2 ring-inset ring-hata",
      )}
    >
      {children}
    </td>
  );
}

export default function ProgramIzgarasi({
  gunler,
  hucreler,
  bakis,
  anahtar,
  duzenlenebilir,
  hedefler,
  suruklenen,
  kilitle,
}: {
  gunler: Gun[];
  hucreler: Hucre[];
  bakis: Bakis;
  /** Gösterilecek şube ya da öğretmen adı */
  anahtar: string;
  /** Sürükle-bırak açık mı (yayın görünümünde kapalı). */
  duzenlenebilir?: boolean;
  /** period_id -> sürüklenen ders o saate konabilir mi. */
  hedefler?: Map<number, Hedef>;
  suruklenen?: Suruklenen | null;
  kilitle?: (assignmentId: number) => void;
}) {
  const aktifGunler = gunler.filter((g) => g.is_active);
  const enFazla = Math.max(
    0,
    ...aktifGunler.map((g) => Math.max(0, ...g.periods.map((p) => p.index + 1))),
  );

  const benimkiler = hucreler.filter((h) =>
    bakis === "sube" ? h.section_name === anahtar : h.teacher_name === anahtar,
  );
  const yerlesim = new Map<string, Hucre>();
  for (const h of benimkiler) yerlesim.set(`${h.day_index}:${h.period_index}`, h);

  // Bloklar tüm hücrelerden çıkarılır: seçili kayıt süzülmüş olsa da bir
  // bloğun tamamı aynı kayda ait olduğu için sonuç değişmez.
  const bloklar = bloklariCikar(hucreler);
  const suruklenenAtamalar = new Set(
    suruklenen?.tur === "hucre" ? suruklenen.hucreler.map((h) => h.assignment_id) : [],
  );

  /** Satır başlığı: ders sırası ve varsa zil saatleri. */
  function saatAraligi(index: number): string | null {
    for (const g of aktifGunler) {
      const p = g.periods.find((x) => x.index === index);
      if (p?.start_time && p?.end_time) {
        return `${p.start_time.slice(0, 5)}–${p.end_time.slice(0, 5)}`;
      }
    }
    return null;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full table-fixed border-collapse">
        <colgroup>
          <col className="w-[86px]" />
          {aktifGunler.map((g) => (
            <col key={g.id} />
          ))}
        </colgroup>
        <thead>
          <tr>
            <th className="border border-cizgi bg-yuzey-alt px-2 py-2 text-[11px] font-semibold text-murekkep-silik">
              Saat
            </th>
            {aktifGunler.map((g) => (
              <th
                key={g.id}
                className="border border-cizgi bg-yuzey-alt px-2 py-2 text-[12px] font-semibold text-murekkep-yumusak"
              >
                {g.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: enFazla }, (_, i) => {
            const aralik = saatAraligi(i);
            return (
              <tr key={i}>
                <th className="border border-cizgi bg-yuzey-alt px-1 py-1 text-center align-middle">
                  <span className="sayisal block text-[12px] font-semibold text-murekkep-yumusak">
                    {i + 1}.
                  </span>
                  {aralik && (
                    <span className="sayisal block font-mono text-[9px] leading-tight text-murekkep-silik">
                      {aralik}
                    </span>
                  )}
                </th>
                {aktifGunler.map((g) => {
                  const p: DersSaati | undefined = g.periods.find((x) => x.index === i);
                  if (!p) {
                    return (
                      <td
                        key={g.id}
                        className="h-14 border border-cizgi bg-[repeating-linear-gradient(45deg,#f8fafc,#f8fafc_6px,#f1f5f9_6px,#f1f5f9_12px)]"
                      />
                    );
                  }
                  if (p.is_break) {
                    return (
                      <td
                        key={g.id}
                        className="h-14 border border-cizgi bg-uyari-zemin text-center text-[10px] font-medium text-uyari"
                      >
                        {p.is_lunch ? "öğle arası" : "teneffüs"}
                      </td>
                    );
                  }
                  const h = yerlesim.get(`${g.index}:${i}`);

                  // Yayın görünümünde sürükleme bağlamı yok; `useDraggable`
                  // çağıran bileşen oraya hiç girmemeli.
                  if (!duzenlenebilir) {
                    return (
                      <td
                        key={g.id}
                        className={clsx(
                          "h-14 border border-cizgi p-0.5",
                          !h && "bg-yuzey-alt/60",
                        )}
                      >
                        {h && <HucreIcerigi hucre={h} bakis={bakis} />}
                      </td>
                    );
                  }
                  return (
                    <Hedefli
                      key={g.id}
                      periodId={p.id}
                      bos={!h}
                      degerlendirme={hedefler?.get(p.id)}
                      suruklemeVar={Boolean(suruklenen)}
                    >
                      {h && (
                        <Surukle
                          hucre={h}
                          bakis={bakis}
                          blokBoyu={bloklar.get(h.assignment_id)?.length ?? 1}
                          kilitle={kilitle}
                          suruklenenMi={suruklenenAtamalar.has(h.assignment_id)}
                        />
                      )}
                    </Hedefli>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
