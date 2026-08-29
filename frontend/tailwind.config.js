/** @type {import('tailwindcss').Config} */

// Belirteçler CSS değişkenlerinden gelir (bkz. src/index.css); burada yalnızca
// Tailwind yardımcılarına bağlanır. Alfa desteklensin diye kanal biçimi kullanılır.
const renk = (ad) => `rgb(var(--${ad}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        kagit: renk("kagit"),
        yuzey: renk("yuzey"),
        "yuzey-alt": renk("yuzey-alt"),
        cizgi: renk("cizgi"),
        "cizgi-guclu": renk("cizgi-guclu"),
        murekkep: renk("murekkep"),
        "murekkep-yumusak": renk("murekkep-yumusak"),
        "murekkep-silik": renk("murekkep-silik"),
        uzeri: renk("uzeri"),
        basari: renk("basari"),
        "basari-zemin": renk("basari-zemin"),
        uyari: renk("uyari"),
        "uyari-zemin": renk("uyari-zemin"),
        hata: renk("hata"),
        "hata-zemin": renk("hata-zemin"),
      },
      fontFamily: {
        // Başlıklar ve büyük sayılar: karakterli, değişken genişlikli grotesk.
        baslik: ['"Bricolage Grotesque Variable"', "system-ui", "sans-serif"],
        // Arayüz: yoğun ekranlar için tasarlanmış, Türkçe kapsamı tam.
        sans: ['"IBM Plex Sans Variable"', "system-ui", "sans-serif"],
        // Veri: saatler, ders sırası, blok desenleri, kısa kodlar.
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      transitionTimingFunction: {
        yumusak: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
    },
  },
  plugins: [],
};
