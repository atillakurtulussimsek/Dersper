/** Renk seçici. Varsayılan olarak "rastgele" seçilidir: yeni kayıt açıldığında
 *  paletten, o dönemde kullanılmayan bir renk otomatik atanır. */
import { Shuffle } from "lucide-react";
import clsx from "clsx";

import { PALET, rastgeleRenk } from "../lib/renkler";

export default function RenkSecici({
  deger,
  degistir,
  rastgele,
  rastgeleDegistir,
  kullanilanlar = [],
}: {
  deger: string;
  degistir: (renk: string) => void;
  /** Rastgele kipi açık mı — açıkken renk otomatik atanmıştır. */
  rastgele: boolean;
  rastgeleDegistir: (acik: boolean) => void;
  /** Zaten kullanılan renkler; rastgele seçim bunlardan kaçınır. */
  kullanilanlar?: string[];
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <button
        type="button"
        title={
          rastgele
            ? "Rastgele seçili — yeniden karmak için tıklayın"
            : "Rastgele renk ata"
        }
        onClick={() => {
          rastgeleDegistir(true);
          degistir(rastgeleRenk(kullanilanlar));
        }}
        className={clsx(
          "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors",
          rastgele
            ? "border-murekkep bg-murekkep text-uzeri"
            : "border-cizgi-guclu bg-yuzey text-murekkep-yumusak hover:bg-yuzey-alt",
        )}
      >
        <Shuffle className="h-3.5 w-3.5" />
        Rastgele
        {rastgele && (
          <span
            className="ml-0.5 h-3.5 w-3.5 rounded-full ring-1 ring-uzeri/40"
            style={{ background: deger }}
          />
        )}
      </button>

      <span className="h-5 w-px bg-cizgi" />

      {PALET.map((r) => (
        <button
          key={r}
          type="button"
          onClick={() => {
            rastgeleDegistir(false);
            degistir(r);
          }}
          style={{ background: r }}
          className={clsx(
            "h-6 w-6 rounded-full ring-offset-2 transition",
            !rastgele && deger.toLowerCase() === r && "ring-2 ring-murekkep",
          )}
          aria-label={`Renk ${r}`}
        />
      ))}
    </div>
  );
}
