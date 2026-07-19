import { APP_STORAGE_PREFIX } from "../shared/brand";
import { DEFAULT_LOCALE, isLocaleCode, type LocaleCode } from "./languages";

const LOCALE_KEY = `${APP_STORAGE_PREFIX}_locale`;
const CHOSEN_KEY = `${APP_STORAGE_PREFIX}_locale_chosen`;

export function readStoredLocale(): LocaleCode | null {
  try {
    const raw = localStorage.getItem(LOCALE_KEY);
    return isLocaleCode(raw) ? raw : null;
  } catch {
    return null;
  }
}

export function hasChosenLocale(): boolean {
  try {
    return localStorage.getItem(CHOSEN_KEY) === "1";
  } catch {
    return false;
  }
}

export function persistLocaleChoice(code: LocaleCode): void {
  try {
    localStorage.setItem(LOCALE_KEY, code);
    localStorage.setItem(CHOSEN_KEY, "1");
  } catch {
    /* private mode */
  }
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
}

export function initialLocale(): LocaleCode {
  return readStoredLocale() ?? DEFAULT_LOCALE;
}
