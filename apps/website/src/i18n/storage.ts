import { APP_STORAGE_PREFIX } from "../shared/brand";
import { DEFAULT_LOCALE, isLocaleCode, type LocaleCode } from "./languages";

const LOCALE_KEY = `${APP_STORAGE_PREFIX}_locale`;
const CHOSEN_KEY = `${APP_STORAGE_PREFIX}_locale_chosen`;

function cookieDomainAttr(): string {
  if (typeof window === "undefined") return "";
  const host = window.location.hostname;
  if (host === "kitchcu.com" || host.endsWith(".kitchcu.com")) return "; Domain=.kitchcu.com";
  if (host === "kitchcu.in" || host.endsWith(".kitchcu.in")) return "; Domain=.kitchcu.in";
  return "";
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function writeCookie(name: string, value: string): void {
  if (typeof document === "undefined") return;
  const maxAge = 60 * 60 * 24 * 365;
  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAge}; SameSite=Lax${cookieDomainAttr()}`;
}

export function readStoredLocale(): LocaleCode | null {
  try {
    const fromLs = localStorage.getItem(LOCALE_KEY);
    if (isLocaleCode(fromLs)) return fromLs;
  } catch {
    /* private mode */
  }
  const fromCookie = readCookie(LOCALE_KEY);
  return isLocaleCode(fromCookie) ? fromCookie : null;
}

export function hasChosenLocale(): boolean {
  try {
    if (localStorage.getItem(CHOSEN_KEY) === "1") return true;
  } catch {
    /* ignore */
  }
  return readCookie(CHOSEN_KEY) === "1";
}

export function persistLocaleChoice(code: LocaleCode): void {
  try {
    localStorage.setItem(LOCALE_KEY, code);
    localStorage.setItem(CHOSEN_KEY, "1");
  } catch {
    /* private mode */
  }
  writeCookie(LOCALE_KEY, code);
  writeCookie(CHOSEN_KEY, "1");
  if (typeof document !== "undefined") {
    document.documentElement.lang = code;
  }
}

export function clearLocaleChoice(): void {
  try {
    localStorage.removeItem(LOCALE_KEY);
    localStorage.removeItem(CHOSEN_KEY);
  } catch {
    /* ignore */
  }
  if (typeof document !== "undefined") {
    const maxAge = 0;
    const domain = cookieDomainAttr();
    document.cookie = `${LOCALE_KEY}=; Path=/; Max-Age=${maxAge}${domain}`;
    document.cookie = `${CHOSEN_KEY}=; Path=/; Max-Age=${maxAge}${domain}`;
  }
}

export function initialLocale(): LocaleCode {
  if (typeof window !== "undefined") {
    const fromQuery = new URLSearchParams(window.location.search).get("lang");
    if (isLocaleCode(fromQuery)) {
      persistLocaleChoice(fromQuery);
      return fromQuery;
    }
  }
  return readStoredLocale() ?? DEFAULT_LOCALE;
}
