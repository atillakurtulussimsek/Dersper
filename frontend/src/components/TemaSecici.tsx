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
    <div className="btn-group btn-group-sm" role="group" aria-label="Tema">
      {SECENEKLER.map(({ id, etiket, ikon: Ikon }) => (
        <button
          key={id}
          type="button"
          onClick={() => setTema(id)}
          title={etiket}
          aria-label={etiket}
          aria-pressed={tema === id}
          className={clsx(
            "btn btn-icon btn-sm",
            tema === id ? "btn-primary" : "btn-light",
          )}
        >
          <Ikon className="h-3.5 w-3.5" />
        </button>
      ))}
    </div>
  );
}
