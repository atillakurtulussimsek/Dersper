/** Haftalık program tablosu. Şube ya da öğretmen bakışıyla çizilir.
 *  `tasi` verilirse hücreler sürüklenebilir. */
import {
  DndContext, PointerSensor, useDraggable, useDroppable, useSensor, useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { Lock } from "lucide-react";
import clsx from "clsx";

import type { Gun, Hucre } from "../lib/types";

export type Bakis = "sube" | "ogretmen";

function Surukle({ hucre, bakis, kilitle }: {
  hucre: Hucre;
  bakis: Bakis;
  kilitle?: (id: number) => void;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: hucre.assignment_id,
    disabled: hucre.is_locked,
  });
  const alt = bakis === "sube" ? hucre.teacher_name : hucre.section_name;

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onDoubleClick={() => kilitle?.(hucre.assignment_id)}
      title={
        hucre.is_locked
          ? "Kilitli — çift tıklayarak kilidi açın"
          : "Sürükleyerek taşıyın · çift tıklayarak kilitleyin"
      }
      className={clsx(
        "flex h-full w-full flex-col justify-center rounded-md px-1.5 py-1 text-center leading-tight",
        hucre.is_locked ? "cursor-default" : "cursor-grab active:cursor-grabbing",
        isDragging && "opacity-40",
      )}
      style={{ background: `${hucre.subject_color}26`, borderLeft: `3px solid ${hucre.subject_color}` }}
    >
      <span className="flex items-center justify-center gap-1 text-[11px] font-semibold text-slate-800">
        {hucre.is_locked && <Lock className="h-3 w-3 shrink-0 text-slate-500" />}
        <span className="truncate">{hucre.subject_name}</span>
      </span>
      <span className="truncate text-[10px] text-slate-500">{alt}</span>
    </div>
  );
}

function Hedef({ periodId, cocuk }: { periodId: number; cocuk: React.ReactNode }) {
  const { setNodeRef, isOver } = useDroppable({ id: periodId });
  return (
    <td
      ref={setNodeRef}
      className={clsx(
        "h-14 border border-slate-200 p-0.5 align-middle transition-colors",
        isOver && "bg-slate-200",
      )}
    >
      {cocuk}
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

  function bittiginde(e: DragEndEvent) {
    if (!tasi || !e.over) return;
    tasi(Number(e.active.id), Number(e.over.id));
  }

  const tablo = (
    <table className="w-full border-collapse">
      <thead>
        <tr>
          <th className="w-20 px-2 py-1.5 text-xs font-medium text-slate-500" />
          {aktifGunler.map((g) => (
            <th
              key={g.id}
              className="border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs font-semibold text-slate-700"
            >
              {g.name}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: enFazla }, (_, i) => (
          <tr key={i}>
            <th className="border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600">
              {i + 1}. ders
            </th>
            {aktifGunler.map((g) => {
              const p = g.periods.find((x) => x.index === i);
              if (!p)
                return <td key={g.id} className="h-14 border border-slate-100 bg-slate-50/60" />;
              if (p.is_break)
                return (
                  <td
                    key={g.id}
                    className="h-14 border border-slate-200 bg-slate-100 text-center text-[10px] text-slate-400"
                  >
                    teneffüs
                  </td>
                );
              const h = yerlesim.get(`${g.index}:${i}`);
              const icerik = h ? <Surukle hucre={h} bakis={bakis} kilitle={kilitle} /> : null;
              return tasi ? (
                <Hedef key={g.id} periodId={p.id} cocuk={icerik} />
              ) : (
                <td key={g.id} className="h-14 border border-slate-200 p-0.5">
                  {icerik}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );

  if (!tasi) return <div className="overflow-x-auto">{tablo}</div>;

  return (
    <DndContext sensors={sensorler} onDragEnd={bittiginde}>
      <div className="overflow-x-auto">{tablo}</div>
    </DndContext>
  );
}
