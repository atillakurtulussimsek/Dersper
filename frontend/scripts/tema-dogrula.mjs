/** Derlemeden önce temanın kurulu olduğunu doğrular.
 *
 *  Tema eksikse derleme DURUR. Arayüzün tamamı Metronic sınıflarına dayanıyor;
 *  o dosya olmadan çıkan paket çalışır ama kullanılamaz görünür. Uyarıp devam
 *  etmek, bozuk bir arayüzün fark edilmeden yayına çıkmasına yol açtı — bu
 *  yüzden artık hata veriyor.
 *
 *  Bilerek temasız derlemek gerekirse (ör. yalnızca tip denetimi):
 *    TEMASIZ_DERLE=1 npm run build
 */
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const buradan = dirname(fileURLToPath(import.meta.url));
const dosya = join(buradan, "..", "public", "metronic", "style.bundle.css");

if (existsSync(dosya)) process.exit(0);

const mesaj = [
  "",
  "  Metronic teması kurulu değil — derleme durduruldu.",
  "",
  "  Arayüzün tamamı bu temanın sınıflarına dayanır; dosya olmadan çıkan",
  "  paket biçimsiz görünür.",
  "",
  "  Düzeltmek için:",
  "    npm run tema:kur",
  "",
  "  Tema tescillidir ve depoda bulunmaz; lisanslı kopyanızı depo köküne",
  "  `Metronic/` olarak koyun ya da yolunu verin:",
  "    METRONIC_DIZINI=/bir/yer/metronic npm run tema:kur",
  "",
  "  Ayrıntı: README > Kurulum > Tema",
  "",
].join("\n");

if (process.env.TEMASIZ_DERLE === "1") {
  console.warn(mesaj.replace("derleme durduruldu", "TEMASIZ_DERLE=1 ile geçildi"));
  process.exit(0);
}

console.error(mesaj);
process.exit(1);
