/** Şube sırası — ekranda tek gelenek.
 *
 *  Sıra sunucudan gelir (`/sections` listesi ve ızgara yanıtındaki
 *  `section_names`): kurum ada göre (doğal: 9-A < 10-A) ya da elle sıra
 *  seçmiştir. Burası yalnızca o sırayı hücrelerden türeyen ad listelerine
 *  uygular; sıra bilinmeyen adlar sona, kendi aralarında doğal sırayla.
 */

/** "10-A" ile "9-A"yı sayı olarak karşılaştırır; harfleri Türkçe kurallarla. */
export function dogalKarsilastir(a: string, b: string): number {
  return a.localeCompare(b, "tr", { numeric: true, sensitivity: "base" });
}

/** Verilen sıraya göre karşılaştırıcı; listede olmayanlar sona. */
export function siraKarsilastirici(sira: readonly string[]): (a: string, b: string) => number {
  const yer = new Map(sira.map((ad, i) => [ad, i]));
  return (a, b) => {
    const ya = yer.get(a) ?? Number.MAX_SAFE_INTEGER;
    const yb = yer.get(b) ?? Number.MAX_SAFE_INTEGER;
    return ya !== yb ? ya - yb : dogalKarsilastir(a, b);
  };
}

export const SIRA_SECENEKLERI: { id: "ad" | "elle"; etiket: string; aciklama: string }[] = [
  {
    id: "ad",
    etiket: "Ada göre",
    aciklama: "Sınıf seviyesi, sonra ad — sayılar sayı olarak sayılır: 9-A, 9-B, 10-A.",
  },
  {
    id: "elle",
    etiket: "Elle",
    aciklama: "Satırları sürükleyip kendi sıranızı kurun; \"Sırayı kaydet\" ile kalıcı olur.",
  },
];
