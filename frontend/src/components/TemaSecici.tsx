/** Tema anahtarı: açık / koyu / sistem. */
import { Monitor, Moon, Sun } from "lucide-react";
import clsx from "clsx";

import { useTema, type Tema } from "../lib/tema";

const SECENEKLER: { id: Tema; etiket: string; ikon: typeof Sun }[] = [
  { id: "acik", etiket: "Açık tema", ikon: Sun },
  { id: "koyu", etiket: "Koyu tema", ikon: Moon },
  { id: "sistem", etiket: "Sistemi izle", ikon: Monitor },
];

export default function TemaSecici() {
  const { tema, setTema } = useTema();

  return (
    <div
      className="flex gap-0.5 rounded-lg border border-cizgi bg-yuzey-alt p-0.5"
      role="group"
      aria-label="Tema"
    >
      {SECENEKLER.map(({ id, etiket, ikon: Ikon }) => (
        <button
          key={id}
          onClick={() => setTema(id)}
          title={etiket}
          aria-label={etiket}
          aria-pressed={tema === id}
          className={clsx(
            "rounded-md p-1.5 transition-colors",
            tema === id
              ? "bg-yuzey text-murekkep shadow-sm"
              : "text-murekkep-silik hover:text-murekkep",
          )}
        >
          <Ikon className="h-3.5 w-3.5" />
        </button>
      ))}
    </div>
  );
}
