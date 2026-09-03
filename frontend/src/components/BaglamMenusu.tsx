/** Sağ tık (dokunmatikte dokunma) menüsü ve hedef saat seçici.
 *
 *  Sürükle-bırakın alternatifi: küçük ekranda bir kartı alıp aşağıdaki rafa ya
 *  da başka bir güne sürüklemek zordur. Menü aynı işleri tıklamayla yaptırır;
 *  "Taşı…" hedef saatleri listeden seçtirir. Kurallar yine sunucuda — seçici,
 *  sürüklemede kullanılan aynı hedef değerlendirmesini gösterir.
 */
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import clsx from "clsx";

import { Kutu } from "./ui";
import type { Gun, Hedef } from "../lib/types";

export type MenuOgesi = {
  etiket: string;
  simge?: React.ReactNode;
  tehlike?: boolean;
  devre?: boolean;
  sec: () => void;
};

export function BaglamMenusu({
  x,
  y,
  baslik,
  ogeler,
  kapat,
}: {
  x: number;
  y: number;
  baslik?: string;
  ogeler: MenuOgesi[];
  kapat: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [konum, setKonum] = useState({ x, y });

  // Menü ekran dışına taşmasın: boyutu ölçülüp gerekirse sola/yukarı çekilir.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    setKonum({
      x: Math.min(x, window.innerWidth - width - 8),
      y: Math.min(y, window.innerHeight - height - 8),
    });
  }, [x, y]);

  useEffect(() => {
    const dis = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) kapat();
    };
    const tus = (e: KeyboardEvent) => e.key === "Escape" && kapat();
    document.addEventListener("pointerdown", dis, true);
    document.addEventListener("keydown", tus);
    window.addEventListener("scroll", kapat, true);
    return () => {
      document.removeEventListener("pointerdown", dis, true);
      document.removeEventListener("keydown", tus);
      window.removeEventListener("scroll", kapat, true);
    };
  }, [kapat]);

  return (
    <div
      ref={ref}
      role="menu"
      style={{ left: konum.x, top: konum.y }}
      className="fixed z-50 min-w-44 rounded-lg border border-cizgi bg-yuzey py-1 shadow-xl shadow-murekkep/10"
    >
      {baslik && (
        <p className="truncate border-b border-cizgi px-3 py-1.5 text-xs text-murekkep-silik">
          {baslik}
        </p>
      )}
      {ogeler.map((o) => (
        <button
          key={o.etiket}
          role="menuitem"
          disabled={o.devre}
          onClick={() => {
            kapat();
            o.sec();
          }}
          className={clsx(
            "flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm",
            "disabled:cursor-not-allowed disabled:opacity-40",
            o.tehlike
              ? "text-hata hover:bg-hata-zemin"
              : "text-murekkep hover:bg-yuzey-alt",
          )}
        >
          {o.simge}
          {o.etiket}
        </button>
      ))}
    </div>
  );
}

/** Taşınacak/yerleştirilecek ders için hedef saat listesi.
 *
 *  Sürüklemedeki yeşil/soluk işaretlemenin liste hâli: uygun saatler
 *  tıklanır, uygunsuzlar nedeniyle birlikte soluk durur. Blok birden fazla
 *  saatse seçilen saat bloğun BAŞLANGICIdır — sürüklemeyle aynı.
 */
export function HedefSecici({
  acik,
  kapat,
  baslik,
  gunler,
  hedefler,
  yukleniyor,
  uzunluk,
  sec,
}: {
  acik: boolean;
  kapat: () => void;
  baslik: string;
  gunler: Gun[];
  hedefler: Map<number, Hedef>;
  yukleniyor: boolean;
  uzunluk: number;
  sec: (periodId: number) => void;
}) {
  const aktif = gunler.filter((g) => g.is_active);
  return (
    <Kutu acik={acik} kapat={kapat} baslik={baslik}>
      <p className="mb-3 text-xs text-murekkep-silik">
        {uzunluk > 1
          ? `${uzunluk} saatlik blok: seçtiğiniz saat bloğun başlangıcı olur.`
          : "Dersin konacağı saati seçin."}{" "}
        Soluk saatler kurala takılıyor; üzerine gelince nedeni yazar.
      </p>
      {yukleniyor ? (
        <p className="py-6 text-center text-sm text-murekkep-silik">
          Uygun saatler hesaplanıyor…
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {aktif.map((g) => (
            <div key={g.id}>
              <p className="mb-1 text-2xs font-semibold uppercase tracking-[0.08em] text-murekkep-silik">
                {g.name}
              </p>
              <div className="space-y-0.5">
                {g.periods
                  .filter((p) => !p.is_break)
                  .map((p) => {
                    const h = hedefler.get(p.id);
                    const uygun = h?.uygun ?? false;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        disabled={!uygun}
                        title={!uygun ? (h?.neden ?? "Bu saate konamaz") : undefined}
                        onClick={() => {
                          sec(p.id);
                          kapat();
                        }}
                        className={clsx(
                          "sayisal flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm",
                          uygun
                            ? "bg-basari-zemin text-murekkep hover:ring-1 hover:ring-inset hover:ring-basari"
                            : "cursor-not-allowed text-murekkep-silik opacity-50",
                        )}
                      >
                        <span>{p.name}</span>
                        {p.start_time && (
                          <span className="font-mono text-[10px] text-murekkep-silik">
                            {p.start_time.slice(0, 5)}
                          </span>
                        )}
                      </button>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>
      )}
    </Kutu>
  );
}

/** Dokunmatik cihazda sağ tık yok: tek dokunuş menüyü açar. */
export function dokunmatikMi(): boolean {
  return window.matchMedia?.("(pointer: coarse)").matches ?? false;
}
