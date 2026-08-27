/** Ders bloğu desenleri. Backend'deki `app/bloklar.py` ile aynı kuralları uygular.
 *
 *  5 saatlik bir ders "2+2+1" ya da "1+1+2+1" olarak dağıtılabilir.
 *  Desen boşsa saatler tek tek dağıtılır.
 */

export const EN_UZUN_BLOK = 8;

export interface DesenSonucu {
  bloklar: number[];
  toplam: number;
  gecerli: boolean;
  /** Geçersizse kullanıcıya gösterilecek sebep. */
  hata: string | null;
}

/** Deseni çözer ve haftalık saate uyup uymadığını söyler. */
export function desenCoz(desen: string, haftalikSaat: number): DesenSonucu {
  const ham = desen.trim();
  if (!ham) {
    return {
      bloklar: Array(Math.max(0, haftalikSaat)).fill(1),
      toplam: haftalikSaat,
      gecerli: true,
      hata: null,
    };
  }

  const bloklar: number[] = [];
  for (const parca of ham.split(/[+,\s]+/).filter(Boolean)) {
    if (!/^\d+$/.test(parca)) {
      return { bloklar: [], toplam: 0, gecerli: false,
        hata: `"${parca}" bir sayı değil. Deseni 2+2+1 gibi yazın.` };
    }
    const sayi = Number(parca);
    if (sayi < 1) {
      return { bloklar: [], toplam: 0, gecerli: false, hata: "Blok uzunluğu en az 1 olmalı." };
    }
    if (sayi > EN_UZUN_BLOK) {
      return { bloklar: [], toplam: 0, gecerli: false,
        hata: `Tek blok en fazla ${EN_UZUN_BLOK} saat olabilir.` };
    }
    bloklar.push(sayi);
  }

  const toplam = bloklar.reduce((t, b) => t + b, 0);
  return {
    bloklar,
    toplam,
    gecerli: toplam === haftalikSaat,
    hata:
      toplam === haftalikSaat
        ? null
        : `Blokların toplamı ${toplam} saat, haftalık ders saati ise ${haftalikSaat}.`,
  };
}

const yaz = (bloklar: number[]) => bloklar.join("+");

/** Haftalık saate uyan birkaç makul desen — arayüzde hızlı seçim için. */
export function desenOnerileri(haftalikSaat: number): string[] {
  if (haftalikSaat < 1) return [];
  if (haftalikSaat === 1) return ["1"];

  const oneriler = [yaz(Array(haftalikSaat).fill(1))];

  const ciftli = Math.floor(haftalikSaat / 2);
  const kalan = haftalikSaat % 2;
  oneriler.push(yaz([...Array(ciftli).fill(2), ...(kalan ? [1] : [])]));

  if (haftalikSaat >= 3) {
    oneriler.push(yaz([2, ...Array(haftalikSaat - 2).fill(1)]));
  }
  if (haftalikSaat >= 4) {
    const ucluler = Math.floor(haftalikSaat / 3);
    const art = haftalikSaat % 3;
    const kuyruk = art === 2 ? [2] : Array(art).fill(1);
    oneriler.push(yaz([...Array(ucluler).fill(3), ...kuyruk]));
  }

  return [...new Set(oneriler)];
}

/** Tabloda gösterim: "1+1+1" gibi tek saatlik desenleri "tek" diye yazar. */
export function desenEtiketi(desen: string, haftalikSaat: number): string {
  const { bloklar } = desenCoz(desen, haftalikSaat);
  return bloklar.every((b) => b === 1) ? "tek saat" : bloklar.join("+");
}
