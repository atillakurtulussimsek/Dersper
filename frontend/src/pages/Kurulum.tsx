/** İlk kurulum sihirbazı. Kurum ve tek yönetici hesabı oluşturur. */
import { useState } from "react";

import { Alan, Buton, Girdi, Secim, Uyari } from "../components/ui";
import { ApiHatasi, jetonuKaydet, post } from "../lib/api";
import type { KurumTipi } from "../lib/types";

export default function Kurulum() {
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
      const { access_token } = await post<{ access_token: string }>("/setup", {
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
      setHata(e instanceof ApiHatasi ? e.message : "Kurulum tamamlanamadı.");
      setGonderiliyor(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={gonder}
        className="w-full max-w-lg space-y-5 rounded-xl border border-slate-200 bg-white p-8 shadow-sm"
      >
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Dersper kurulumu</h1>
          <p className="mt-1 text-sm text-slate-500">
            Kurumunuzu tanımlayın ve yönetici hesabınızı oluşturun. Bu ekran yalnızca
            bir kez görünür.
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

        <hr className="border-slate-100" />

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
          Kurulumu tamamla
        </Buton>
      </form>
    </div>
  );
}
