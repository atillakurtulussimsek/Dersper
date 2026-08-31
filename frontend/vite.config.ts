import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import path from "node:path";

// Sürüm numarasının tek kaynağı package.json. Derleme sırasında gömülür;
// arayüz `__SURUM__` olarak okur. Dosyadan okumak, tip ayarlarından bağımsız
// olduğu için hem geliştirmede hem Docker derlemesinde aynı çalışır.
const paket = JSON.parse(
  readFileSync(new URL("./package.json", import.meta.url), "utf8"),
) as { version: string };

// Backend başka bir adreste ya da portta çalışıyorsa ortam değişkenleriyle
// yönlendirilebilir: DERSPER_API=http://127.0.0.1:8001 DERSPER_PORT=5175 npm run dev
const API = process.env.DERSPER_API ?? "http://127.0.0.1:8000";
const PORT = Number(process.env.DERSPER_PORT ?? 5173);

export default defineConfig({
  define: { __SURUM__: JSON.stringify(paket.version) },
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: PORT,
    proxy: { "/api": { target: API, changeOrigin: true } },
  },
});
