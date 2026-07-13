import { useCallback, useEffect, useMemo, useState, type CSSProperties, type RefObject } from "react";
import { useNavigate } from "react-router-dom";
import { sampleDishImages } from "../data/content";
import { DEMO } from "../shared/demo";
import { fetchNearbyKitchens, type KitchenNearby } from "../shared/api";
import { useCustomerAuth } from "../shared/customerAuth";
import { saveKitchenToSession } from "../shared/customerSession";
import { useGeolocation } from "../hooks/useGeolocation";
import { useInView } from "../hooks/useParallax";

const CARD_IMAGES = Object.values(sampleDishImages);

type SortOrder = "asc" | "desc";
type DietFilter = "" | "veg" | "non_veg" | "vegan";

export function NearbyKitchensList() {
  const navigate = useNavigate();
  const { updateSession } = useCustomerAuth();
  const { ref, visible } = useInView(0.06);
  const { coords, status, error: geoError, refresh, setCoords } = useGeolocation(DEMO.defaultLocation);
  const [kitchens, setKitchens] = useState<KitchenNearby[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [sort, setSort] = useState<SortOrder>("asc");
  const [maxKm, setMaxKm] = useState(25);
  const [diet, setDiet] = useState<DietFilter>("");
  const [liveCaptureOnly, setLiveCaptureOnly] = useState(false);

  const mapSrc = useMemo(() => {
    const pad = 0.04;
    const lat = coords.latitude;
    const lng = coords.longitude;
    const bbox = [lng - pad, lat - pad, lng + pad, lat + pad].join("%2C");
    return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat}%2C${lng}`;
  }, [coords.latitude, coords.longitude]);

  const load = useCallback(async () => {
    setLoading(true);
    setFetchError("");
    try {
      const data = await fetchNearbyKitchens({
        latitude: coords.latitude,
        longitude: coords.longitude,
        limit: 30,
        max_km: maxKm,
        sort,
        diet: diet || undefined,
        live_capture: liveCaptureOnly || undefined,
      });
      setKitchens(data.kitchens);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Could not load nearby kitchens");
      setKitchens([]);
    } finally {
      setLoading(false);
    }
  }, [coords.latitude, coords.longitude, maxKm, sort, diet, liveCaptureOnly]);

  useEffect(() => {
    load();
  }, [load]);

  const openKitchen = (kitchen: KitchenNearby) => {
    const next = saveKitchenToSession(kitchen);
    updateSession(next);
    navigate(`/kitchen/${kitchen.id}/menu`);
  };

  const useDemoLocation = () => {
    setCoords(DEMO.defaultLocation);
  };

  return (
    <section
      className="nearby-kitchens"
      id="nearby"
      ref={ref as RefObject<HTMLElement>}
    >
      <div className="container">
        <div className={`nearby-kitchens__head reveal ${visible ? "reveal--visible" : ""}`}>
          <div>
            <span className="section__eyebrow">Near you</span>
            <h2>Cloud kitchens nearby</h2>
            <p>
              Map + list sorted by distance. Filter by diet and live-capture menu photos.
              {geoError && <span className="nearby-kitchens__geo-hint"> {geoError}</span>}
            </p>
          </div>
          <div className="nearby-kitchens__controls">
            <label>
              Radius (km)
              <select value={maxKm} onChange={(e) => setMaxKm(Number(e.target.value))}>
                {[10, 25, 50, 100].map((km) => (
                  <option key={km} value={km}>{km} km</option>
                ))}
              </select>
            </label>
            <label>
              Sort
              <select value={sort} onChange={(e) => setSort(e.target.value as SortOrder)}>
                <option value="asc">Distance ↑ nearest</option>
                <option value="desc">Distance ↓ farthest</option>
              </select>
            </label>
            <label>
              Diet
              <select value={diet} onChange={(e) => setDiet(e.target.value as DietFilter)}>
                <option value="">Any</option>
                <option value="veg">Veg</option>
                <option value="non_veg">Non-veg</option>
                <option value="vegan">Vegan</option>
              </select>
            </label>
            <label className="nearby-kitchens__checkbox">
              <input
                type="checkbox"
                checked={liveCaptureOnly}
                onChange={(e) => setLiveCaptureOnly(e.target.checked)}
              />
              Live-capture photos only
            </label>
            <button type="button" className="btn btn--ghost btn--sm" onClick={refresh} disabled={status === "loading"}>
              {status === "loading" ? "Locating…" : "Use my location"}
            </button>
            <button type="button" className="btn btn--ghost btn--sm" onClick={useDemoLocation}>
              Demo: Pune
            </button>
          </div>
        </div>

        <div className="nearby-kitchens__map glass">
          <iframe
            title="Kitchen discovery map"
            src={mapSrc}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
        </div>

        {fetchError && <div className="auth-card__error">{fetchError}</div>}

        {loading ? (
          <p className="app-loading nearby-kitchens__loading">Finding kitchens near you…</p>
        ) : kitchens.length === 0 ? (
          <div className="glass nearby-kitchens__empty">
            <p>No active kitchens within {maxKm} km with these filters.</p>
            <p className="nearby-kitchens__empty-hint">
              Run <code>python scripts/seed-dev-data.py</code> or widen the search radius.
            </p>
          </div>
        ) : (
          <ul className={`nearby-kitchens__list reveal-stagger ${visible ? "reveal--visible" : ""}`}>
            {kitchens.map((k, i) => (
              <li key={k.id} style={{ "--i": i } as CSSProperties}>
                <button type="button" className="nearby-kitchens__card glass" onClick={() => openKitchen(k)}>
                  <div className="nearby-kitchens__card-img">
                    <img src={CARD_IMAGES[i % CARD_IMAGES.length]} alt="" loading="lazy" />
                    <span className="nearby-kitchens__distance">{formatDistance(k.distance_km)}</span>
                  </div>
                  <div className="nearby-kitchens__card-body">
                    <strong>{k.name}</strong>
                    <span className="nearby-kitchens__meta">
                      {k.code}
                      {k.city ? ` · ${k.city}` : ""}
                      {k.state ? `, ${k.state}` : ""}
                    </span>
                    <span className="nearby-kitchens__badges">
                      {k.has_veg && <span className="nearby-kitchens__badge">Veg</span>}
                      {k.has_non_veg && <span className="nearby-kitchens__badge">Non-veg</span>}
                      {k.has_live_capture && <span className="nearby-kitchens__badge">Live photo</span>}
                    </span>
                  </div>
                  <span className="nearby-kitchens__arrow" aria-hidden="true">→</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(km < 10 ? 1 : 0)} km`;
}
