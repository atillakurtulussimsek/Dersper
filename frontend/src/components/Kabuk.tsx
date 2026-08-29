/** Giriş yapmış kullanıcının gördüğü çerçeve: yan menü + içerik.
 *
 *  Yan menü bir ders programı sütunu gibi kurulur: solda çentikli bir ray,
 *  bölümler sıra numaralarıyla. Izgaradaki saat rayının aynısı, böylece
 *  gezinme ile veri aynı dili konuşur.
 */
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen, CalendarClock, CalendarRange, GraduationCap, LayoutGrid, LogOut,
  Settings, Table2, UserCog, Users,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import clsx from "clsx";

import DonemSecici from "./DonemSecici";
import TemaSecici from "./TemaSecici";
import { get, jetonuSil } from "../lib/api";
import type { Kurum } from "../lib/types";

const MENU = [
  { yol: "/", ad: "Özet", ikon: LayoutGrid },
  { yol: "/ogretmenler", ad: "Öğretmenler", ikon: Users },
  { yol: "/dersler", ad: "Dersler", ikon: BookOpen },
  { yol: "/subeler", ad: "Şubeler", ikon: GraduationCap },
  { yol: "/ders-atamalari", ad: "Ders Atamaları", ikon: Table2 },
  { yol: "/zaman-izgarasi", ad: "Zaman Izgarası", ikon: CalendarClock },
  { yol: "/programlar", ad: "Ders Programları", ikon: LayoutGrid },
  { yol: "/donemler", ad: "Dönemler", ikon: CalendarRange },
  { yol: "/kullanicilar", ad: "Kullanıcılar", ikon: UserCog },
  { yol: "/ayarlar", ad: "Ayarlar", ikon: Settings },
];

export default function Kabuk() {
  const navigate = useNavigate();
  const kurum = useQuery({ queryKey: ["kurum"], queryFn: () => get<Kurum>("/institution") });

  function cikis() {
    jetonuSil();
    navigate("/giris", { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-kagit">
      <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-cizgi bg-yuzey">
        <div className="border-b border-cizgi px-5 py-4">
          <p className="font-baslik text-lg font-semibold tracking-tight text-murekkep">
            Dersper
          </p>
          <p className="truncate text-xs text-murekkep-silik">
            {kurum.data?.name ?? "—"}
          </p>
        </div>

        <DonemSecici />

        {/* Ray: menü öğeleri ders saatleri gibi sıralanır. */}
        <nav className="relative flex-1 overflow-y-auto py-3 pl-5 pr-3">
          <span
            aria-hidden
            className="pointer-events-none absolute bottom-3 left-5 top-3 w-px bg-cizgi"
          />
          {MENU.map(({ yol, ad, ikon: Ikon }, i) => (
            <NavLink
              key={yol}
              to={yol}
              end={yol === "/"}
              className={({ isActive }) =>
                clsx(
                  "group relative flex items-center gap-2.5 rounded-lg py-1.5 pl-4 pr-3 text-sm transition-colors",
                  isActive
                    ? "bg-murekkep font-medium text-uzeri"
                    : "text-murekkep-yumusak hover:bg-yuzey-alt hover:text-murekkep",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {/* Çentik: aktif satırda raydan dışarı taşar. */}
                  <span
                    aria-hidden
                    className={clsx(
                      "absolute -left-0 top-1/2 h-px -translate-y-1/2 transition-all",
                      isActive
                        ? "w-3 bg-murekkep"
                        : "w-1.5 bg-cizgi-guclu group-hover:w-2.5",
                    )}
                  />
                  <span className="sayisal w-3 shrink-0 text-2xs tabular-nums opacity-50">
                    {i + 1}
                  </span>
                  <Ikon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{ad}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-2 border-t border-cizgi px-4 py-3">
          <TemaSecici />
          <button
            onClick={cikis}
            className="flex w-full items-center gap-2.5 rounded-lg px-1 py-1.5 text-sm text-murekkep-silik transition-colors hover:text-murekkep"
          >
            <LogOut className="h-4 w-4" />
            Çıkış yap
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        <div className="mx-auto max-w-[1400px] p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
