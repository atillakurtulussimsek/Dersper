/** Zaman ızgarası satırlarının adlandırılması.
 *
 *  Satırlar sürüklenerek yeniden sıralanabildiği için adlar sıraya göre
 *  yeniden yazılmalı — yoksa araya teneffüs eklendiğinde dersler "1, 3, 4"
 *  diye gider. Ama yalnızca OTOMATİK adlar yeniden yazılır: kullanıcı bir
 *  satıra "Etüt" ya da "Kahvaltı" yazdıysa ona dokunulmaz.
 */

/** Adlandırma için gereken en az alan. */
export interface AdlanabilirSaat {
  name: string;
  is_break: boolean;
  is_lunch: boolean;
}

const OTOMATIK_DERS = /^\d+\. ders$/;
const OTOMATIK_ARA = /^(Teneffüs|Öğle arası)$/;

/** Ad, uygulamanın kendi ürettiği kalıplardan biri mi? */
export function otomatikAdMi(ad: string): boolean {
  return OTOMATIK_DERS.test(ad) || OTOMATIK_ARA.test(ad);
}

/** Bir günün satırlarındaki otomatik adları sıraya göre yeniden numaralar.
 *  Ders numarası yalnızca ders saatlerini sayar; teneffüsler atlanır. */
export function adlariTazele<T extends AdlanabilirSaat>(saatler: T[]): T[] {
  let dersSirasi = 0;
  return saatler.map((p) => {
    if (!p.is_break) dersSirasi += 1;
    if (!otomatikAdMi(p.name)) return p;
    const ad = p.is_lunch ? "Öğle arası" : p.is_break ? "Teneffüs" : `${dersSirasi}. ders`;
    return ad === p.name ? p : { ...p, name: ad };
  });
}
