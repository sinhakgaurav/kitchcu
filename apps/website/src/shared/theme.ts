/**
 * Platform theme management — apply once per app entry (main.tsx).
 *
 * - Marketing (portal, customer): light brand surface
 * - Ops (kitchen PWA after login, admin): dark dashboard shell
 * - Kitchen marketing landing shares the kitchen app; ops routes use
 *   owner-app / dashboard-shell without flipping the marketing theme.
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
