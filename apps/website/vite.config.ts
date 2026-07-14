import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxy = {
  "/api": {
    target: "http://localhost:18000",
    changeOrigin: true,
  },
  "/openapi.json": {
    target: "http://localhost:18000",
    changeOrigin: true,
  },
  "/docs": {
    target: "http://localhost:18000",
    changeOrigin: true,
  },
  "/redoc": {
    target: "http://localhost:18000",
    changeOrigin: true,
  },
};

/** kitchCU portal homepage — choose customer.kitchcu.in or kitchen.kitchcu.in (port 13000) */
export default defineConfig({
  plugins: [react()],
  server: {
    port: 13000,
    strictPort: true,
    host: true,
    proxy: apiProxy,
  },
  preview: {
    port: 13000,
    proxy: apiProxy,
  },
  build: {
    outDir: "dist/portal",
    emptyOutDir: true,
    rollupOptions: {
      input: "index.html",
    },
  },
});
