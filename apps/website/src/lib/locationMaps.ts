export type KitchenAddressParts = {
  addressLine?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;
};

export function formatKitchenAddress(parts: KitchenAddressParts): string {
  const segments = [
    parts.addressLine?.trim(),
    [parts.city, parts.state].filter(Boolean).join(", ") || undefined,
    parts.pincode?.trim(),
  ].filter(Boolean);
  return segments.join(" · ");
}

/** Browser Maps key from Vite env (never hardcode secrets in source). */
export function getGoogleMapsApiKey(): string {
  const key = import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim();
  return key || "";
}

export function hasGoogleMapsApiKey(): boolean {
  return getGoogleMapsApiKey().length > 10;
}

/** Google Maps place/search URL — opens native app on mobile when available. */
export function googleMapsUrl(latitude: number, longitude: number, label?: string): string {
  const coords = `${latitude},${longitude}`;
  const query = label ? encodeURIComponent(`${label} (${coords})`) : coords;
  return `https://www.google.com/maps/search/?api=1&query=${query}`;
}

/** Google Maps turn-by-turn directions to the kitchen pin. */
export function googleMapsDirectionsUrl(latitude: number, longitude: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`;
}

/** Google Maps driving directions between two pins (opens Maps app / web). */
export function googleMapsRouteUrl(
  originLat: number,
  originLng: number,
  destLat: number,
  destLng: number,
): string {
  return (
    `https://www.google.com/maps/dir/?api=1` +
    `&origin=${originLat},${originLng}` +
    `&destination=${destLat},${destLng}` +
    `&travelmode=driving`
  );
}

/**
 * Embeddable Google Maps directions (no API key required).
 * Uses the classic maps embed endpoint with saddr/daddr.
 */
export function googleMapsDirectionsEmbedUrl(
  originLat: number,
  originLng: number,
  destLat: number,
  destLng: number,
): string {
  return (
    `https://maps.google.com/maps?` +
    `saddr=${originLat},${originLng}&daddr=${destLat},${destLng}` +
    `&hl=en&output=embed`
  );
}

/** Google Maps Embed API — centered view (requires Maps Embed API enabled on the key). */
export function googleMapsEmbedViewUrl(
  latitude: number,
  longitude: number,
  zoom = 13,
): string | null {
  const key = getGoogleMapsApiKey();
  if (!key) return null;
  const q = new URLSearchParams({
    key,
    center: `${latitude},${longitude}`,
    zoom: String(zoom),
    maptype: "roadmap",
  });
  return `https://www.google.com/maps/embed/v1/view?${q.toString()}`;
}

/** Google Maps Embed API — single place pin. */
export function googleMapsEmbedPlaceUrl(
  latitude: number,
  longitude: number,
  zoom = 15,
): string | null {
  const key = getGoogleMapsApiKey();
  if (!key) return null;
  const q = new URLSearchParams({
    key,
    q: `${latitude},${longitude}`,
    zoom: String(zoom),
    maptype: "roadmap",
  });
  return `https://www.google.com/maps/embed/v1/place?${q.toString()}`;
}

type MapMarker = { latitude: number; longitude: number; label?: string };

/**
 * Static map with blue you-pin + orange kitchen pins (Maps Static API).
 * Falls back to null when no key — caller should use OSM embed.
 */
export function googleMapsNearbyStaticUrl(
  centerLat: number,
  centerLng: number,
  kitchens: MapMarker[],
  opts?: { width?: number; height?: number; zoom?: number },
): string | null {
  const key = getGoogleMapsApiKey();
  if (!key) return null;
  const width = opts?.width ?? 640;
  const height = opts?.height ?? 320;
  const zoom = opts?.zoom ?? 12;
  const params = new URLSearchParams({
    key,
    size: `${width}x${height}`,
    scale: "2",
    zoom: String(zoom),
    center: `${centerLat},${centerLng}`,
    maptype: "roadmap",
  });
  // You are here
  params.append("markers", `color:0x00897B|label:Y|${centerLat},${centerLng}`);
  // Cap markers — Static Maps URL length limits
  for (const k of kitchens.slice(0, 25)) {
    const label = (k.label || "K").slice(0, 1).toUpperCase();
    params.append("markers", `color:0xE65100|label:${label}|${k.latitude},${k.longitude}`);
  }
  return `https://maps.googleapis.com/maps/api/staticmap?${params.toString()}`;
}

/** Prefer Google Embed place when key is set; otherwise OSM. */
export function discoveryMapEmbedUrl(latitude: number, longitude: number): string {
  return (
    googleMapsEmbedViewUrl(latitude, longitude, 13) ||
    openStreetMapEmbedUrl(latitude, longitude)
  );
}

/** Embedded OpenStreetMap preview (no API key). */
export function openStreetMapEmbedUrl(latitude: number, longitude: number, pad = 0.012): string {
  const bbox = [longitude - pad, latitude - pad, longitude + pad, latitude + pad].join("%2C");
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${latitude}%2C${longitude}`;
}

export function formatCoordinates(latitude: number, longitude: number): string {
  return `${latitude.toFixed(5)}°, ${longitude.toFixed(5)}°`;
}

/** Haversine distance in km — used to detect GPS far from demo kitchens. */
export function distanceKm(
  a: { latitude: number; longitude: number },
  b: { latitude: number; longitude: number },
): number {
  const R = 6371;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.latitude - a.latitude);
  const dLng = toRad(b.longitude - a.longitude);
  const lat1 = toRad(a.latitude);
  const lat2 = toRad(b.latitude);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}
