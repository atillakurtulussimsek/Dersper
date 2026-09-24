import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { senkronBasla } from "./lib/senkron";
import "./index.css";

// Sekmeye/pencereye dönünce veriler tazelenir: zaman ızgarası bir sekmede
// değişince öbür sekmedeki program sayfası da ona uyar. Sürekli yoklanan
// sorgular kendi aralığını zaten kullanır; odak tazelemesi onlara ek yük değil.
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true } },
});
senkronBasla(queryClient);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
