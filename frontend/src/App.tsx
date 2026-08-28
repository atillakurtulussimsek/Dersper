import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";

import { Yukleniyor } from "./components/ui";
import Kabuk from "./components/Kabuk";
import { get, jetonuAl } from "./lib/api";
import Ayarlar from "./pages/Ayarlar";
import Dersler from "./pages/Dersler";
import Donemler from "./pages/Donemler";
import Giris from "./pages/Giris";
import Kurulum from "./pages/Kurulum";
import DersAtamalari from "./pages/DersAtamalari";
import Ogretmenler from "./pages/Ogretmenler";
import Ozet from "./pages/Ozet";
import ProgramDetay from "./pages/ProgramDetay";
import Programlar from "./pages/Programlar";
import Subeler from "./pages/Subeler";
import Yayin from "./pages/Yayin";
import ZamanIzgarasi from "./pages/ZamanIzgarasi";

export default function App() {
  const kurulum = useQuery({
    queryKey: ["setup-status"],
    queryFn: () => get<{ completed: boolean }>("/setup/status"),
  });

  if (kurulum.isLoading) return <Yukleniyor metin="Başlatılıyor…" />;

  const kuruldu = kurulum.data?.completed ?? false;
  const oturumVar = Boolean(jetonuAl());

  return (
    <Routes>
      <Route path="/p/:token" element={<Yayin />} />
      <Route
        path="/kurulum"
        element={kuruldu ? <Navigate to="/giris" replace /> : <Kurulum />}
      />
      <Route
        path="/giris"
        element={!kuruldu ? <Navigate to="/kurulum" replace /> : <Giris />}
      />
      {!kuruldu ? (
        <Route path="*" element={<Navigate to="/kurulum" replace />} />
      ) : !oturumVar ? (
        <Route path="*" element={<Navigate to="/giris" replace />} />
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
          <Route path="/ayarlar" element={<Ayarlar />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      )}
    </Routes>
  );
}
