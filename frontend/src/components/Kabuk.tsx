/** Giriş yapmış kullanıcının gördüğü çerçeve: yan menü + üst çubuk + içerik.
 *
 *  Düzen Metronic 8'in "dark sidebar" şablonudur. Metronic'in kendi JavaScript
 *  paketi yüklenmez — düzenin tamamı CSS ve `data-kt-app-*` öznitelikleriyle
 *  çalışır, etkileşimi (mobil çekmece, daraltma) React yürütür. Böylece jQuery
 *  ve Bootstrap JS React'in DOM'una karışmaz.
 *
 *  Menü, ekranların gerçekten ayrıldığı üç öbeği gösterir: önce programın
 *  beslendiği tanımlar, sonra programın kendisi, en sonda kurum yönetimi.
 */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen, Building2, CalendarClock, CalendarRange, ChevronLeft, Gauge,
  GraduationCap, LayoutGrid, LogOut, Menu, Settings, Table2, UserCog, Users,
} from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import clsx from "clsx";

import DonemSecici from "./DonemSecici";
import TemaSecici from "./TemaSecici";
import { get, jetonuSil } from "../lib/api";
import type { Kurum } from "../lib/types";

type Girdi = { yol: string; ad: string; ikon: typeof Gauge };
type Obek = { baslik?: string; girdiler: Girdi[] };

const MENU: Obek[] = [
  {
    girdiler: [{ yol: "/", ad: "Özet", ikon: Gauge }],
  },
  {
    baslik: "Tanımlar",
    girdiler: [
      { yol: "/ogretmenler", ad: "Öğretmenler", ikon: Users },
      { yol: "/dersler", ad: "Dersler", ikon: BookOpen },
      { yol: "/subeler", ad: "Şubeler", ikon: GraduationCap },
      { yol: "/ders-atamalari", ad: "Ders Atamaları", ikon: Table2 },
      { yol: "/zaman-izgarasi", ad: "Zaman Izgarası", ikon: CalendarClock },
    ],
  },
  {
    baslik: "Program",
    girdiler: [{ yol: "/programlar", ad: "Ders Programları", ikon: LayoutGrid }],
  },
  {
    baslik: "Kurum",
    girdiler: [
      { yol: "/binalar", ad: "Binalar", ikon: Building2 },
      { yol: "/donemler", ad: "Dönemler", ikon: CalendarRange },
      { yol: "/kullanicilar", ad: "Kullanıcılar", ikon: UserCog },
      { yol: "/ayarlar", ad: "Ayarlar", ikon: Settings },
    ],
  },
];

const DARALT_ANAHTARI = "dersper_menu_dar";

// Metronic'te yan menü lg altında çekmeceye döner; bu sınıflar masaüstünde
// uygulanırsa menü ekran dışında kalır. Kırılma noktası Bootstrap'ın lg'si.
const CEKMECE_SORGUSU = "(max-width: 991.98px)";

function useCekmeceModu(): boolean {
  const [kucuk, setKucuk] = useState(
    () => window.matchMedia?.(CEKMECE_SORGUSU).matches ?? false,
  );
  useEffect(() => {
    const mq = window.matchMedia(CEKMECE_SORGUSU);
    const uygula = () => setKucuk(mq.matches);
    uygula();
    mq.addEventListener("change", uygula);
    return () => mq.removeEventListener("change", uygula);
  }, []);
  return kucuk;
}

export default function Kabuk() {
  const navigate = useNavigate();
  const konum = useLocation();
  const kurum = useQuery({ queryKey: ["kurum"], queryFn: () => get<Kurum>("/institution") });

  const cekmece = useCekmeceModu();
  const [mobilAcik, setMobilAcik] = useState(false);
  const [dar, setDar] = useState(() => {
    try {
      return localStorage.getItem(DARALT_ANAHTARI) === "1";
    } catch {
      // Gizli sekmede erişim hata verebilir; geniş menüyle başlarız.
      return false;
    }
  });

  // Daraltma Metronic'te gövde özniteliğiyle yürür; CSS gerisini halleder.
  useEffect(() => {
    document.body.setAttribute("data-kt-app-sidebar-minimize", dar ? "on" : "off");
    try {
      localStorage.setItem(DARALT_ANAHTARI, dar ? "1" : "0");
    } catch {
      // Saklanamazsa yalnızca bu oturumda geçerli olur.
    }
  }, [dar]);

  // Mobilde bir bağlantıya basıldığında çekmece açık kalmamalı.
  useEffect(() => setMobilAcik(false), [konum.pathname]);

  function cikis() {
    jetonuSil();
    navigate("/giris", { replace: true });
  }

  return (
    <div className="d-flex flex-column flex-root app-root">
      <div className="app-page flex-column flex-column-fluid">
        {/* Üst çubuk: kurum kimliği solda, dönem ve tema sağda. */}
        <div className="app-header">
          <div className="app-container container-fluid d-flex align-items-stretch justify-content-between">
            <div className="d-flex align-items-center d-lg-none ms-n2 me-2">
              <button
                type="button"
                onClick={() => setMobilAcik(true)}
                className="btn btn-icon btn-active-color-primary w-35px h-35px"
                aria-label="Menüyü aç"
              >
                <Menu className="h-5 w-5" />
              </button>
            </div>

            <div className="d-flex align-items-center flex-grow-1 min-w-0">
              <span className="fs-6 fw-semibold text-gray-800 text-truncate">
                {kurum.data?.name ?? "—"}
              </span>
            </div>

            <div className="d-flex align-items-center gap-2 gap-md-3 flex-shrink-0">
              <DonemSecici />
              <TemaSecici />
            </div>
          </div>
        </div>

        <div className="app-wrapper flex-column flex-row-fluid">
          {/* Yan menü. Mobilde Metronic'in çekmece sınıflarıyla açılır. */}
          <div
            className={clsx(
              "app-sidebar flex-column",
              cekmece && "drawer drawer-start",
              cekmece && mobilAcik && "drawer-on",
            )}
          >
            <div className="app-sidebar-logo px-6">
              <NavLink to="/" className="d-flex align-items-center gap-3 text-decoration-none">
                <span className="symbol symbol-35px">
                  <span className="symbol-label bg-primary text-inverse-primary fw-bold fs-5">
                    D
                  </span>
                </span>
                <span className="app-sidebar-logo-default fs-4 fw-bold text-white">
                  Dersper
                </span>
              </NavLink>

              <button
                type="button"
                onClick={() => setDar((d) => !d)}
                aria-label={dar ? "Menüyü genişlet" : "Menüyü daralt"}
                aria-expanded={!dar}
                className={clsx(
                  "app-sidebar-toggle btn btn-icon btn-shadow btn-sm btn-color-muted",
                  "btn-active-color-primary body-bg h-30px w-30px position-absolute",
                  "top-50 start-100 translate-middle d-none d-lg-flex",
                )}
              >
                <ChevronLeft className={clsx("h-4 w-4 transition-transform", dar && "rotate-180")} />
              </button>
            </div>

            <div className="app-sidebar-menu overflow-hidden flex-column-fluid">
              <div className="app-sidebar-wrapper hover-scroll-overlay-y my-5">
                <div className="menu menu-column menu-rounded menu-sub-indention px-3">
                  {MENU.map((obek, i) => (
                    <div key={obek.baslik ?? i}>
                      {obek.baslik && (
                        <div className="menu-item pt-5">
                          <div className="menu-content">
                            <span className="menu-heading fw-bold text-uppercase fs-7">
                              {obek.baslik}
                            </span>
                          </div>
                        </div>
                      )}
                      {obek.girdiler.map(({ yol, ad, ikon: Ikon }) => (
                        <div key={yol} className="menu-item">
                          <NavLink
                            to={yol}
                            end={yol === "/"}
                            className={({ isActive }) =>
                              clsx("menu-link", isActive && "active")
                            }
                          >
                            <span className="menu-icon">
                              <Ikon className="h-5 w-5" />
                            </span>
                            <span className="menu-title">{ad}</span>
                          </NavLink>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="app-sidebar-footer flex-column-auto pt-2 pb-6 px-6">
              <button
                onClick={cikis}
                className="btn btn-flex flex-center btn-custom overflow-hidden text-nowrap px-0 h-40px w-100"
                title={`Dersper ${__SURUM__}`}
              >
                <LogOut className="h-4 w-4" />
                <span className="btn-label ms-2">Çıkış yap</span>
              </button>
              <div className="app-sidebar-logo-default text-center pt-3">
                <span className="sayisal font-mono text-2xs text-gray-600">
                  v{__SURUM__}
                </span>
              </div>
            </div>
          </div>

          {/* Mobil çekmece perdesi. */}
          {cekmece && mobilAcik && (
            <div className="drawer-overlay" onClick={() => setMobilAcik(false)} />
          )}

          <div className="app-main flex-column flex-row-fluid">
            <div className="d-flex flex-column flex-column-fluid">
              <div className="app-content flex-column-fluid">
                <div className="app-container container-fluid">
                  <Outlet />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
