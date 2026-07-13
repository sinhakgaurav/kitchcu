/** Cross-app URLs — customer.kitchCU.in / kitchen.kitchCU.in / admin.kitchCU.in */

const DEV_PORTS = { customer: 13001, kitchen: 13002, admin: 13003, portal: 13000 } as const;

function stripAppPrefix(hostname: string): string {
  let base = hostname;
  if (base.startsWith("www.")) base = base.slice(4);
  if (base.startsWith("customer.") || base.startsWith("kitchen.") || base.startsWith("admin.")) {
    base = base.split(".").slice(1).join(".");
  }
  return base;
}

/** Resolve base URL for customer or kitchen app (full origin, no trailing slash). */
export function resolveAppUrl(
  envValue: string | undefined,
  app: keyof typeof DEV_PORTS,
): string {
  const localhostFallback = `http://localhost:${DEV_PORTS[app]}`;
  const env = envValue?.replace(/\/$/, "") ?? "";

  if (typeof window === "undefined") {
    return env || localhostFallback;
  }

  const { protocol, hostname } = window.location;

  // Built-in prod URLs from env (e.g. https://customer.kitchCU.in)
  if (env && !env.includes("localhost") && !env.includes("127.0.0.1")) {
    return env;
  }

  // Local dev — ports 13001 / 13002
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return env || localhostFallback;
  }

  // Same registrable domain — use subdomains (customer.example.com, kitchen.example.com)
  const base = stripAppPrefix(hostname);
  if (base.includes(".")) {
    return `${protocol}//${app}.${base}`;
  }

  return env || localhostFallback;
}

export const CUSTOMER_APP_URL =
  import.meta.env.VITE_CUSTOMER_APP_URL ?? "http://localhost:13001";

export const KITCHEN_APP_URL =
  import.meta.env.VITE_KITCHEN_APP_URL ?? "http://localhost:13002";

export const ADMIN_APP_URL =
  import.meta.env.VITE_ADMIN_APP_URL ?? "http://localhost:13003";

export function adminUrl(path = "/"): string {
  const base = resolveAppUrl(ADMIN_APP_URL, "admin" as keyof typeof DEV_PORTS);
  return path.startsWith("/") ? `${base}${path}` : `${base}/${path}`;
}

export function customerUrl(path = "/"): string {
  const base = resolveAppUrl(CUSTOMER_APP_URL, "customer");
  return path.startsWith("/") ? `${base}${path}` : `${base}/${path}`;
}

export function kitchenUrl(path = "/"): string {
  const base = resolveAppUrl(KITCHEN_APP_URL, "kitchen");
  return path.startsWith("/") ? `${base}${path}` : `${base}/${path}`;
}

/** Navigate to another kitchCU app (full page — required for cross-subdomain). */
export function goToCustomer(path = "/"): void {
  window.location.assign(customerUrl(path));
}

export function goToKitchen(path = "/"): void {
  window.location.assign(kitchenUrl(path));
}
