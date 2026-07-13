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

/** Embedded OpenStreetMap preview (no API key). */
export function openStreetMapEmbedUrl(latitude: number, longitude: number, pad = 0.012): string {
  const bbox = [longitude - pad, latitude - pad, longitude + pad, latitude + pad].join("%2C");
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${latitude}%2C${longitude}`;
}

export function formatCoordinates(latitude: number, longitude: number): string {
  return `${latitude.toFixed(5)}°, ${longitude.toFixed(5)}°`;
}
