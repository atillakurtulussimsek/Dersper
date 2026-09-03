/** Ders seçilince öğretmen listesi: önce o dersin branş öğretmenleri.
 *
 *  "Branş öğretmeni" iki yoldan anlaşılır: öğretmenin branşı dersin adıyla
 *  örtüşüyor (Türkçe küçük harfle, biri öbürünü içeriyor) ya da öğretmen bu
 *  dersi başka bir şubede zaten okutuyor. İkisi de yoksa "diğer"e düşer.
 *  Her grup kendi içinde ada göre.
 */
import type { MufredatSatiri, Ogretmen } from "./types";

function kucult(s: string): string {
  return s.trim().toLocaleLowerCase("tr");
}

function bransUyar(brans: string | null, dersAdi: string): boolean {
  if (!brans) return false;
  const b = kucult(brans);
  const d = kucult(dersAdi);
  return b.length > 0 && (b === d || b.includes(d) || d.includes(b));
}

export function ogretmenleriGrupla(
  ogretmenler: Ogretmen[],
  dersId: number | null,
  dersAdi: string | null,
  mufredat: MufredatSatiri[],
): { brans: Ogretmen[]; diger: Ogretmen[] } {
  const okutanlar = new Set(
    mufredat.filter((m) => m.subject_id === dersId).map((m) => m.teacher_id),
  );
  const ada = (a: Ogretmen, b: Ogretmen) => a.full_name.localeCompare(b.full_name, "tr");
  const brans: Ogretmen[] = [];
  const diger: Ogretmen[] = [];
  for (const o of ogretmenler) {
    const uyar = dersAdi !== null && (okutanlar.has(o.id) || bransUyar(o.branch, dersAdi));
    (uyar ? brans : diger).push(o);
  }
  return { brans: brans.sort(ada), diger: diger.sort(ada) };
}
