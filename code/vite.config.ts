import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { cloudflare } from "@cloudflare/vite-plugin";
import { mochaPlugins } from "@getmocha/vite-plugins";

const isVercel = process.env.VERCEL === "1";

export default defineConfig({
  plugins: isVercel
    ? [react()]
    : [
        ...mochaPlugins(process.env as Record<string, string>),
        react(),
        cloudflare(),
      ],
  server: {
    allowedHosts: true,
    proxy: {
      "/api": {
        target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 5000,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
