import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Backend başka bir adreste ya da portta çalışıyorsa ortam değişkenleriyle
// yönlendirilebilir: DERSPER_API=http://127.0.0.1:8001 DERSPER_PORT=5175 npm run dev
const API = process.env.DERSPER_API ?? "http://127.0.0.1:8000";
const PORT = Number(process.env.DERSPER_PORT ?? 5173);

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: PORT,
    proxy: { "/api": { target: API, changeOrigin: true } },
  },
});
