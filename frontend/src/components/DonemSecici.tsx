/** Üst çubuktaki dönem anahtarı. Dönem değişince tüm veriler yeniden yüklenir. */
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
    <div className="relative">
      <button
        onClick={() => setAcik((a) => !a)}
        aria-expanded={acik}
        className="btn btn-sm btn-light d-flex align-items-center gap-2"
      >
        <span className="text-muted fs-8 text-uppercase d-none d-md-inline">Dönem</span>
        <span className="fw-semibold text-truncate" style={{ maxWidth: "12rem" }}>
          {aktif?.name ?? "—"}
        </span>
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 opacity-50" />
      </button>

      {acik && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setAcik(false)} />
          <div className="menu menu-sub menu-sub-dropdown menu-column show absolute right-0 top-full z-20 mt-2 w-64 py-0">
            <div className="max-h-64 overflow-y-auto py-2">
              {donemler.data?.map((d) => (
                <div key={d.id} className="menu-item px-3">
                  <button
                    onClick={() => (d.is_active ? setAcik(false) : sec.mutate(d.id))}
                    className={clsx("menu-link px-3 w-100", d.is_active && "active")}
                  >
                    <Check
                      className={clsx(
                        "h-3.5 w-3.5 shrink-0 me-2",
                        d.is_active ? "opacity-100" : "opacity-0",
                      )}
                    />
                    <span className="min-w-0 flex-1 truncate text-start">{d.name}</span>
                    <span className="badge badge-light-primary ms-2 flex-shrink-0">
                      {d.counts.sube ?? 0} şube
                    </span>
                  </button>
                </div>
              ))}
            </div>
            <div className="separator" />
            <div className="menu-item px-3 py-2">
              <Link to="/donemler" onClick={() => setAcik(false)} className="menu-link px-3">
                <Settings2 className="h-3.5 w-3.5 me-2" />
                Dönemleri yönet
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
