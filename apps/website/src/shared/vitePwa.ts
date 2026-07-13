import type { PluginOption } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export function kitchcuPwaPlugin(appName: string, shortName: string): PluginOption {
  return VitePWA({
    registerType: "autoUpdate",
    includeAssets: ["favicon.svg"],
    manifest: {
      name: appName,
      short_name: shortName,
      theme_color: "#e65100",
      background_color: "#121212",
      display: "standalone",
      start_url: "/",
      icons: [
        {
          src: "/favicon.svg",
          sizes: "any",
          type: "image/svg+xml",
          purpose: "any",
        },
      ],
    },
    workbox: {
      globPatterns: ["**/*.{js,css,html,svg,woff2}"],
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
