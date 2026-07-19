import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { kitchcuPwaPlugin } from "./src/shared/vitePwa";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

const apiProxy = {
  "/api": {
    target: "http://localhost:18000",
    changeOrigin: true,
  },
};

export default defineConfig({
  envDir: repoRoot,
  plugins: [react(), kitchcuPwaPlugin("kitchCU Customer", "kitchCU")],
  server: {
    port: 13001,
    host: true,
    proxy: apiProxy,
  },
  preview: {
    port: 13001,
    proxy: apiProxy,
  },
  build: {
    outDir: "dist/customer",
    emptyOutDir: true,
    rollupOptions: {
      input: "customer.html",
    },
  },
});
