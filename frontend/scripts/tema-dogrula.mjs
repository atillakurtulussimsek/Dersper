/** Derlemeden önce temanın kurulu olduğunu doğrular.
 *
 *  Eksikse derleme durdurulmaz — biçimsiz de olsa çalışan bir arayüz çıkar —
 *  ama sessizce geçilmez: eksik tema, derleyen kişinin görmesi gereken bir
 *  durumdur, çünkü sonuç ancak çalıştırınca fark edilir.
 */
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const buradan = dirname(fileURLToPath(import.meta.url));
const dosya = join(buradan, "..", "public", "metronic", "style.bundle.css");

if (!existsSync(dosya)) {
  console.warn(
    [
      "",
      "  UYARI: Metronic teması kurulu değil.",
      "  Arayüz derlenir ama biçimsiz görünür.",
      "",
      "  Düzeltmek için:  npm run tema:kur",
      "  Ayrıntı: README > Kurulum > Tema",
      "",
    ].join("\n"),
  );
}
