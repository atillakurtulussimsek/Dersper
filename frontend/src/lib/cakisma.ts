/** Çakışma ölçütü ve zaman ızgarasının saat denetimi.
 *
 *  Kurum, iki yerleşimin "aynı anda" sayılması için neye bakılacağını seçer:
 *  ızgaranın satırına mı, gerçek saat aralığına mı. Kural sunucuda
 *  `app/cakisma.py` içinde; buradaki karşılığı yalnızca seçimi anlatmak ve
 *  girilen saatleri denetlemek içindir.
 */
import type { CakismaOlcutu } from "./types";

export const OLCUT_SECENEKLERI: {
  id: CakismaOlcutu;
  etiket: string;
  ozet: string;
  aciklama: string;
}[] = [
  {
    id: "ders_saati",
    etiket: "Ders saati",
    ozet: "ızgaranın satırına göre",
    aciklama:
      "Salı 3. ders yalnızca Salı 3. dersle çakışır; girilen saatlere bakılmaz. Tek ve düzenli bir ızgarası olan okullar için doğru olan budur — satır zaten saatin kendisidir.",
  },
  {
    id: "saat",
    etiket: "Saat aralığı",
    ozet: "gerçek başlangıç ve bitişe göre",
    aciklama:
      "09:00–09:40 ile 09:20–10:00 ayrı satırlar olsa da çakışır. Saatleri üst üste binebilen ızgaralarda gerekir: vardiyalı okullar ya da bölümlere göre değişen ders süreleri. Saati girilmemiş satır yalnızca kendisiyle çakışır.",
  },
];

export function olcutEtiketi(olcut: CakismaOlcutu): string {
  return OLCUT_SECENEKLERI.find((s) => s.id === olcut)?.etiket ?? olcut;
}

/** "09:30" ya da "09:30:00" -> gün başından beri dakika. */
export function dakikaya(saat: string | null | undefined): number | null {
  if (!saat) return null;
  const [s, d] = saat.split(":");
  const sayi = Number(s) * 60 + Number(d);
  return Number.isFinite(sayi) ? sayi : null;
}

export type SaatSorunu = {
  tur: "cakisma" | "sira" | "eksik";
  metin: string;
};

type DenetlenenSaat = {
  name: string;
  start_time: string | null;
  end_time: string | null;
  is_break: boolean;
};

/** Bir günün saatlerindeki tutarsızlıklar.
 *
 *  Üç şeye bakar:
 *    * çakışma — iki ders saatinin aralığı üst üste biniyor,
 *    * sıra — satır sırası ile saat sırası ters,
 *    * eksik — biri girilmiş öbürü boş ya da bitiş başlangıçtan önce.
 *
 *  Teneffüsler çakışma denetiminin dışındadır: onlara ders konmuyor.
 */
export function saatSorunlari(saatler: DenetlenenSaat[]): SaatSorunu[] {
  const sorunlar: SaatSorunu[] = [];
  const araliklar = saatler.map((s) => ({
    ad: s.name || "adsız satır",
    bas: dakikaya(s.start_time),
    bit: dakikaya(s.end_time),
    ders: !s.is_break,
  }));

  for (const a of araliklar) {
    if (a.bas === null && a.bit === null) continue;
    if (a.bas === null || a.bit === null) {
      sorunlar.push({ tur: "eksik", metin: `${a.ad}: saatin bir ucu boş.` });
    } else if (a.bit <= a.bas) {
      sorunlar.push({ tur: "eksik", metin: `${a.ad}: bitiş, başlangıçtan sonra değil.` });
    }
  }

  // Sıra: satır sırası ilerlerken saat geri gitmemeli.
  const sirali = araliklar.filter((a) => a.bas !== null);
  for (let i = 1; i < sirali.length; i++) {
    if (sirali[i].bas! < sirali[i - 1].bas!) {
      sorunlar.push({
        tur: "sira",
        metin: `${sirali[i].ad}, kendinden önceki ${sirali[i - 1].ad} satırından daha erken başlıyor.`,
      });
    }
  }

  const gecerli = araliklar.filter(
    (a) => a.ders && a.bas !== null && a.bit !== null && a.bit > a.bas,
  );
  for (let i = 0; i < gecerli.length; i++) {
    for (let j = i + 1; j < gecerli.length; j++) {
      if (gecerli[i].bas! < gecerli[j].bit! && gecerli[j].bas! < gecerli[i].bit!) {
        sorunlar.push({
          tur: "cakisma",
          metin: `${gecerli[i].ad} ile ${gecerli[j].ad} saatleri üst üste biniyor.`,
        });
      }
    }
  }

  return sorunlar;
}
