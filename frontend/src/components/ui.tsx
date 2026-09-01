/** Küçük bileşen seti.
 *
 *  Renk kullanmaz: tüm yüzeyler ve metinler tasarım belirteçlerinden gelir
 *  (bkz. src/index.css). Ekrandaki tek kroma kaynağı kullanıcının seçtiği ders
 *  ve öğretmen renkleridir; arayüz kromu onlarla yarışmaz.
 */
import clsx from "clsx";
import { ChevronRight, Loader2, X } from "lucide-react";
import type {
  ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

type ButonTuru = "birincil" | "ikincil" | "tehlike" | "sade";

const BUTON_STILLERI: Record<ButonTuru, string> = {
  birincil: "bg-murekkep text-uzeri hover:opacity-90",
  ikincil: "border border-cizgi-guclu bg-yuzey text-murekkep hover:bg-yuzey-alt",
  tehlike: "border border-hata/30 bg-hata-zemin text-hata hover:bg-hata/15",
  sade: "text-murekkep-yumusak hover:bg-yuzey-alt hover:text-murekkep",
};

export function Buton({
  tur = "birincil",
  yukleniyor = false,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  tur?: ButonTuru;
  yukleniyor?: boolean;
}) {
  return (
    <button
      {...rest}
      disabled={rest.disabled || yukleniyor}
      className={clsx(
        "inline-flex shrink-0 items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium",
        "transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2",
        "focus-visible:ring-murekkep focus-visible:ring-offset-2 focus-visible:ring-offset-kagit",
        "disabled:cursor-not-allowed disabled:opacity-50",
        BUTON_STILLERI[tur],
        className,
      )}
    >
      {yukleniyor && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Alan({
  etiket,
  ipucu,
  hata,
  children,
}: {
  etiket: string;
  ipucu?: string;
  hata?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-2xs font-semibold uppercase tracking-[0.08em] text-murekkep-silik">
        {etiket}
      </span>
      {children}
      {ipucu && !hata && (
        <span className="mt-1.5 block text-xs leading-relaxed text-murekkep-silik">
          {ipucu}
        </span>
      )}
      {hata && <span className="mt-1.5 block text-xs text-hata">{hata}</span>}
    </label>
  );
}

const GIRDI_STILI = clsx(
  "rounded-lg border border-cizgi-guclu bg-yuzey px-3 py-2 text-sm text-murekkep",
  "placeholder:text-murekkep-silik/70 transition-colors",
  "focus:border-murekkep focus:outline-none focus:ring-1 focus:ring-murekkep",
  "disabled:bg-yuzey-alt disabled:text-murekkep-silik",
);

/** Varsayılan genişlik tam; ama çağıran kendi genişliğini verdiyse ona dokunma.
 *
 *  Tailwind sınıfları eşit özgüllüktedir, dolayısıyla `w-full` ile `w-28` bir
 *  arada verildiğinde kazanan sınıfın yazılış sırası değil, üretilen CSS'teki
 *  sırasıdır. Bu da alanların beklenmedik genişliklere çıkmasına yol açar. */
function girdiSinifi(gelen?: string): string {
  const genislikVar = gelen ? /(^|\s)(w-|min-w-|max-w-|flex-1|basis-)/.test(gelen) : false;
  return clsx(GIRDI_STILI, !genislikVar && "w-full", gelen);
}

export function Girdi(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={girdiSinifi(props.className)} />;
}

export function Secim(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={girdiSinifi(props.className)} />;
}

export function CokSatir(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={girdiSinifi(props.className)} />;
}

export function Kart({
  baslik,
  aciklama,
  sag,
  katlanir = false,
  acik = false,
  ozet,
  className,
  children,
}: {
  baslik?: string;
  aciklama?: string;
  sag?: ReactNode;
  /** Başlık tıklanınca açılıp kapanır; kapalıyken kart tek satırdır. */
  katlanir?: boolean;
  /** Katlanır kartın açılıştaki hâli. */
  acik?: boolean;
  /** Kapalıyken başlığın yanında görünen kısa bilgi ("6 deneme" gibi). */
  ozet?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  const kabuk = clsx("rounded-xl border border-cizgi bg-yuzey", className);

  /* Saat rayı: başlıklar ızgaradaki ders saatleri gibi işaretlenir. */
  const ustluk = (
    <>
      {baslik && (
        <h2 className="ray font-baslik text-[0.95rem] font-semibold tracking-tight text-murekkep">
          {baslik}
        </h2>
      )}
      {aciklama && !katlanir && (
        <p className="mt-1 pl-[1.125rem] text-sm text-murekkep-silik">{aciklama}</p>
      )}
    </>
  );

  /* Seyrek bakılan bölümler sayfayı uzatmasın diye kapalı durabilir. Yerli
   * <details> tercih edildi: klavye ve ekran okuyucu desteği hazır gelir,
   * durum React'te tutulmaz, sayfada arama (Ctrl+F) içeriği bulup açar. */
  if (katlanir) {
    return (
      <details className={clsx(kabuk, "group/kart")} open={acik}>
        <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-3.5 [&::-webkit-details-marker]:hidden">
          <ChevronRight className="h-4 w-4 shrink-0 text-murekkep-silik transition-transform group-open/kart:rotate-90" />
          <div className="min-w-0 flex-1">{ustluk}</div>
          {ozet && (
            <span className="shrink-0 text-xs text-murekkep-silik group-open/kart:hidden">
              {ozet}
            </span>
          )}
          {sag && <span onClick={(e) => e.stopPropagation()}>{sag}</span>}
        </summary>
        <div className="border-t border-cizgi p-5">
          {aciklama && (
            <p className="mb-4 -mt-1 text-sm text-murekkep-silik">{aciklama}</p>
          )}
          {children}
        </div>
      </details>
    );
  }

  return (
    <section className={kabuk}>
      {(baslik || sag) && (
        <header className="flex items-start justify-between gap-4 border-b border-cizgi px-5 py-3.5">
          <div className="min-w-0">{ustluk}</div>
          {sag}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

/** Katlanmış kullanım notu.
 *
 *  Bu metinler ilk kez kullanana gerekli, sonra sürekli yer kaplar. Kapalı
 *  hâlde tek satır; <details> olduğu için Ctrl+F ile aranınca kendi açılır. */
export function Ipucu({
  etiket = "Nasıl kullanılır?",
  children,
}: {
  etiket?: string;
  children: ReactNode;
}) {
  return (
    <details className="group/ipucu mt-3">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 text-xs text-murekkep-silik hover:text-murekkep-yumusak [&::-webkit-details-marker]:hidden">
        <ChevronRight className="h-3.5 w-3.5 transition-transform group-open/ipucu:rotate-90" />
        {etiket}
      </summary>
      <p className="mt-2 pl-5 text-xs leading-relaxed text-murekkep-silik">
        {children}
      </p>
    </details>
  );
}

export function Rozet({
  tur = "notr",
  children,
}: {
  tur?: "notr" | "iyi" | "uyari" | "kotu";
  children: ReactNode;
}) {
  const stiller = {
    notr: "bg-yuzey-alt text-murekkep-yumusak ring-cizgi",
    iyi: "bg-basari-zemin text-basari ring-basari/20",
    uyari: "bg-uyari-zemin text-uyari ring-uyari/20",
    kotu: "bg-hata-zemin text-hata ring-hata/20",
  };
  return (
    <span
      className={clsx(
        "inline-flex shrink-0 items-center rounded-md px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-[0.06em] ring-1 ring-inset",
        stiller[tur],
      )}
    >
      {children}
    </span>
  );
}

export function Uyari({
  tur = "bilgi",
  children,
}: {
  tur?: "bilgi" | "hata" | "basari";
  children: ReactNode;
}) {
  const stiller = {
    bilgi: "border-cizgi bg-yuzey-alt text-murekkep-yumusak",
    hata: "border-hata/25 bg-hata-zemin text-hata",
    basari: "border-basari/25 bg-basari-zemin text-basari",
  };
  return (
    <div
      className={clsx(
        "rounded-lg border px-4 py-2.5 text-sm leading-relaxed",
        stiller[tur],
      )}
    >
      {children}
    </div>
  );
}

export function Yukleniyor({ metin = "Yükleniyor…" }: { metin?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-murekkep-silik">
      <Loader2 className="h-4 w-4 animate-spin" />
      {metin}
    </div>
  );
}

export function BosDurum({
  baslik,
  aciklama,
  eylem,
}: {
  baslik: string;
  aciklama?: string;
  eylem?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-cizgi-guclu px-6 py-12 text-center">
      <p className="font-baslik font-semibold text-murekkep">{baslik}</p>
      {aciklama && (
        <p className="mx-auto mt-1.5 max-w-md text-sm leading-relaxed text-murekkep-silik">
          {aciklama}
        </p>
      )}
      {eylem && <div className="mt-5 flex justify-center">{eylem}</div>}
    </div>
  );
}

export function Kutu({
  acik,
  kapat,
  baslik,
  children,
}: {
  acik: boolean;
  kapat: () => void;
  baslik: string;
  children: ReactNode;
}) {
  if (!acik) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-murekkep/40 p-4 backdrop-blur-[2px] sm:p-10"
      onClick={kapat}
    >
      <div
        className="w-full max-w-lg rounded-xl border border-cizgi bg-yuzey shadow-2xl shadow-murekkep/10"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-cizgi px-5 py-3.5">
          <h2 className="ray font-baslik text-[0.95rem] font-semibold tracking-tight text-murekkep">
            {baslik}
          </h2>
          <button
            onClick={kapat}
            className="rounded-md p-1 text-murekkep-silik transition-colors hover:bg-yuzey-alt hover:text-murekkep"
            aria-label="Kapat"
          >
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function Tablo({
  basliklar,
  children,
}: {
  basliklar: string[];
  children: ReactNode;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-cizgi text-left text-2xs uppercase tracking-[0.08em] text-murekkep-silik">
            {basliklar.map((b, i) => (
              <th key={`${b}-${i}`} className="px-3 py-2 font-semibold">
                {b}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-cizgi">{children}</tbody>
      </table>
    </div>
  );
}

/** Sayfa başlığı. Ray motifi burada en belirgin hâlini alır. */
export function SayfaBasligi({
  baslik,
  aciklama,
  sag,
}: {
  baslik: string;
  aciklama?: string;
  sag?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="ray min-w-0">
        <h1 className="font-baslik text-2xl font-semibold tracking-tight text-murekkep">
          {baslik}
        </h1>
        {aciklama && (
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-murekkep-silik">
            {aciklama}
          </p>
        )}
      </div>
      {sag && <div className="flex shrink-0 flex-wrap gap-2">{sag}</div>}
    </header>
  );
}
