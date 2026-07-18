import type { PluginOption } from "vite";
import { VitePWA } from "vite-plugin-pwa";

/** Inline brand hex so Vite config load does not import brand.ts (which resolves domains via env). */
const PWA_THEME = { orange: "#FF6B1A", navy: "#0B1B32" } as const;

export function kitchcuPwaPlugin(appName: string, shortName: string): PluginOption {
  return VitePWA({
    registerType: "autoUpdate",
    includeAssets: ["favicon.png", "brand/appicon.png", "brand/wordmark.png"],
    manifest: {
      name: appName,
      short_name: shortName,
      theme_color: PWA_THEME.orange,
      background_color: PWA_THEME.navy,
      display: "standalone",
      start_url: "/",
      icons: [
        {
          src: "/brand/appicon.png",
          sizes: "768x768",
          type: "image/png",
          purpose: "any",
        },
        {
          src: "/brand/appicon.png",
          sizes: "768x768",
          type: "image/png",
          purpose: "maskable",
        },
        {
          src: "/favicon.png",
          sizes: "192x192",
          type: "image/png",
          purpose: "any",
        },
      ],
    },
    workbox: {
      globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
      runtimeCaching: [
        {
          urlPattern: ({ url }) => url.pathname.includes("/menu"),
          handler: "NetworkFirst",
          options: {
            cacheName: "kitchcu-menu",
            expiration: { maxEntries: 32, maxAgeSeconds: 300 },
          },
        },
      ],
    },
  });
}
