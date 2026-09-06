/**
 * Deployment-environment detection for the four website hosts.
 *
 * Production is `*.kitchcu.com`; `*.kitchcu.in` and localhost are demo/QA
 * deployments where seeded credentials are deliberately visible. Vite bakes
 * `VITE_*` at build time, so the hostname is the only signal available to a
 * single bundle served from several hosts — the env var is the explicit
 * override for anything that does not follow the domain convention.
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
 * Whether seeded demo accounts (phones, OTP, dev admin password) may be
 * rendered. Off in production so the login screens never advertise seeded
 * logins to the public, on everywhere else so QA keeps one-click sign-in.
 */
export function showDemoCredentials(): boolean {
  return asBool(viteEnv("VITE_SHOW_DEMO_CREDENTIALS")) ?? !isProductionHost();
}
