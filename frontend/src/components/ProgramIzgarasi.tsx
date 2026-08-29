/** Haftalık program tablosu. Şube ya da öğretmen bakışıyla çizilir.
 *
 *  Sütunlar eşit genişlikte sabitlenir (`table-fixed`) ve hücre metinleri
 *  kırpılır; böylece gün sayısı ne olursa olsun tablo ekrana sığar, yatay
 *  kaydırma yalnızca gerçekten gerektiğinde devreye girer.
 *
 *  `tasi` verilirse hücreler sürüklenebilir.
 */
import {
  DndContext, DragOverlay, PointerSensor, useDraggable, useDroppable, useSensor,
  useSensors, type DragEndEvent, type DragStartEvent,
} from "@dnd-kit/core";
import { useState } from "react";
import { Lock } from "lucide-react";
import clsx from "clsx";

import type { DersSaati, Gun, Hucre } from "../lib/types";

export type Bakis = "sube" | "ogretmen";

/** Hücrenin alt satırı: şube bakışında öğretmen, öğretmen bakışında şube. */
function altSatir(hucre: Hucre, bakis: Bakis): string {
  return bakis === "sube" ? hucre.teacher_name : hucre.section_name;
}

/** Ders renginin hücre kompozisyonu.
 *
 *  Renk kullanıcıya aittir ve her iki temada okunur kalmalıdır. Sabit bir
 *  saydamlık işe yaramaz: açık temada yeterli olan %12, koyu zeminde kaybolur.
 *  Zemin payı temaya göre belirteçten gelir; rengin kendisi solda katı bir
 *  barda durur, orada her koşulda görünür.
 */
function dersZemini(renk: string): React.CSSProperties {
  return {
    background: `color-mix(in srgb, ${renk} calc(var(--ders-zemin-alfa) * 100%), transparent)`,
    boxShadow: `inset 3px 0 0 ${renk}`,
  };
}

function HucreIcerigi({ hucre, bakis }: { hucre: Hucre; bakis: Bakis }) {
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
  kilitle,
}: {
  hucre: Hucre;
  bakis: Bakis;
  kilitle?: (id: number) => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: hucre.assignment_id,
    disabled: hucre.is_locked,
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onDoubleClick={() => kilitle?.(hucre.assignment_id)}
      title={
        hucre.is_locked
          ? `${hucre.subject_name} · ${altSatir(hucre, bakis)} — kilitli, çift tıklayarak açın`
          : `${hucre.subject_name} · ${altSatir(hucre, bakis)} — sürükleyerek taşıyın, çift tıklayarak kilitleyin`
      }
      className={clsx(
        "h-full w-full transition-opacity",
        hucre.is_locked
          ? "cursor-default rounded-md ring-1 ring-inset ring-cizgi-guclu"
          : "cursor-grab active:cursor-grabbing",
        isDragging && "opacity-30",
      )}
    >
      <HucreIcerigi hucre={hucre} bakis={bakis} />
    </div>
  );
}

function Hedef({
  periodId,
  bos,
  children,
}: {
  periodId: number;
  bos: boolean;
  children: React.ReactNode;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: periodId });
  return (
    <td
      ref={setNodeRef}
      className={clsx(
        "h-14 border border-cizgi p-0.5 align-middle transition-colors",
        bos && "bg-yuzey-alt/60",
        isOver && "bg-murekkep/10 ring-2 ring-inset ring-cizgi-guclu",
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
  tasi,
  kilitle,
}: {
  gunler: Gun[];
  hucreler: Hucre[];
  bakis: Bakis;
  /** Gösterilecek şube ya da öğretmen adı */
  anahtar: string;
  tasi?: (assignmentId: number, periodId: number) => void;
  kilitle?: (assignmentId: number) => void;
}) {
  const [suruklenen, setSuruklenen] = useState<Hucre | null>(null);
  const sensorler = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

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

  function bittiginde(e: DragEndEvent) {
    setSuruklenen(null);
    if (!tasi || !e.over) return;
    tasi(Number(e.active.id), Number(e.over.id));
  }

  function basladiginda(e: DragStartEvent) {
    setSuruklenen(benimkiler.find((h) => h.assignment_id === Number(e.active.id)) ?? null);
  }

  const tablo = (
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
                      teneffüs
                    </td>
                  );
                }
                const h = yerlesim.get(`${g.index}:${i}`);
                const icerik = h ? (
                  <Surukle hucre={h} bakis={bakis} kilitle={kilitle} />
                ) : null;
                return tasi ? (
                  <Hedef key={g.id} periodId={p.id} bos={!h}>
                    {icerik}
                  </Hedef>
                ) : (
                  <td
                    key={g.id}
                    className={clsx(
                      "h-14 border border-cizgi p-0.5",
                      !h && "bg-yuzey-alt/60",
                    )}
                  >
                    {icerik}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );

  if (!tasi) return <div className="overflow-x-auto">{tablo}</div>;

  return (
    <DndContext
      sensors={sensorler}
      onDragStart={basladiginda}
      onDragEnd={bittiginde}
      onDragCancel={() => setSuruklenen(null)}
    >
      <div className="overflow-x-auto">{tablo}</div>
      <DragOverlay dropAnimation={null}>
        {suruklenen && (
          <div className="h-14 w-32 rounded-md shadow-lg">
            <HucreIcerigi hucre={suruklenen} bakis={bakis} />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
