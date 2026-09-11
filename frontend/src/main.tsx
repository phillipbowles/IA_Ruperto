import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App";
import "./estilos.css";

const cliente = new QueryClient({
  defaultOptions: {
    queries: {
      // La placa manda cada 5 min en régimen normal; refrescar cada 30 s alcanza
      // para que el panel se sienta en vivo sin castigar a la API.
      refetchInterval: 30_000,
      retry: 1,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={cliente}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
