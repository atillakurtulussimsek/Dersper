/** Backend istemcisi. Oturum jetonu localStorage'da tutulur. */

const JETON_ANAHTARI = "dersper_token";

export function jetonuAl(): string | null {
  return localStorage.getItem(JETON_ANAHTARI);
}

export function jetonuKaydet(token: string): void {
  localStorage.setItem(JETON_ANAHTARI, token);
}

export function jetonuSil(): void {
  localStorage.removeItem(JETON_ANAHTARI);
}

export class ApiHatasi extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

function hataMesaji(status: number, govde: unknown): string {
  if (typeof govde === "string" && govde) return govde;
  const detay = (govde as { detail?: unknown })?.detail;
  if (typeof detay === "string") return detay;
  if (Array.isArray(detay)) {
    // Pydantic doğrulama hataları
    return detay
      .map((d: { loc?: unknown[]; msg?: string }) =>
        [d.loc?.slice(1).join("."), d.msg].filter(Boolean).join(": "),
      )
      .join(" · ");
  }
  if (status === 401) return "Oturumunuz sona ermiş. Yeniden giriş yapın.";
  return `Beklenmeyen bir hata oluştu (${status}).`;
}

export async function api<T>(
  yol: string,
  secenekler: RequestInit = {},
): Promise<T> {
  const basliklar = new Headers(secenekler.headers);
  if (secenekler.body && !basliklar.has("Content-Type")) {
    basliklar.set("Content-Type", "application/json");
  }
  const jeton = jetonuAl();
  if (jeton) basliklar.set("Authorization", `Bearer ${jeton}`);

  const yanit = await fetch(`/api${yol}`, { ...secenekler, headers: basliklar });

  if (yanit.status === 401) {
    jetonuSil();
    if (!location.pathname.startsWith("/giris")) location.href = "/giris";
    throw new ApiHatasi(401, "Oturumunuz sona ermiş.");
  }
  if (yanit.status === 204) return undefined as T;

  const metin = await yanit.text();
  const govde = metin ? JSON.parse(metin) : null;
  if (!yanit.ok) throw new ApiHatasi(yanit.status, hataMesaji(yanit.status, govde));
  return govde as T;
}

export const get = <T,>(yol: string) => api<T>(yol);
export const post = <T,>(yol: string, veri?: unknown) =>
  api<T>(yol, { method: "POST", body: veri === undefined ? undefined : JSON.stringify(veri) });
export const put = <T,>(yol: string, veri: unknown) =>
  api<T>(yol, { method: "PUT", body: JSON.stringify(veri) });
export const patch = <T,>(yol: string, veri: unknown) =>
  api<T>(yol, { method: "PATCH", body: JSON.stringify(veri) });
export const del = (yol: string) => api<void>(yol, { method: "DELETE" });
