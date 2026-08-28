/** Ders ve öğretmen renkleri. */

export const PALET = [
  "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
  "#3b82f6", "#8b5cf6", "#ec4899", "#64748b", "#0ea5e9",
] as const;

export const VARSAYILAN_RENK = "#94a3b8";

/** Paletten rastgele bir renk. Kullanılmayanlara öncelik verir; hepsi
 *  kullanılmışsa palet baştan devreye girer. */
export function rastgeleRenk(kullanilanlar: string[] = []): string {
  const dolu = new Set(kullanilanlar.map((r) => r.toLowerCase()));
  const bos = PALET.filter((r) => !dolu.has(r));
  const havuz = bos.length ? bos : PALET;
  return havuz[Math.floor(Math.random() * havuz.length)];
}
