import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Backend port defaults to 8000 (matches docker-compose.yml). Override with
// STS2_BACKEND_PORT when running the server on a different port locally.
const backendPort = process.env.STS2_BACKEND_PORT || "8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    headers: {
      "Cache-Control": "no-store",
    },
    watch: {
      // Ensure tailwind config changes trigger rebuild
      ignored: ["!**/tailwind.config.*"],
    },
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      },
      "/ws": {
        target: `ws://127.0.0.1:${backendPort}`,
        ws: true,
      },
    },
  },
});
