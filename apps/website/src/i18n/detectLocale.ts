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
 * Order matters — first match wins.
 * Karnataka is listed before Tamil so Bengaluru → kn (not ta).
 * Telugu west edge includes Hyderabad; Karnataka box stops south of Maharashtra
 * so Pune/Mumbai/Kolhapur → Marathi.
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
  // Inside India but no specific belt — Hindi as last resort (not MH; MH is boxed as mr)
  return "hi";
}

/** Map BCP-47 / browser tags to our locale codes. */
export function localeFromBrowserTag(tag: string | undefined | null): LocaleCode | null {
  if (!tag) return null;
  const normalized = tag.trim().toLowerCase().replace(/_/g, "-");
  const primary = normalized.split("-")[0];
  // Common aliases
  if (primary === "mai" || normalized.startsWith("mai-")) return "mai";
  if (primary === "bho" || normalized.startsWith("bho-")) return "bho";
  if (isLocaleCode(primary)) return primary;
  return null;
}

/**
 * Browser language is a weak signal in India — many devices ship with hi-IN
 * even in Maharashtra. Prefer non-Hindi regional tags first; treat hi as last.
 */
export function localeFromNavigator(
  languages: readonly string[] | undefined,
  language: string | undefined,
): LocaleCode | null {
  const tags = [...(languages ?? []), language ?? ""].filter(Boolean);
  let hindi: LocaleCode | null = null;
  for (const tag of tags) {
    const hit = localeFromBrowserTag(tag);
    if (!hit || hit === "en") continue;
    if (hit === "hi") {
      hindi = hit;
      continue;
    }
    return hit;
  }
  if (hindi) return hindi;
  for (const tag of tags) {
    const hit = localeFromBrowserTag(tag);
    if (hit) return hit;
  }
  return null;
}

export type DetectedLocale = {
  suggested: LocaleCode;
  source: "geo" | "browser" | "default";
  /** Strong only when GPS matched a region box */
  confidence: "high" | "low";
};

export function resolveSuggestedLocale(input: {
  lat?: number | null;
  lng?: number | null;
  languages?: readonly string[];
  language?: string;
}): DetectedLocale {
  if (input.lat != null && input.lng != null) {
    const geo = localeFromCoordinates(input.lat, input.lng);
    if (geo) return { suggested: geo, source: "geo", confidence: "high" };
  }
  const browser = localeFromNavigator(input.languages, input.language);
  if (browser) return { suggested: browser, source: "browser", confidence: "low" };
  return { suggested: DEFAULT_LOCALE, source: "default", confidence: "low" };
}

export function readGeolocation(): Promise<{ lat: number; lng: number } | null> {
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    const timer = window.setTimeout(() => resolve(null), 6000);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        window.clearTimeout(timer);
        resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude });
      },
      () => {
        window.clearTimeout(timer);
        resolve(null);
      },
      { enableHighAccuracy: false, maximumAge: 600_000, timeout: 5500 },
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
