/** Ders adından kısa kod türetir.
 *
 *  Önce yaygın MEB kısaltmalarına bakar (Türkçe → TRK, Matematik → MAT).
 *  Tabloda yoksa kurallara düşer: çok kelimeli adlarda baş harfler
 *  (Din Kültürü ve Ahlak Bilgisi → DKAB), tek kelimede ilk üç harf
 *  (Felsefe → FEL).
 */

/** Türkçe'ye uygun büyütme: i → İ, ı → I. */
export function buyut(metin: string): string {
  return metin.replace(/i/g, "İ").replace(/ı/g, "I").toUpperCase();
}

/** Yaygın MEB dersleri. Anahtarlar büyütülmüş ve sadeleştirilmiş hâlleriyle tutulur. */
const BILINEN: Record<string, string> = {
  TÜRKÇE: "TRK",
  "TÜRK DİLİ VE EDEBİYATI": "EDB",
  EDEBİYAT: "EDB",
  MATEMATİK: "MAT",
  GEOMETRİ: "GEO",
  "FEN BİLİMLERİ": "FEN",
  "FEN VE TEKNOLOJİ": "FEN",
  FİZİK: "FİZ",
  KİMYA: "KİM",
  BİYOLOJİ: "BİY",
  "SOSYAL BİLGİLER": "SOS",
  "HAYAT BİLGİSİ": "HAY",
  TARİH: "TAR",
  "T.C. İNKILAP TARİHİ VE ATATÜRKÇÜLÜK": "İNK",
  "İNKILAP TARİHİ": "İNK",
  COĞRAFYA: "COĞ",
  FELSEFE: "FEL",
  PSİKOLOJİ: "PSİ",
  SOSYOLOJİ: "SOSY",
  MANTIK: "MAN",
  "DİN KÜLTÜRÜ VE AHLAK BİLGİSİ": "DKAB",
  "TEMEL DİNİ BİLGİLER": "TDB",
  "PEYGAMBERİMİZİN HAYATI": "PEY",
  "KUR'AN-I KERİM": "KUR",
  "ARAPÇA": "ARP",
  İNGİLİZCE: "İNG",
  ALMANCA: "ALM",
  FRANSIZCA: "FRA",
  RUSÇA: "RUS",
  "YABANCI DİL": "YDL",
  MÜZİK: "MÜZ",
  "GÖRSEL SANATLAR": "GÖR",
  RESİM: "RES",
  "BEDEN EĞİTİMİ VE SPOR": "BED",
  "BEDEN EĞİTİMİ": "BED",
  "OYUN VE FİZİKİ ETKİNLİKLER": "OYUN",
  "TEKNOLOJİ VE TASARIM": "TEK",
  "BİLİŞİM TEKNOLOJİLERİ VE YAZILIM": "BİL",
  "BİLİŞİM TEKNOLOJİLERİ": "BİL",
  "BİLGİSAYAR BİLİMİ": "BİL",
  REHBERLİK: "REH",
  "REHBERLİK VE YÖNLENDİRME": "REH",
  "SAĞLIK BİLGİSİ": "SAĞ",
  "TRAFİK GÜVENLİĞİ": "TRF",
  "İNSAN HAKLARI YURTTAŞLIK VE DEMOKRASİ": "İHYD",
  "SEÇMELİ DERS": "SEÇ",
  "SERBEST ETKİNLİKLER": "SER",
  "ASTRONOMİ VE UZAY BİLİMLERİ": "AST",
  "SANAT TARİHİ": "SAN",
  "DRAMA": "DRM",
  "SATRANÇ": "SAT",
  "ZEKA OYUNLARI": "ZEK",
};

/** Baş harf alınmayan bağlaçlar. */
const BAGLAC = new Set(["VE", "İLE", "VEYA"]);

/** Ad sonundaki seviye ekleri: "Matematik 2", "Fizik II", "Almanca - 3".
 *  Ek, önünde bir ayraç olmadan sayılmaz; yoksa "Uygulamaları" gibi kelimelerin
 *  son harfi Roma rakamı sanılır. */
const SEVIYE_EKI = /(?:\s+|\s*[-–(]\s*)(?:\d+|[IVX]+)\s*\)?$/;

function sadelestir(ad: string): string {
  return buyut(ad).replace(/\s+/g, " ").trim();
}

/** Ders adına göre önerilen kısa kod. Ad boşsa boş dizge döner. */
export function kisaltmaOner(ad: string): string {
  const tam = sadelestir(ad);
  if (!tam) return "";

  if (BILINEN[tam]) return BILINEN[tam];

  // "Matematik 2" gibi seviye ekli adlarda kök adı dene, eki koru.
  const ek = tam.match(SEVIYE_EKI)?.[0]?.replace(/[\s()–-]/g, "") ?? "";
  const kok = tam.replace(SEVIYE_EKI, "").trim();
  if (ek && BILINEN[kok]) return BILINEN[kok] + ek;

  const kaynak = kok || tam;
  const kelimeler = kaynak
    .split(/[\s./-]+/)
    .map((k) => k.replace(/[^A-ZÇĞİÖŞÜ]/g, ""))
    .filter(Boolean);

  if (!kelimeler.length) return "";

  const anlamli = kelimeler.filter((k) => !BAGLAC.has(k));
  if (!anlamli.length) return "";

  // Üç ve daha fazla anlamlı kelime → baş harfler (en fazla 4).
  const govde =
    anlamli.length >= 3
      ? anlamli.slice(0, 4).map((k) => k[0]).join("")
      : anlamli[0].slice(0, 3);

  return govde + ek;
}
