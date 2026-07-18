/** Product branding — user-facing name, domains, and contact. */
export const APP_NAME = "kitchCU";
/** localStorage / sessionStorage key prefix (camel brand, no spaces). */
export const APP_STORAGE_PREFIX = "kitchCU";
export const APP_NAME_LOWER = "kitchcu";
/** Shown only under the logo in top chrome (BrandNavMark). Do not reuse in meta/heroes/footers. */
export const APP_TAGLINE = "A complete kitchen care unit";
/** Category-defining claim for marketing surfaces (portal / heroes / meta). */
export const APP_POSITIONING =
  "India's first — and the world's third — platform with this feature stack";
export const APP_POSITIONING_SHORT = "India's 1st · World's 3rd feature stack";
/** Registrable domain — production subdomains hang off this. */
function resolveAppDomain(): string {
  const fromEnv = (import.meta.env.VITE_APP_DOMAIN as string | undefined)?.trim();
  if (fromEnv) {
    return fromEnv.replace(/^https?:\/\//i, "").replace(/\/$/, "");
  }
  // Infer from baked app URLs (GCP builds set VITE_ADMIN_APP_URL=https://admin.kitchcu.com)
  for (const key of ["VITE_ADMIN_APP_URL", "VITE_KITCHEN_APP_URL", "VITE_CUSTOMER_APP_URL"] as const) {
    const raw = (import.meta.env[key] as string | undefined)?.trim();
    if (!raw || raw.includes("localhost")) continue;
    try {
      const host = new URL(raw).hostname.toLowerCase();
      return host.replace(/^(www|customer|kitchen|admin|api|media)\./, "");
    } catch {
      /* continue */
    }
  }
  return "kitchcu.in";
}

export const APP_DOMAIN = resolveAppDomain();

export const CUSTOMER_HOST = `customer.${APP_DOMAIN}`;
export const KITCHEN_HOST = `kitchen.${APP_DOMAIN}`;
export const ADMIN_HOST = `admin.${APP_DOMAIN}`;
export const PORTAL_HOST = APP_DOMAIN;

export const SUPPORT_EMAIL = `hello@${APP_DOMAIN}`;
export const ADMIN_DEV_EMAIL = "admin@kitchcu.dev";
/** Production bootstrap email (GCP ADMIN_EMAIL). */
export const ADMIN_PROD_EMAIL = "admin@kitchcu.com";

export const PAGE_TITLE = `${APP_NAME} — Cloud Kitchen Platform`;

/** Brand color tokens aligned with logos/ UX design */
export const BRAND_COLORS = {
  orange: "#FF6B1A",
  orangeLight: "#FF8A3D",
  teal: "#2EC4B6",
  tealDeep: "#1A9B90",
  navy: "#0B1B32",
  navyMid: "#152A45",
  flame: "#FFC107",
  cream: "#FFF8EE",
} as const;

/**
 * Static brand assets from logos/ (copied to public/brand).
 * Prefer these over plain text wordmarks in chrome UI.
 */
export const BRAND_ASSETS = {
  wordmark: "/brand/wordmark.png",
  appicon: "/brand/appicon.png",
  badge: "/brand/badge.png",
  mascot: "/brand/mascot.png",
  markCircle: "/brand/mark-circle.png",
  lockupDark: "/brand/lockup-dark.png",
  creativeChef: "/brand/creative-chef.png",
  creativeNeon: "/brand/creative-neon.png",
  creativeHero: "/brand/creative-hero.png",
} as const;

export type BrandAssetKey = keyof typeof BRAND_ASSETS;
