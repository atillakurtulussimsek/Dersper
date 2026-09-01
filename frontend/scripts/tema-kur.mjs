/** Metronic temasını projeye kurar.
 *
 *  Metronic (KeenThemes) tescilli bir üründür; dosyaları bu açık kaynak depoya
 *  giremez. Bu yüzden tema kaynağı depoda bulunmaz: kurulumu yapan kişi kendi
 *  lisanslı kopyasını sağlar, bu betik de gereken tek dosyayı `public/` altına
 *  kopyalar. Kopyalanan dizin `.gitignore` içindedir.
 *
 *  Yalnızca `assets/css/style.bundle.css` gerekir; içindeki tüm ikon ve desenler
 *  data-URI olduğu için ayrıca yazı tipi ya da görsel taşımaya gerek yoktur.
 *
 *  Kullanım:
 *    npm run tema:kur                     # ../Metronic klasörünü arar
 *    METRONIC_DIZINI=/yol/to/metronic npm run tema:kur
 */
import { copyFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const buradan = dirname(fileURLToPath(import.meta.url));
const kok = resolve(buradan, "..", "..");

// Sırayla denenir: ortam değişkeni, depo kökündeki Metronic, bir üst dizin.
const adaylar = [
  process.env.METRONIC_DIZINI,
  join(kok, "Metronic"),
  join(kok, "..", "Metronic"),
].filter(Boolean);

const DOSYA = join("assets", "css", "style.bundle.css");

const kaynak = adaylar
  .map((d) => join(resolve(d), DOSYA))
  .find((y) => existsSync(y));

if (!kaynak) {
  console.error(
    [
      "Metronic bulunamadı.",
      "",
      "Bu proje arayüzünü Metronic 8 (KeenThemes) üzerine kurar. Tema tescillidir",
      "ve depoya dahil edilemez; kendi lisanslı kopyanızı edinmeniz gerekir:",
      "  https://keenthemes.com/metronic",
      "",
      "Sonra klasörü depo köküne `Metronic/` olarak koyun ya da yolunu verin:",
      "  METRONIC_DIZINI=/bir/yer/metronic npm run tema:kur",
      "",
      `Aranan dosya: ${DOSYA}`,
      "Bakılan yerler:",
      ...adaylar.map((d) => `  ${join(resolve(d), DOSYA)}`),
    ].join("\n"),
  );
  process.exit(1);
}

const hedefDizin = join(buradan, "..", "public", "metronic");
const hedef = join(hedefDizin, "style.bundle.css");
mkdirSync(hedefDizin, { recursive: true });
copyFileSync(kaynak, hedef);

const kb = Math.round(statSync(hedef).size / 1024);
console.log(`Metronic teması kuruldu: public/metronic/style.bundle.css (${kb} KB)`);
console.log(`Kaynak: ${kaynak}`);
