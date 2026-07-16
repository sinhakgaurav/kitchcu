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
export const APP_DOMAIN = "kitchcu.in";

export const CUSTOMER_HOST = `customer.${APP_DOMAIN}`;
export const KITCHEN_HOST = `kitchen.${APP_DOMAIN}`;
export const ADMIN_HOST = `admin.${APP_DOMAIN}`;
export const PORTAL_HOST = APP_DOMAIN;

export const SUPPORT_EMAIL = "hello@kitchcu.in";
export const ADMIN_DEV_EMAIL = "admin@kitchcu.dev";

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
