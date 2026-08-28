/** Yan menüdeki dönem anahtarı. Dönem değişince tüm veriler yeniden yüklenir. */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronsUpDown, Settings2 } from "lucide-react";
import { Link } from "react-router-dom";
import clsx from "clsx";

import { get, post } from "../lib/api";
import type { Donem } from "../lib/types";

export default function DonemSecici() {
  const qc = useQueryClient();
  const [acik, setAcik] = useState(false);

  const donemler = useQuery({ queryKey: ["donemler"], queryFn: () => get<Donem[]>("/terms") });
  const sec = useMutation({
    mutationFn: (id: number) => post<Donem>(`/terms/${id}/activate`),
    onSuccess: () => {
      // Dönem değişti: önbellekteki her şey artık başka döneme ait.
      // resetQueries hem veriyi atar hem de ekrandaki sorguları yeniden çeker;
      // clear() bunu yapmaz, bağlı bileşenler eski veriyle kalır.
      qc.resetQueries();
      setAcik(false);
    },
  });

  const aktif = donemler.data?.find((d) => d.is_active);

  return (
    <div className="relative border-b border-slate-100 px-3 py-2">
      <button
        onClick={() => setAcik((a) => !a)}
        className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-slate-100"
      >
        <span className="min-w-0 flex-1">
          <span className="block text-[10px] font-medium uppercase tracking-wide text-slate-400">
            Dönem
          </span>
          <span className="block truncate text-sm font-medium text-slate-800">
            {aktif?.name ?? "—"}
          </span>
        </span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-slate-400" />
      </button>

      {acik && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setAcik(false)} />
          <div className="absolute left-3 right-3 z-20 mt-1 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
            <div className="max-h-64 overflow-y-auto py-1">
              {donemler.data?.map((d) => (
                <button
                  key={d.id}
                  onClick={() => (d.is_active ? setAcik(false) : sec.mutate(d.id))}
                  className={clsx(
                    "flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50",
                    d.is_active && "font-medium",
                  )}
                >
                  <Check
                    className={clsx(
                      "h-3.5 w-3.5 shrink-0",
                      d.is_active ? "text-slate-900" : "text-transparent",
                    )}
                  />
                  <span className="min-w-0 flex-1 truncate">{d.name}</span>
                  <span className="shrink-0 text-[10px] text-slate-400">
                    {d.counts.sube ?? 0} şube
                  </span>
                </button>
              ))}
            </div>
            <Link
              to="/donemler"
              onClick={() => setAcik(false)}
              className="flex items-center gap-2 border-t border-slate-100 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              <Settings2 className="h-3.5 w-3.5" />
              Dönemleri yönet
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
