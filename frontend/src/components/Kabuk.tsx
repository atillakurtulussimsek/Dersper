/** Giriş yapmış kullanıcının gördüğü çerçeve: yan menü + içerik.
 *
 *  Menü, ekranların gerçekten ayrıldığı üç öbeği gösterir: önce programın
 *  beslendiği tanımlar, sonra programın kendisi, en sonda kurum yönetimi.
 *  Öbek başlıkları bilgi taşır; sıra numarası taşımazdı, o yüzden yok.
 */
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Building2, CalendarClock, CalendarRange, Gauge, GraduationCap, LayoutGrid,
  LogOut, Settings, Table2, UserCog, Users,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
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
        <div className="px-5 pb-3 pt-4">
          <p className="font-baslik text-lg font-semibold leading-none tracking-tight text-murekkep">
            Dersper
          </p>
          <p className="mt-1 truncate text-xs text-murekkep-silik">
            {kurum.data?.name ?? "—"}
          </p>
        </div>

        <DonemSecici />

        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
          {MENU.map((obek, i) => (
            <div key={obek.baslik ?? i} className="space-y-0.5">
              {obek.baslik && (
                <p className="px-3 pb-1.5 text-2xs font-semibold uppercase tracking-[0.1em] text-murekkep-silik">
                  {obek.baslik}
                </p>
              )}
              {obek.girdiler.map(({ yol, ad, ikon: Ikon }) => (
                <NavLink
                  key={yol}
                  to={yol}
                  end={yol === "/"}
                  className={({ isActive }) =>
                    clsx(
                      "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-murekkep font-medium text-uzeri"
                        : "text-murekkep-yumusak hover:bg-yuzey-alt hover:text-murekkep",
                    )
                  }
                >
                  <Ikon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{ad}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="space-y-2 border-t border-cizgi px-4 py-3">
          <div className="flex items-center justify-between gap-2">
            <TemaSecici />
            <span
              title={`Dersper ${__SURUM__}`}
              className="sayisal shrink-0 font-mono text-[11px] text-murekkep-silik"
            >
              v{__SURUM__}
            </span>
          </div>
          <button
            onClick={cikis}
            className="flex w-full items-center gap-2.5 rounded-lg px-1 py-2 text-sm text-murekkep-silik transition-colors hover:text-murekkep"
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
