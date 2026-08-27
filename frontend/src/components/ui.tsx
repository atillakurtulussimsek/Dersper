/** Küçük bileşen seti. Tailwind üzerine yazılmıştır, ek bağımlılık yoktur. */
import clsx from "clsx";
import { Loader2, X } from "lucide-react";
import type {
  ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

type ButonTuru = "birincil" | "ikincil" | "tehlike" | "sade";

const BUTON_STILLERI: Record<ButonTuru, string> = {
  birincil: "bg-slate-900 text-white hover:bg-slate-800 disabled:bg-slate-400",
  ikincil: "bg-white text-slate-800 border border-slate-300 hover:bg-slate-50",
  tehlike: "bg-red-600 text-white hover:bg-red-700",
  sade: "text-slate-600 hover:bg-slate-100",
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
        "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium",
        "transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1",
        "disabled:cursor-not-allowed disabled:opacity-70",
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
      <span className="mb-1 block text-sm font-medium text-slate-700">{etiket}</span>
      {children}
      {ipucu && !hata && <span className="mt-1 block text-xs text-slate-500">{ipucu}</span>}
      {hata && <span className="mt-1 block text-xs text-red-600">{hata}</span>}
    </label>
  );
}

const GIRDI_STILI =
  "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm " +
  "placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500";

export function Girdi(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={clsx(GIRDI_STILI, props.className)} />;
}

export function Secim(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={clsx(GIRDI_STILI, props.className)} />;
}

export function CokSatir(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={clsx(GIRDI_STILI, props.className)} />;
}

export function Kart({
  baslik,
  aciklama,
  sag,
  className,
  children,
}: {
  baslik?: string;
  aciklama?: string;
  sag?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={clsx(
        "rounded-xl border border-slate-200 bg-white shadow-sm",
        className,
      )}
    >
      {(baslik || sag) && (
        <header className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
          <div>
            {baslik && <h2 className="font-semibold text-slate-900">{baslik}</h2>}
            {aciklama && <p className="mt-0.5 text-sm text-slate-500">{aciklama}</p>}
          </div>
          {sag}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
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
    notr: "bg-slate-100 text-slate-700",
    iyi: "bg-emerald-100 text-emerald-800",
    uyari: "bg-amber-100 text-amber-800",
    kotu: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
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
    bilgi: "border-slate-200 bg-slate-50 text-slate-700",
    hata: "border-red-200 bg-red-50 text-red-800",
    basari: "border-emerald-200 bg-emerald-50 text-emerald-800",
  };
  return (
    <div className={clsx("rounded-lg border px-4 py-3 text-sm", stiller[tur])}>
      {children}
    </div>
  );
}

export function Yukleniyor({ metin = "Yükleniyor…" }: { metin?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-slate-500">
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
    <div className="rounded-lg border border-dashed border-slate-300 px-6 py-12 text-center">
      <p className="font-medium text-slate-700">{baslik}</p>
      {aciklama && <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{aciklama}</p>}
      {eylem && <div className="mt-4 flex justify-center">{eylem}</div>}
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
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4 sm:p-10"
      onClick={kapat}
    >
      <div
        className="w-full max-w-lg rounded-xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="font-semibold text-slate-900">{baslik}</h2>
          <button
            onClick={kapat}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
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
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            {basliklar.map((b) => (
              <th key={b} className="px-3 py-2 font-medium">
                {b}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">{children}</tbody>
      </table>
    </div>
  );
}
