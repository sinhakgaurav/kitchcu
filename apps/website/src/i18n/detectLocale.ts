import { DEFAULT_LOCALE, isLocaleCode, type LocaleCode } from "./languages";
import regionsJson from "./regions.json";

/** Coarse India bounding boxes → primary language (no geocoding API). */
type RegionBox = {
  lang: LocaleCode;
  /** South, west, north, east (lat/lng) */
  s: number;
  w: number;
  n: number;
  e: number;
};

/**
 * Order matters — first match wins. Boxes are approximate administrative belts.
 * Pune/MH → Marathi; TN → Tamil; etc. Hindi belt covers large north/central area.
 */
export const INDIA_LANGUAGE_REGIONS: RegionBox[] = regionsJson as RegionBox[];

export function localeFromCoordinates(lat: number, lng: number): LocaleCode | null {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  // Outside a loose India envelope — no regional suggestion
  if (lat < 6.5 || lat > 37.5 || lng < 67.5 || lng > 97.5) return null;
  for (const box of INDIA_LANGUAGE_REGIONS) {
    if (lat >= box.s && lat <= box.n && lng >= box.w && lng <= box.e) {
      return box.lang;
    }
  }
  return "hi";
}

/** Map BCP-47 / browser tags to our locale codes. */
export function localeFromBrowserTag(tag: string | undefined | null): LocaleCode | null {
  if (!tag) return null;
  const primary = tag.trim().toLowerCase().split("-")[0];
  if (isLocaleCode(primary)) return primary;
  return null;
}

export function localeFromNavigator(
  languages: readonly string[] | undefined,
  language: string | undefined,
): LocaleCode | null {
  const tags = [...(languages ?? []), language ?? ""].filter(Boolean);
  for (const tag of tags) {
    const hit = localeFromBrowserTag(tag);
    if (hit && hit !== "en") return hit;
  }
  for (const tag of tags) {
    const hit = localeFromBrowserTag(tag);
    if (hit) return hit;
  }
  return null;
}

export type DetectedLocale = {
  suggested: LocaleCode;
  source: "geo" | "browser" | "default";
};

export function resolveSuggestedLocale(input: {
  lat?: number | null;
  lng?: number | null;
  languages?: readonly string[];
  language?: string;
}): DetectedLocale {
  if (input.lat != null && input.lng != null) {
    const geo = localeFromCoordinates(input.lat, input.lng);
    if (geo) return { suggested: geo, source: "geo" };
  }
  const browser = localeFromNavigator(input.languages, input.language);
  if (browser) return { suggested: browser, source: "browser" };
  return { suggested: DEFAULT_LOCALE, source: "default" };
}

export function readGeolocation(): Promise<{ lat: number; lng: number } | null> {
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    const timer = window.setTimeout(() => resolve(null), 4000);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        window.clearTimeout(timer);
        resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      },
      () => {
        window.clearTimeout(timer);
        resolve(null);
      },
      { enableHighAccuracy: false, maximumAge: 600_000, timeout: 3500 },
    );
  });
}

export async function detectSuggestedLocale(): Promise<DetectedLocale> {
  const coords = await readGeolocation();
  return resolveSuggestedLocale({
    lat: coords?.lat,
    lng: coords?.lng,
    languages: typeof navigator !== "undefined" ? navigator.languages : undefined,
    language: typeof navigator !== "undefined" ? navigator.language : undefined,
  });
}
