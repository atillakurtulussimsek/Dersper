/** Kurum kaydı. Kurumu, ilk kullanıcıyı ve ilk dönemi birlikte oluşturur.
 *
 *  Sunucuda kayıt kapalıysa (ALLOW_REGISTRATION=false) bu sayfa yalnızca
 *  sistemde hiç kurum yokken açılır; ilk kurulum böylece kilitlenmez.
 */
import { useState } from "react";
import { Link } from "react-router-dom";

import { Alan, Buton, Girdi, Secim, Uyari } from "../components/ui";
import { ApiHatasi, jetonuKaydet, post } from "../lib/api";
import type { KurumTipi } from "../lib/types";

export default function Kayit() {
  const [kurumAdi, setKurumAdi] = useState("");
  const [kurumTipi, setKurumTipi] = useState<KurumTipi>("k12");
  const [donemAdi, setDonemAdi] = useState("2026-2027 Güz Dönemi");
  const [adSoyad, setAdSoyad] = useState("");
  const [eposta, setEposta] = useState("");
  const [parola, setParola] = useState("");
  const [parolaTekrar, setParolaTekrar] = useState("");
  const [hata, setHata] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);

  async function gonder(e: React.FormEvent) {
    e.preventDefault();
    setHata(null);
    if (parola !== parolaTekrar) return setHata("Parolalar birbirini tutmuyor.");
    if (parola.length < 8) return setHata("Parola en az 8 karakter olmalı.");

    setGonderiliyor(true);
    try {
      const { access_token } = await post<{ access_token: string }>("/auth/register", {
        institution_name: kurumAdi,
        institution_type: kurumTipi,
        term_name: donemAdi,
        full_name: adSoyad,
        email: eposta,
        password: parola,
      });
      jetonuKaydet(access_token);
      location.href = "/";
    } catch (e) {
      setHata(e instanceof ApiHatasi ? e.message : "Kayıt tamamlanamadı.");
      setGonderiliyor(false);
    }
  }

  return (
    <div className="d-flex min-h-screen align-items-center justify-content-center p-4">
      <form onSubmit={gonder} className="card w-full max-w-lg shadow-sm my-10">
        <div className="card-body p-10 space-y-5">
        <div className="text-center">
          <span className="symbol symbol-50px d-inline-block mb-4">
            <span className="symbol-label bg-primary text-inverse-primary fw-bold fs-2">
              D
            </span>
          </span>
          <h1 className="fw-bold fs-2 text-gray-900 m-0">Kurum kaydı</h1>
          <p className="text-muted fs-7 mt-1 mb-0">
            Kurumunuzu tanımlayın ve ilk hesabınızı oluşturun. Bir hesap yalnızca bir
            kuruma bağlanır; başka bir kurum için ayrı hesap açmanız gerekir.
          </p>
        </div>

        {hata && <Uyari tur="hata">{hata}</Uyari>}

        <Alan etiket="Kurum adı">
          <Girdi
            required
            minLength={2}
            value={kurumAdi}
            onChange={(e) => setKurumAdi(e.target.value)}
            placeholder="Örn. Atatürk Ortaokulu"
          />
        </Alan>

        <Alan etiket="Kurum tipi">
          <Secim value={kurumTipi} onChange={(e) => setKurumTipi(e.target.value as KurumTipi)}>
            <option value="k12">Okul (ilkokul / ortaokul / lise)</option>
            <option value="kurs">Kurs / dershane / dil okulu</option>
          </Secim>
        </Alan>

        <Alan
          etiket="İlk dönem adı"
          ipucu="Tüm tanımlar bir döneme aittir. Sonradan yeni dönem açabilirsiniz."
        >
          <Girdi
            required
            value={donemAdi}
            onChange={(e) => setDonemAdi(e.target.value)}
          />
        </Alan>

        <hr className="border-cizgi" />

        <Alan etiket="Adınız soyadınız">
          <Girdi required value={adSoyad} onChange={(e) => setAdSoyad(e.target.value)} />
        </Alan>

        <Alan etiket="E-posta">
          <Girdi
            required
            type="email"
            value={eposta}
            onChange={(e) => setEposta(e.target.value)}
            autoComplete="username"
          />
        </Alan>

        <div className="grid gap-4 sm:grid-cols-2">
          <Alan etiket="Parola" ipucu="En az 8 karakter">
            <Girdi
              required
              type="password"
              value={parola}
              onChange={(e) => setParola(e.target.value)}
              autoComplete="new-password"
            />
          </Alan>
          <Alan etiket="Parola tekrar">
            <Girdi
              required
              type="password"
              value={parolaTekrar}
              onChange={(e) => setParolaTekrar(e.target.value)}
              autoComplete="new-password"
            />
          </Alan>
        </div>

        <Buton type="submit" yukleniyor={gonderiliyor} className="w-full">
          Kurumu oluştur
        </Buton>

        <p className="text-center fs-7 text-muted mb-0">
          Hesabınız var mı?{" "}
          <Link to="/giris" className="link-primary fw-semibold">
            Giriş yapın
          </Link>
        </p>
        </div>
      </form>
    </div>
  );
}
