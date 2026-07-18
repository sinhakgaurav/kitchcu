/**
 * Platform theme management — apply once per app entry (main.tsx).
 *
 * All four apps (portal, customer, kitchen, admin) run the light brand
 * surface — a single professional, eye-catchy light theme across
 * marketing pages, auth, and ops dashboards. "ops-dark" is kept as a
 * dormant option in case a future user preference (e.g. an in-app dark
 * mode toggle) needs it, but no app entry point applies it today.
 */
export type AppTheme = "brand-light" | "ops-dark";

const THEME_CLASSES = ["theme-brand-light", "theme-ops-dark"] as const;

export function applyAppTheme(theme: AppTheme): void {
  const root = document.documentElement;
  for (const cls of THEME_CLASSES) {
    root.classList.remove(cls);
  }
  if (theme === "brand-light") {
    root.classList.add("theme-brand-light");
  } else {
    root.classList.add("theme-ops-dark");
  }
  root.dataset.theme = theme;
}
