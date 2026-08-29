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

/** Program hücresinin ders rengi kompozisyonu.
 *
 *  Renk kullanıcıya aittir ve her iki temada okunur kalmalıdır. Sabit bir
 *  saydamlık işe yaramaz: açık temada yeterli olan %14, koyu zeminde kaybolur.
 *  Zemin payı temaya göre belirteçten gelir; rengin kendisi solda katı bir
 *  barda durur, orada her koşulda görünür. Çarşafta hücre dar olduğu için bar
 *  inceltilir.
 */
export function dersZemini(renk: string, bar = 3): React.CSSProperties {
  return {
    background: `color-mix(in srgb, ${renk} calc(var(--ders-zemin-alfa) * 100%), transparent)`,
    boxShadow: `inset ${bar}px 0 0 ${renk}`,
  };
}
