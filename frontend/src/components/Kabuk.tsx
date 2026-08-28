/** Giriş yapmış kullanıcının gördüğü çerçeve: yan menü + içerik. */
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen, CalendarClock, CalendarRange, GraduationCap, LayoutGrid, LogOut,
  Settings, Table2, Users,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import clsx from "clsx";

import DonemSecici from "./DonemSecici";
import { get, jetonuSil } from "../lib/api";
import type { Kurum } from "../lib/types";

const MENU = [
  { yol: "/", ad: "Özet", ikon: LayoutGrid },
  { yol: "/ogretmenler", ad: "Öğretmenler", ikon: Users },
  { yol: "/dersler", ad: "Dersler", ikon: BookOpen },
  { yol: "/subeler", ad: "Şubeler", ikon: GraduationCap },
  { yol: "/mufredat", ad: "Müfredat", ikon: Table2 },
  { yol: "/zaman-izgarasi", ad: "Zaman Izgarası", ikon: CalendarClock },
  { yol: "/programlar", ad: "Ders Programları", ikon: LayoutGrid },
  { yol: "/donemler", ad: "Dönemler", ikon: CalendarRange },
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
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-100 px-5 py-4">
          <p className="text-lg font-semibold tracking-tight text-slate-900">Dersper</p>
          <p className="truncate text-xs text-slate-500">{kurum.data?.name ?? "—"}</p>
        </div>

        <DonemSecici />

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {MENU.map(({ yol, ad, ikon: Ikon }) => (
            <NavLink
              key={yol}
              to={yol}
              end={yol === "/"}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-slate-900 font-medium text-white"
                    : "text-slate-600 hover:bg-slate-100",
                )
              }
            >
              <Ikon className="h-4 w-4" />
              {ad}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={cikis}
          className="flex items-center gap-2.5 border-t border-slate-100 px-6 py-3.5 text-sm text-slate-600 hover:bg-slate-50"
        >
          <LogOut className="h-4 w-4" />
          Çıkış yap
        </button>
      </aside>

      <main className="flex-1 overflow-x-hidden">
        <div className="mx-auto max-w-[1400px] p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
