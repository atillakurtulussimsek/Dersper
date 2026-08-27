import { useState } from "react";

import { Alan, Buton, Girdi, Uyari } from "../components/ui";
import { ApiHatasi, jetonuKaydet, post } from "../lib/api";

export default function Giris() {
  const [eposta, setEposta] = useState("");
  const [parola, setParola] = useState("");
  const [hata, setHata] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);

  async function gonder(e: React.FormEvent) {
    e.preventDefault();
    setHata(null);
    setGonderiliyor(true);
    try {
      const { access_token } = await post<{ access_token: string }>("/auth/login", {
        email: eposta,
        password: parola,
      });
      jetonuKaydet(access_token);
      location.href = "/";
    } catch (e) {
      setHata(e instanceof ApiHatasi ? e.message : "Giriş yapılamadı.");
      setGonderiliyor(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={gonder}
        className="w-full max-w-sm space-y-5 rounded-xl border border-slate-200 bg-white p-8 shadow-sm"
      >
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Dersper</h1>
          <p className="mt-1 text-sm text-slate-500">Yönetici girişi</p>
        </div>

        {hata && <Uyari tur="hata">{hata}</Uyari>}

        <Alan etiket="E-posta">
          <Girdi
            required
            type="email"
            value={eposta}
            onChange={(e) => setEposta(e.target.value)}
            autoComplete="username"
          />
        </Alan>

        <Alan etiket="Parola">
          <Girdi
            required
            type="password"
            value={parola}
            onChange={(e) => setParola(e.target.value)}
            autoComplete="current-password"
          />
        </Alan>

        <Buton type="submit" yukleniyor={gonderiliyor} className="w-full">
          Giriş yap
        </Buton>
      </form>
    </div>
  );
}
