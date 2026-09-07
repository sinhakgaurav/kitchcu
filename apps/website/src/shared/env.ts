/**
 * Deployment-environment detection for the four website hosts.
 *
 * Production is `*.kitchcu.com`. Vite bakes `VITE_*` at build time; hostname
 * still gates a few production-only strings (admin email). Demo owner/customer
 * phones are shown on Sign in unless `VITE_SHOW_DEMO_CREDENTIALS=0`.
 */

const PRODUCTION_APEX = "kitchcu.com";

function viteEnv(key: string): string | undefined {
  const value = (import.meta.env as Record<string, string | undefined>)[key];
  return value === undefined || value === "" ? undefined : value;
}

function asBool(value: string | undefined): boolean | undefined {
  if (value === undefined) return undefined;
  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  return undefined;
}

/** True on the live `*.kitchcu.com` deployment. */
export function isProductionHost(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname.toLowerCase();
  return host === PRODUCTION_APEX || host.endsWith(`.${PRODUCTION_APEX}`);
}

/**
 * Whether seeded demo accounts (phones, OTP) are printed on kitchen and
 * customer Sign in. On by default, including `*.kitchcu.com`. Set
 * `VITE_SHOW_DEMO_CREDENTIALS=0` at build time to hide them.
 */
export function showDemoCredentials(): boolean {
  return asBool(viteEnv("VITE_SHOW_DEMO_CREDENTIALS")) ?? true;
}
