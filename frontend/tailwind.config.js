/** @type {import('tailwindcss').Config} */

// Belirteçler CSS değişkenlerinden gelir (bkz. src/index.css); burada yalnızca
// Tailwind yardımcılarına bağlanır. Alfa desteklensin diye kanal biçimi kullanılır.
const renk = (ad) => `rgb(var(--${ad}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // Koyu tema Metronic ile ortak öznitelik üzerinden açılır.
  darkMode: ["selector", '[data-theme="dark"]'],
  // Metronic kendi temel stillerini (Bootstrap reboot) getirir; Tailwind'in
  // preflight'ı onunla çakışır ve .btn/.card/.table gibi bileşenleri bozar.
  corePlugins: { preflight: false },
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
        vurgu: renk("vurgu"),
        "vurgu-zemin": renk("vurgu-zemin"),
        basari: renk("basari"),
        "basari-zemin": renk("basari-zemin"),
        uyari: renk("uyari"),
        "uyari-zemin": renk("uyari-zemin"),
        hata: renk("hata"),
        "hata-zemin": renk("hata-zemin"),
      },
      fontFamily: {
        // Metronic tek bir arayüz yazı tipi kullanır; başlık/gövde ayrımı
        // ağırlık ve punto ile yapılır.
        baslik: ["var(--yazi-arayuz)"],
        sans: ["var(--yazi-arayuz)"],
        mono: ["var(--yazi-veri)"],
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      borderRadius: {
        // Metronic'in bileşen yarıçapları.
        md: "0.475rem",
        lg: "0.625rem",
        xl: "0.625rem",
      },
      transitionTimingFunction: {
        yumusak: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
    },
  },
  plugins: [],
};
