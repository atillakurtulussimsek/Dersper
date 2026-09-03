/** Bekleyenler rafı: ızgaraya girmemiş ders blokları.
 *
 *  İki kaynaktan dolar — çözücünün yerleştiremediği saatler ve kullanıcının
 *  ızgaradan aldıkları. Buradan ızgaraya sürüklenir; ızgaradan buraya bırakılan
 *  ders programı terk eder ama silinmez, ders ataması yerinde durur.
 *
 *  Raf boşken de görünür kalır: bir dersi geçici olarak kenara koymak için
 *  hedefin hep orada olması gerekir.
 */
import { useDraggable, useDroppable } from "@dnd-kit/core";
import { Inbox } from "lucide-react";
import clsx from "clsx";

import { Kart } from "./ui";
import { dersZemini } from "../lib/renkler";
import type { BekleyenBlok, Suruklenen } from "../lib/types";
import { dokunmatikMi } from "./BaglamMenusu";

/** Aynı dersin aynı uzunluktaki blokları tek kartta toplanır; birden çoksa
 *  sayısı yazılır. Ayrı ayrı göstermek aynı kimlikte iki sürüklenebilir
 *  öğe demek olurdu. */
function grupla(bloklar: BekleyenBlok[]): { blok: BekleyenBlok; adet: number }[] {
  const gruplar = new Map<string, { blok: BekleyenBlok; adet: number }>();
  for (const b of bloklar) {
    const anahtar = `${b.curriculum_entry_id}:${b.uzunluk}`;
    const var_olan = gruplar.get(anahtar);
    if (var_olan) var_olan.adet += 1;
    else gruplar.set(anahtar, { blok: b, adet: 1 });
  }
  return [...gruplar.values()];
}

function Blok({
  blok,
  adet,
  suruklenenMi,
  menuAc,
}: {
  blok: BekleyenBlok;
  adet: number;
  suruklenenMi: boolean;
  menuAc?: (e: { clientX: number; clientY: number }, blok: BekleyenBlok) => void;
}) {
  const kimlik = `b:${blok.curriculum_entry_id}:${blok.uzunluk}`;
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: kimlik });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onContextMenu={(e) => {
        if (!menuAc) return;
        e.preventDefault();
        menuAc(e, blok);
      }}
      onClick={(e) => {
        if (menuAc && dokunmatikMi()) menuAc(e, blok);
      }}
      title={`${blok.section_name} · ${blok.subject_name} · ${blok.teacher_name} — ${blok.uzunluk} saat. Izgaraya sürükleyin ya da sağ tıklayın.`}
      className={clsx(
        "cursor-grab rounded-md px-2 py-1.5 active:cursor-grabbing",
        (isDragging || suruklenenMi) && "opacity-30",
      )}
      style={dersZemini(blok.subject_color)}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="truncate text-[12px] font-semibold text-murekkep">
          {blok.subject_name}
        </span>
        <span className="sayisal shrink-0 font-mono text-[10px] text-murekkep-yumusak">
          {adet > 1 ? `${adet} × ` : ""}{blok.uzunluk} saat
        </span>
      </div>
      <div className="truncate text-[10.5px] text-murekkep-yumusak">
        {blok.section_name} · {blok.teacher_name}
      </div>
    </div>
  );
}

export default function BekleyenDersler({
  bloklar,
  suruklenen,
  menuAc,
}: {
  bloklar: BekleyenBlok[];
  suruklenen: Suruklenen | null;
  menuAc?: (e: { clientX: number; clientY: number }, blok: BekleyenBlok) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: "raf" });
  const izgaradanGeliyor = suruklenen?.tur === "hucre";
  // Bekleyen yokken ve sürükleme de yokken raf işlevsizdir: kesikli kutu ve
  // açıklama yer kaplamasın, tek satır yeter. Bırakma hedefi yine de bağlıdır,
  // sürükleme başlar başlamaz kutu geri açılır.
  const sakin = bloklar.length === 0 && !izgaradanGeliyor;

  return (
    <Kart
      baslik="Bekleyen dersler"
      aciklama={
        sakin
          ? undefined
          : "Izgaraya girmemiş saatler. Buradan ızgaraya sürükleyin; ızgaradan buraya bırakılan ders programdan çıkar."
      }
      sag={<Inbox className="h-4 w-4 text-murekkep-silik" />}
    >
      <div
        ref={setNodeRef}
        className={clsx(
          "rounded-lg transition-colors",
          !sakin && "min-h-[76px] border border-dashed p-2",
          isOver && izgaradanGeliyor
            ? "border-cizgi-guclu bg-uyari-zemin"
            : izgaradanGeliyor
              ? "border-cizgi-guclu bg-yuzey-alt"
              : "border-cizgi",
        )}
      >
        {bloklar.length === 0 ? (
          <p
            className={clsx(
              "text-sm text-murekkep-silik",
              sakin ? "" : "px-1 py-4 text-center",
            )}
          >
            {izgaradanGeliyor
              ? "Dersi buraya bırakın — ızgaradan çıkar, sonra geri koyabilirsiniz."
              : "Bekleyen ders yok; bütün saatler yerleşmiş."}
          </p>
        ) : (
          <div className="grid gap-1.5 sm:grid-cols-2 lg:grid-cols-3">
            {grupla(bloklar).map(({ blok, adet }) => (
              <Blok
                key={`${blok.curriculum_entry_id}:${blok.uzunluk}`}
                blok={blok}
                adet={adet}
                menuAc={menuAc}
                suruklenenMi={
                  suruklenen?.tur === "bekleyen" &&
                  suruklenen.entryId === blok.curriculum_entry_id &&
                  suruklenen.uzunluk === blok.uzunluk
                }
              />
            ))}
          </div>
        )}
      </div>
    </Kart>
  );
}
