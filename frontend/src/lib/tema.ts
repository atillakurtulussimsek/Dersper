/** Açık / koyu tema. Seçim tarayıcıda saklanır, varsayılan koyudur. */
import { useEffect, useState } from "react";

export type Tema = "acik" | "koyu" | "sistem";

const ANAHTAR = "dersper_tema";
export const VARSAYILAN: Tema = "koyu";

export function kayitliTema(): Tema {
  try {
    const t = localStorage.getItem(ANAHTAR);
    if (t === "acik" || t === "koyu" || t === "sistem") return t;
  } catch {
    // Gizli sekmede localStorage erişimi hata verebilir; varsayılana düşeriz.
  }
  return VARSAYILAN;
}

/** Seçim "sistem" ise işletim sisteminin tercihine bakar. */
export function koyuMu(tema: Tema): boolean {
  if (tema === "sistem") {
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
  }
  return tema === "koyu";
}

export function temayiUygula(tema: Tema): void {
  const koyu = koyuMu(tema);
  document.documentElement.classList.toggle("koyu", koyu);
  // Tarayıcının kendi bileşenleri (kaydırma çubuğu, tarih seçici) de uysun.
  document.documentElement.style.colorScheme = koyu ? "dark" : "light";
}

export function useTema() {
  const [tema, setTema] = useState<Tema>(kayitliTema);

  useEffect(() => {
    temayiUygula(tema);
    try {
      localStorage.setItem(ANAHTAR, tema);
    } catch {
      // Saklanamazsa da tema uygulanmış olur; sonraki açılışta varsayılana döner.
    }
  }, [tema]);

  // "Sistem" seçiliyken işletim sistemi tercihi değişirse anında uy.
  useEffect(() => {
    if (tema !== "sistem") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const uygula = () => temayiUygula("sistem");
    mq.addEventListener("change", uygula);
    return () => mq.removeEventListener("change", uygula);
  }, [tema]);

  return { tema, setTema };
}
