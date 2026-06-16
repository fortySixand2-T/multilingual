import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// SPA dev server. `/api/*` is proxied to the FastAPI backend so there's no CORS
// fuss and the same code runs in prod behind a reverse proxy. Override the
// backend target with VITE_API_TARGET if it isn't on :9000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://localhost:9000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
