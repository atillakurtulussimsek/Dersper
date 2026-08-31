/** Öğretmen boşluğu tercihleri.
 *
 *  Boşluk, bir öğretmenin bir gündeki ilk ve son dersi arasında kalan boş ders
 *  saatidir. Üçü de meşru bir okul düzenidir; metinler tek yerde dursun diye
 *  burada toplandı (hem oluşturma kutusu hem program ekranı kullanıyor).
 *
 *  Tercih, kuralların üstünde DEĞİLDİR: program başka türlü kurulamıyorsa
 *  çözücü tercihten vazgeçer.
 */
import type { BoslukPolitikasi } from "./types";

export const BOSLUK_SECENEKLERI: {
  id: BoslukPolitikasi;
  etiket: string;
  ozet: string;
  aciklama: string;
}[] = [
  {
    id: "bosluklu",
    etiket: "Boşluklu",
    ozet: "Dersler güne yayılır",
    aciklama:
      "Öğretmenin dersleri arasında boşluk kalması istenir; ders aralarında " +
      "nefes payı olur. Öğretmen okulda daha uzun kalır.",
  },
  {
    id: "ideal",
    etiket: "İdeal",
    ozet: "Boşluğa bakılmaz",
    aciklama:
      "Boşluk bir ölçüt değildir; çözücü yalnızca kurallara uyan bir program " +
      "arar. En hızlı seçenek budur.",
  },
  {
    id: "siki",
    etiket: "Sıkı",
    ozet: "Boşluk en aza iner",
    aciklama:
      "Öğretmenin günü olabildiğince sıkışır; dersler arka arkaya gelir ve " +
      "öğretmen işi bitince okuldan ayrılabilir.",
  },
];

export function boslukEtiketi(p: BoslukPolitikasi): string {
  return BOSLUK_SECENEKLERI.find((s) => s.id === p)?.etiket ?? p;
}
