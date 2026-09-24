/** Sekmeler arası tazeleme.
 *
 *  Zaman ızgarası bir sekmede kaydedilince öbür sekmedeki program sayfası da
 *  anında değişmeli; odak tazelemesi (refetchOnWindowFocus) sekmeye dönene
 *  kadar bekler ve gizli pencerede hiç çalışmaz. `storage` olayı ise aynı
 *  kökendeki BÜTÜN öbür sekmelerde, gizli olsalar da, anında tetiklenir.
 */
import type { QueryClient } from "@tanstack/react-query";

const ANAHTAR = "dersper_senkron";

/** Bu sekmede yapılan değişikliği öbür sekmelere duyurur. */
export function degisiklikDuyur(sorgular: string[]): void {
  try {
    localStorage.setItem(ANAHTAR, JSON.stringify({ sorgular, zaman: Date.now() }));
  } catch {
    // Depolama kapalıysa (gizli pencere) sessizce vazgeç; odak tazelemesi kalır.
  }
}

/** Öbür sekmelerden gelen duyuruları dinler, ilgili sorguları eskitir. */
export function senkronBasla(qc: QueryClient): void {
  window.addEventListener("storage", (e) => {
    if (e.key !== ANAHTAR || !e.newValue) return;
    try {
      const { sorgular } = JSON.parse(e.newValue) as { sorgular: string[] };
      for (const s of sorgular) qc.invalidateQueries({ queryKey: [s] });
    } catch {
      // bozuk kayıt: yok say
    }
  });
}
