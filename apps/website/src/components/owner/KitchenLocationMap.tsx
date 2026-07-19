import { useMemo } from "react";
import {
  formatCoordinates,
  formatKitchenAddress,
  googleMapsDirectionsUrl,
  googleMapsEmbedPlaceUrl,
  googleMapsUrl,
  openStreetMapEmbedUrl,
  type KitchenAddressParts,
} from "../../lib/locationMaps";

type KitchenLocationMapProps = KitchenAddressParts & {
  latitude: number;
  longitude: number;
  name?: string;
  className?: string;
};

export function KitchenLocationMap({
  latitude,
  longitude,
  name,
  addressLine,
  city,
  state,
  pincode,
  className = "",
}: KitchenLocationMapProps) {
  const address = formatKitchenAddress({ addressLine, city, state, pincode });
  const mapsUrl = googleMapsUrl(latitude, longitude, name ?? (address || undefined));
  const directionsUrl = googleMapsDirectionsUrl(latitude, longitude);
  const mapSrc = useMemo(
    () => googleMapsEmbedPlaceUrl(latitude, longitude) || openStreetMapEmbedUrl(latitude, longitude),
    [latitude, longitude],
  );

  const hasValidCoords =
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    Math.abs(latitude) <= 90 &&
    Math.abs(longitude) <= 180;

  if (!hasValidCoords) {
    return (
      <p className="owner-kitchen-map__empty">
        Location coordinates are not set — update latitude and longitude to show the map.
      </p>
    );
  }

  return (
    <div className={`owner-kitchen-map ${className}`.trim()}>
      {address && <p className="owner-kitchen-map__address">{address}</p>}
      <p className="owner-kitchen-map__coords">{formatCoordinates(latitude, longitude)}</p>

      <div className="owner-kitchen-map__frame">
        <iframe
          title={name ? `Map — ${name}` : "Kitchen location map"}
          src={mapSrc}
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
        />
      </div>

      <div className="owner-kitchen-map__actions">
        <a
          href={mapsUrl}
          className="btn btn--primary btn--sm"
          target="_blank"
          rel="noopener noreferrer"
        >
          Open in Google Maps
        </a>
        <a
          href={directionsUrl}
          className="btn btn--ghost btn--sm"
          target="_blank"
          rel="noopener noreferrer"
        >
          Get directions
        </a>
      </div>
    </div>
  );
}
