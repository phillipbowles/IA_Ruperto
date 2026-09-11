import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Sin host 0.0.0.0 el dev server solo escucha dentro del contenedor y el
    // navegador del host no lo alcanza.
    host: true,
    port: 5173,
    // El polling del watcher es necesario cuando el código entra por un bind
    // mount: los eventos inotify del host no siempre cruzan al contenedor.
    watch: { usePolling: true },
    proxy: {
      // El front pega a rutas relativas (/api/...) y el proxy las manda al
      // backend. Así el mismo código anda en dev y en prod sin variables de
      // entorno con la URL de la API.
      "/api": {
        target: process.env.VITE_API_URL ?? "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
});
