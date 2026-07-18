import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api calls to the FastAPI backend during development so the frontend
// can call relative URLs and avoid CORS quirks.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
