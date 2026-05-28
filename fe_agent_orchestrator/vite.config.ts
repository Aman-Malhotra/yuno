import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// Local backend port — keep in sync with backend/Dockerfile. Override in your
// shell if you run the backend somewhere else.
const BACKEND_DEV_TARGET = process.env.VITE_BACKEND_DEV_TARGET ?? "http://localhost:3001";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    strictPort: true,
    proxy: {
      "/api": {
        target: BACKEND_DEV_TARGET,
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 3000,
    strictPort: true,
  },
});
