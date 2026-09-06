import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { spaIndex } from "./viteSpaIndex";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

const apiProxy = {
  "/api": {
    target: "http://localhost:18000",
    changeOrigin: true,
  },
};

export default defineConfig({
  envDir: repoRoot,
  plugins: [react(), spaIndex("admin.html")],
  server: {
    port: 13003,
    strictPort: true,
    host: true,
    proxy: apiProxy,
  },
  preview: {
    port: 13003,
    proxy: apiProxy,
  },
  build: {
    outDir: "dist/admin",
    emptyOutDir: true,
    rollupOptions: {
      input: "admin.html",
    },
  },
});
