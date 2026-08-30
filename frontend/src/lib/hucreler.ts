/** Program hücrelerinin blok mantığı.
 *
 *  Blok, aynı ders atamasının bir gün içinde arka arkaya gelen saatleridir.
 *  İşlem birimi bloktur: "2+2" istenmişken bir saati ayrı çekmek, çözücünün
 *  asla üretmeyeceği bir programı elle oluşturmak olurdu. Sunucu da aynı
 *  kuralla çalışır (bkz. `app/duzenle.py`).
 */
import type { Hucre } from "./types";

/** İki hücre aynı ders atamasının parçası mı?
 *  (şube, öğretmen, ders) üçlüsü bir müfredat satırını tekil belirler. */
export function ayniDers(a: Hucre, b: Hucre): boolean {
  return (
    a.section_id === b.section_id &&
    a.teacher_id === b.teacher_id &&
    a.subject_name === b.subject_name
  );
}

/** assignment_id -> o hücrenin içinde bulunduğu bloğun tüm hücreleri.
 *  Hangi hücreye dokunulursa dokunulsun blok bulunur. */
export function bloklariCikar(hucreler: Hucre[]): Map<number, Hucre[]> {
  const gunluk = new Map<string, Hucre[]>();
  for (const h of hucreler) {
    const anahtar = `${h.section_id}:${h.teacher_id}:${h.subject_name}:${h.day_index}`;
    const liste = gunluk.get(anahtar) ?? [];
    liste.push(h);
    gunluk.set(anahtar, liste);
  }

  const sonuc = new Map<number, Hucre[]>();
  for (const liste of gunluk.values()) {
    liste.sort((a, b) => a.period_index - b.period_index);
    let blok: Hucre[] = [];
    for (const h of liste) {
      if (blok.length && h.period_index - blok[blok.length - 1].period_index !== 1) {
        for (const uye of blok) sonuc.set(uye.assignment_id, blok);
        blok = [];
      }
      blok.push(h);
    }
    for (const uye of blok) sonuc.set(uye.assignment_id, blok);
  }
  return sonuc;
}
