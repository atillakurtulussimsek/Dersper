import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";

import { Buton, Uyari, Yukleniyor } from "./components/ui";
import Kabuk from "./components/Kabuk";
import { get, jetonuAl } from "./lib/api";
import Ayarlar from "./pages/Ayarlar";
import DersAtamalari from "./pages/DersAtamalari";
import Dersler from "./pages/Dersler";
import Donemler from "./pages/Donemler";
import Giris from "./pages/Giris";
import Kayit from "./pages/Kayit";
import Kullanicilar from "./pages/Kullanicilar";
import Ogretmenler from "./pages/Ogretmenler";
import Ozet from "./pages/Ozet";
import ProgramDetay from "./pages/ProgramDetay";
import Programlar from "./pages/Programlar";
import Subeler from "./pages/Subeler";
import Yayin from "./pages/Yayin";
import ZamanIzgarasi from "./pages/ZamanIzgarasi";
import type { OturumDurumu } from "./lib/types";

export default function App() {
  const durum = useQuery({
    queryKey: ["auth-status"],
    queryFn: () => get<OturumDurumu>("/auth/status"),
    // Sunucuya ulaşılamıyorsa sonsuza kadar beklemektense hata göster.
    retry: 1,
  });

  if (durum.isPending) return <Yukleniyor metin="Başlatılıyor…" />;

  if (durum.isError) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-md space-y-4 rounded-xl border border-cizgi bg-yuzey p-8 shadow-sm">
          <h1 className="text-lg font-semibold tracking-tight">
            Sunucuya ulaşılamıyor
          </h1>
          <Uyari tur="hata">{(durum.error as Error).message}</Uyari>
          <p className="text-sm text-murekkep-silik">
            Uygulama çalışıyor ama <code>/api</code> yanıt vermedi. En sık sebebi
            veritabanına erişilememesidir; <code>/api/health/db</code> adresi
            durumu söyler.
          </p>
          <Buton onClick={() => durum.refetch()} yukleniyor={durum.isFetching}>
            Yeniden dene
          </Buton>
        </div>
      </div>
    );
  }

  const kayitAcik = durum.data?.registration_open ?? false;
  const oturumVar = Boolean(jetonuAl());

  return (
    <Routes>
      <Route path="/p/:token" element={<Yayin />} />
      <Route
        path="/kayit"
        element={kayitAcik ? <Kayit /> : <Navigate to="/giris" replace />}
      />
      <Route path="/giris" element={<Giris />} />
      {/* Eski kurulum adresi kayda yönlendirilir. */}
      <Route path="/kurulum" element={<Navigate to="/kayit" replace />} />
      {!oturumVar ? (
        <Route
          path="*"
          element={
            <Navigate
              // Sistemde hiç kurum yoksa doğrudan kayda götür.
              to={durum.data?.has_institutions ? "/giris" : "/kayit"}
              replace
            />
          }
        />
      ) : (
        <Route element={<Kabuk />}>
          <Route path="/" element={<Ozet />} />
          <Route path="/ogretmenler" element={<Ogretmenler />} />
          <Route path="/dersler" element={<Dersler />} />
          <Route path="/subeler" element={<Subeler />} />
          <Route path="/ders-atamalari" element={<DersAtamalari />} />
          {/* Eski adres, yer imleri bozulmasın diye yönlendirilir. */}
          <Route path="/mufredat" element={<Navigate to="/ders-atamalari" replace />} />
          <Route path="/zaman-izgarasi" element={<ZamanIzgarasi />} />
          <Route path="/programlar" element={<Programlar />} />
          <Route path="/programlar/:id" element={<ProgramDetay />} />
          <Route path="/donemler" element={<Donemler />} />
          <Route path="/kullanicilar" element={<Kullanicilar />} />
          <Route path="/ayarlar" element={<Ayarlar />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      )}
    </Routes>
  );
}
