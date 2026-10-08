import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "./src") },
  },
  // Main bundle is ~540KB (React, router, Base UI, Motion); chart/map pages are split out.
  build: { chunkSizeWarningLimit: 600 },
  server: {
    proxy: { "/api": "http://localhost:8502" },
  },
});
