/** Çoklu seçim: seçilenler etiket olarak durur, gerisi aranabilir listeden eklenir.
 *
 *  Uzun onay kutusu listelerinin yerine: alan küçük kalır, çoğu zaman tek
 *  etiket görünür, gerektiğinde "+ ekle" ile bir iki tane daha seçilir.
 *  Yerli öğelerle yazıldı; dışarıdan paket getirmez.
 */
import { useEffect, useRef, useState } from "react";
import { Plus, X } from "lucide-react";
import clsx from "clsx";

export type CokluSecenek = { id: number; etiket: string; not?: string };

export function CokluSecim({
  secenekler,
  secili,
  degistir,
  ekleEtiketi = "Ekle",
  arama = "Ara…",
  bos = "Seçim yok",
}: {
  secenekler: CokluSecenek[];
  secili: number[];
  degistir: (ids: number[]) => void;
  ekleEtiketi?: string;
  arama?: string;
  bos?: string;
}) {
  const [acik, setAcik] = useState(false);
  const [metin, setMetin] = useState("");
  const kok = useRef<HTMLDivElement>(null);
  const girdi = useRef<HTMLInputElement>(null);

  const harita = new Map(secenekler.map((s) => [s.id, s]));
  const kalanlar = secenekler.filter((s) => !secili.includes(s.id));
  const suzulen = metin.trim()
    ? kalanlar.filter((s) =>
        s.etiket.toLocaleLowerCase("tr").includes(metin.trim().toLocaleLowerCase("tr")),
      )
    : kalanlar;

  useEffect(() => {
    if (!acik) return;
    girdi.current?.focus();
    const dis = (e: PointerEvent) => {
      if (!kok.current?.contains(e.target as Node)) setAcik(false);
    };
    document.addEventListener("pointerdown", dis, true);
    return () => document.removeEventListener("pointerdown", dis, true);
  }, [acik]);

  function ekle(id: number) {
    degistir([...secili, id]);
    setMetin("");
    // Ekleyecek başka bir şey kalmadıysa liste kendiliğinden kapanır.
    if (kalanlar.length <= 1) setAcik(false);
  }

  return (
    <div ref={kok} className="relative">
      <div className="flex min-h-[38px] flex-wrap items-center gap-1.5 rounded-lg border border-cizgi-guclu bg-yuzey px-2 py-1.5">
        {secili.length === 0 && (
          <span className="px-1 text-sm text-murekkep-silik">{bos}</span>
        )}
        {secili.map((id) => {
          const s = harita.get(id);
          if (!s) return null;
          return (
            <span
              key={id}
              className="flex items-center gap-1 rounded-md bg-yuzey-alt py-0.5 pl-2 pr-1 text-sm font-medium text-murekkep ring-1 ring-inset ring-cizgi"
            >
              {s.etiket}
              <button
                type="button"
                onClick={() => degistir(secili.filter((x) => x !== id))}
                aria-label={`${s.etiket} kaldır`}
                className="rounded p-0.5 text-murekkep-silik hover:bg-cizgi hover:text-murekkep"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          );
        })}
        {kalanlar.length > 0 && (
          <button
            type="button"
            onClick={() => setAcik((a) => !a)}
            aria-expanded={acik}
            className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-sm text-murekkep-silik hover:bg-yuzey-alt hover:text-murekkep"
          >
            <Plus className="h-3.5 w-3.5" />
            {ekleEtiketi}
          </button>
        )}
      </div>

      {acik && (
        <div className="absolute left-0 right-0 z-30 mt-1 overflow-hidden rounded-lg border border-cizgi bg-yuzey shadow-lg">
          <input
            ref={girdi}
            value={metin}
            onChange={(e) => setMetin(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setAcik(false);
              if (e.key === "Enter") {
                e.preventDefault();
                if (suzulen[0]) ekle(suzulen[0].id);
              }
            }}
            placeholder={arama}
            className="w-full border-b border-cizgi bg-transparent px-3 py-2 text-sm text-murekkep outline-none placeholder:text-murekkep-silik/70"
          />
          <div className="max-h-48 overflow-y-auto py-1">
            {suzulen.length === 0 ? (
              <p className="px-3 py-2 text-sm text-murekkep-silik">Eşleşen yok.</p>
            ) : (
              suzulen.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => ekle(s.id)}
                  className={clsx(
                    "flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-sm",
                    "text-murekkep hover:bg-yuzey-alt",
                  )}
                >
                  <span className="font-medium">{s.etiket}</span>
                  {s.not && <span className="text-xs text-murekkep-silik">{s.not}</span>}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
