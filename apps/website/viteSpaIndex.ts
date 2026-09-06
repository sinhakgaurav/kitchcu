import type { Plugin } from "vite";

/**
 * Serve the app HTML for React Router paths in local Vite.
 *
 * Kitchen/customer/admin builds use `kitchen.html` / `customer.html` / `admin.html`
 * as the nginx index. Vite's default is still `index.html` (portal), so `/login`
 * on those ports would otherwise load the portal. Rewrite extension-less routes
 * to the host HTML so local QA matches production.
 */
export function spaIndex(htmlFile: string): Plugin {
  return {
    name: `spa-index-${htmlFile}`,
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const incoming = req as { url?: string };
        const url = incoming.url ?? "";
        const pathOnly = url.split("?")[0] ?? "";
        if (
          pathOnly.startsWith("/api") ||
          pathOnly.startsWith("/@") ||
          pathOnly.startsWith("/src/") ||
          pathOnly.startsWith("/node_modules") ||
          pathOnly.startsWith("/media/") ||
          pathOnly.startsWith("/brand/") ||
          /\.[a-zA-Z0-9]+$/.test(pathOnly)
        ) {
          next();
          return;
        }
        incoming.url = `/${htmlFile}${url.slice(pathOnly.length)}`;
        next();
      });
    },
  };
}
