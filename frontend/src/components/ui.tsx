/** Küçük bileşen seti.
 *
 *  Görünüm Metronic 8'den gelir: bileşenler Metronic'in kendi sınıflarını
 *  (.btn, .card, .form-control, .table, .badge, .alert) yayar. Buradaki iş,
 *  uygulamanın Türkçe adlandırılmış API'sini o sınıflara bağlamak ve tekrarı
 *  tek yerde toplamaktır.
 */
import clsx from "clsx";
import { Loader2, X } from "lucide-react";
import type {
  ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

type ButonTuru = "birincil" | "ikincil" | "tehlike" | "sade";

const BUTON_STILLERI: Record<ButonTuru, string> = {
  birincil: "btn-primary",
  ikincil: "btn-light",
  tehlike: "btn-light-danger",
  sade: "btn-color-gray-600 btn-active-light-primary",
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
        "btn btn-sm d-inline-flex align-items-center gap-2 flex-shrink-0",
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
    <label className="d-block">
      <span className="form-label fs-8 fw-semibold text-uppercase text-muted">
        {etiket}
      </span>
      {children}
      {ipucu && !hata && <span className="form-text">{ipucu}</span>}
      {hata && <span className="d-block mt-2 fs-8 text-danger">{hata}</span>}
    </label>
  );
}

/** Varsayılan genişlik tam; ama çağıran kendi genişliğini verdiyse ona dokunma.
 *
 *  Tailwind sınıfları eşit özgüllüktedir, dolayısıyla `w-full` ile `w-28` bir
 *  arada verildiğinde kazanan sınıfın yazılış sırası değil, üretilen CSS'teki
 *  sırasıdır. Bu da alanların beklenmedik genişliklere çıkmasına yol açar. */
function girdiSinifi(temel: string, gelen?: string): string {
  const genislikVar = gelen ? /(^|\s)(w-|min-w-|max-w-|flex-1|basis-)/.test(gelen) : false;
  return clsx(temel, !genislikVar && "w-full", gelen);
}

export function Girdi(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={girdiSinifi("form-control form-control-sm", props.className)}
    />
  );
}

export function Secim(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={girdiSinifi("form-select form-select-sm", props.className)}
    />
  );
}

export function CokSatir(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={girdiSinifi("form-control form-control-sm", props.className)}
    />
  );
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
    <div className={clsx("card", className)}>
      {(baslik || sag) && (
        <div className="card-header align-items-center gap-4">
          <div className="card-title flex-column align-items-start gap-1 min-w-0">
            {baslik && <h3 className="fw-bold fs-5 m-0">{baslik}</h3>}
            {aciklama && <span className="text-muted fs-7 fw-normal">{aciklama}</span>}
          </div>
          {sag && <div className="card-toolbar flex-shrink-0">{sag}</div>}
        </div>
      )}
      <div className="card-body">{children}</div>
    </div>
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
    notr: "badge-light",
    iyi: "badge-light-success",
    uyari: "badge-light-warning",
    kotu: "badge-light-danger",
  };
  return <span className={clsx("badge", stiller[tur])}>{children}</span>;
}

export function Uyari({
  tur = "bilgi",
  children,
}: {
  tur?: "bilgi" | "hata" | "basari";
  children: ReactNode;
}) {
  const stiller = {
    bilgi: "bg-light-primary text-gray-700",
    hata: "bg-light-danger text-danger",
    basari: "bg-light-success text-success",
  };
  return (
    <div className={clsx("alert d-flex mb-0 fs-7", stiller[tur])}>{children}</div>
  );
}

export function Yukleniyor({ metin = "Yükleniyor…" }: { metin?: string }) {
  return (
    <div className="d-flex align-items-center gap-2 py-10 fs-7 text-muted">
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
    <div className="border border-gray-300 border-dashed rounded px-6 py-12 text-center">
      <p className="fw-bold fs-5 text-gray-800 mb-1">{baslik}</p>
      {aciklama && (
        <p className="mx-auto max-w-md fs-7 text-muted mb-0">{aciklama}</p>
      )}
      {eylem && <div className="mt-5 d-flex justify-content-center">{eylem}</div>}
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
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 sm:p-10"
      onClick={kapat}
    >
      <div
        className="modal-content w-full max-w-lg shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header py-4">
          <h2 className="fw-bold fs-5 m-0">{baslik}</h2>
          <button
            onClick={kapat}
            className="btn btn-icon btn-sm btn-active-light-primary"
            aria-label="Kapat"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="modal-body">{children}</div>
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
    <div className="table-responsive">
      <table className="table table-row-dashed table-row-gray-300 align-middle gy-3 mb-0">
        <thead>
          <tr className="fw-bold text-muted text-uppercase fs-8 text-start">
            {basliklar.map((b, i) => (
              <th key={`${b}-${i}`}>{b}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

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
    <div className="d-flex flex-wrap align-items-start justify-content-between gap-3">
      <div className="min-w-0">
        <h1 className="page-heading fw-bold fs-2 text-gray-900 m-0">{baslik}</h1>
        {aciklama && (
          <p className="text-muted fs-7 mt-1 mb-0 max-w-2xl">{aciklama}</p>
        )}
      </div>
      {sag && <div className="d-flex flex-wrap gap-2 flex-shrink-0">{sag}</div>}
    </div>
  );
}
