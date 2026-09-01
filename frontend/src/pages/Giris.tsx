import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Alan, Buton, Girdi, Uyari } from "../components/ui";
import { ApiHatasi, get, jetonuKaydet, post } from "../lib/api";
import type { OturumDurumu } from "../lib/types";

export default function Giris() {
  const [eposta, setEposta] = useState("");
  const [parola, setParola] = useState("");
  const [hata, setHata] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const durum = useQuery({
    queryKey: ["auth-status"],
    queryFn: () => get<OturumDurumu>("/auth/status"),
  });

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
    <div className="d-flex min-h-screen align-items-center justify-content-center p-4">
      <form onSubmit={gonder} className="card w-full max-w-sm shadow-sm">
        <div className="card-body p-10 space-y-5">
          <div className="text-center">
            <span className="symbol symbol-50px d-inline-block mb-4">
              <span className="symbol-label bg-primary text-inverse-primary fw-bold fs-2">
                D
              </span>
            </span>
            <h1 className="fw-bold fs-2 text-gray-900 m-0">Dersper</h1>
            <p className="text-muted fs-7 mt-1 mb-0">Kurum hesabınızla giriş yapın.</p>
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

          {durum.data?.registration_open && (
            <p className="text-center fs-7 text-muted mb-0">
              Kurumunuz kayıtlı değil mi?{" "}
              <Link to="/kayit" className="link-primary fw-semibold">
                Kurum kaydı oluşturun
              </Link>
            </p>
          )}
        </div>
      </form>
    </div>
  );
}
