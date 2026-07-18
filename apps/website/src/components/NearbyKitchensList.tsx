import { useCallback, useEffect, useMemo, useState, type CSSProperties, type RefObject } from "react";
import { useNavigate } from "react-router-dom";
import { ListingToolbar } from "./ListingToolbar";
import { kitchenCardImage } from "../data/content";
import { DEMO } from "../shared/demo";
import type { KitchenNearby, LiveKitchenSummary } from "../shared/api";
import { fetchLiveKitchens } from "../shared/api";
import { fetchPublicNearbyKitchens } from "../shared/publicApi";
import { useCustomerAuth } from "../shared/customerAuth";
import { saveKitchenToSession } from "../shared/customerSession";
import { useGeolocation } from "../hooks/useGeolocation";
import { useInView } from "../hooks/useParallax";

type SortOrder = "asc" | "desc";
type DietFilter = "" | "veg" | "non_veg" | "vegan";
type ListSort = "distance_asc" | "distance_desc" | "name_asc" | "name_desc";

export function NearbyKitchensList() {
  const navigate = useNavigate();
  const { updateSession } = useCustomerAuth();
  const { ref, visible } = useInView(0.06);
  const { coords, status, error: geoError, refresh, setCoords } = useGeolocation(DEMO.defaultLocation);
  const [kitchens, setKitchens] = useState<KitchenNearby[]>([]);
  const [liveByKitchen, setLiveByKitchen] = useState<Record<string, LiveKitchenSummary>>({});
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [sort, setSort] = useState<SortOrder>("asc");
  const [listSort, setListSort] = useState<ListSort>("distance_asc");
  const [search, setSearch] = useState("");
  const [maxKm, setMaxKm] = useState(25);
  const [diet, setDiet] = useState<DietFilter>("");
  const [liveCaptureOnly, setLiveCaptureOnly] = useState(false);
  const [liveOnly, setLiveOnly] = useState(false);

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
      const [data, liveRes] = await Promise.all([
        fetchPublicNearbyKitchens({
          latitude: coords.latitude,
          longitude: coords.longitude,
          limit: 30,
          max_km: maxKm,
          sort,
          diet: diet || undefined,
          live_capture: liveCaptureOnly || undefined,
          live_only: liveOnly || undefined,
        }),
        fetchLiveKitchens().catch(() => ({ kitchens: [] as LiveKitchenSummary[], total: 0 })),
      ]);
      setKitchens(data.kitchens);
      const map: Record<string, LiveKitchenSummary> = {};
      for (const live of liveRes.kitchens) {
        map[live.kitchen_id] = live;
      }
      setLiveByKitchen(map);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Could not load nearby kitchens");
      setKitchens([]);
    } finally {
      setLoading(false);
    }
  }, [coords.latitude, coords.longitude, maxKm, sort, diet, liveCaptureOnly, liveOnly]);

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

  const displayed = useMemo(() => {
    let list = [...kitchens];
    if (search.trim()) {
      const n = search.trim().toLowerCase();
      list = list.filter(
        (k) =>
          k.name.toLowerCase().includes(n) ||
          (k.city || "").toLowerCase().includes(n) ||
          (k.code || "").toLowerCase().includes(n),
      );
    }
    if (listSort === "name_asc") list.sort((a, b) => a.name.localeCompare(b.name));
    else if (listSort === "name_desc") list.sort((a, b) => b.name.localeCompare(a.name));
    else if (listSort === "distance_desc") list.sort((a, b) => b.distance_km - a.distance_km);
    else list.sort((a, b) => a.distance_km - b.distance_km);
    return list;
  }, [kitchens, search, listSort]);

  const onListSortChange = (v: string) => {
    const next = v as ListSort;
    setListSort(next);
    if (next === "distance_asc") setSort("asc");
    if (next === "distance_desc") setSort("desc");
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
              Map + list sorted by distance. Filter by diet, live-capture menu photos, or kitchens streaming now.
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
                checked={liveOnly}
                onChange={(e) => setLiveOnly(e.target.checked)}
              />
              Live prep streaming only
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

        <ListingToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search kitchens by name or city…"
          sort={listSort}
          onSortChange={onListSortChange}
          sortOptions={[
            { value: "distance_asc", label: "Distance ↑" },
            { value: "distance_desc", label: "Distance ↓" },
            { value: "name_asc", label: "Name A–Z" },
            { value: "name_desc", label: "Name Z–A" },
          ]}
          resultCount={displayed.length}
        />

        {loading ? (
          <p className="app-loading nearby-kitchens__loading">Finding kitchens near you…</p>
        ) : kitchens.length === 0 ? (
          <div className="glass nearby-kitchens__empty">
            <p>No active kitchens within {maxKm} km with these filters.</p>
            <p className="nearby-kitchens__empty-hint">
              Run <code>python scripts/seed-dev-data.py</code> or widen the search radius.
            </p>
          </div>
        ) : displayed.length === 0 ? (
          <div className="glass nearby-kitchens__empty">
            <p>No kitchens match “{search}”.</p>
          </div>
        ) : (
          <ul className={`nearby-kitchens__list reveal-stagger ${visible ? "reveal--visible" : ""}`}>
            {displayed.map((k, i) => {
              const live = liveByKitchen[k.id];
              return (
              <li key={k.id} style={{ "--i": i } as CSSProperties}>
                <button type="button" className="nearby-kitchens__card glass" onClick={() => openKitchen(k)}>
                  <div className="nearby-kitchens__card-img">
                    <img src={kitchenCardImage(k.id)} alt="" loading="lazy" />
                    <span className="nearby-kitchens__distance">{formatDistance(k.distance_km)}</span>
                  </div>
                  <div className="nearby-kitchens__card-body">
                    <strong>{k.name}</strong>
                    <span className="nearby-kitchens__meta">
                      {k.code}
                      {k.city ? ` · ${k.city}` : ""}
                      {k.state ? `, ${k.state}` : ""}
                      {live?.dish_name
                        ? ` · cooking ${live.dish_name}${
                            live.showcase_phase && live.showcase_phase !== "idle"
                              ? ` (${live.showcase_phase})`
                              : ""
                          }`
                        : ""}
                    </span>
                    <span className="nearby-kitchens__badges">
                      {k.has_veg && <span className="nearby-kitchens__badge">Veg</span>}
                      {k.has_non_veg && <span className="nearby-kitchens__badge">Non-veg</span>}
                      {k.has_live_capture && <span className="nearby-kitchens__badge">Live photo</span>}
                      {(k.is_live_now || live) && (
                        <span className="nearby-kitchens__badge nearby-kitchens__badge--live">LIVE</span>
                      )}
                    </span>
                    {live?.session_id && (
                      <span
                        role="link"
                        tabIndex={0}
                        className="btn btn--primary btn--sm"
                        style={{ marginTop: "0.5rem", display: "inline-block" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/live/${live.session_id}`);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            e.stopPropagation();
                            navigate(`/live/${live.session_id}`);
                          }
                        }}
                      >
                        Watch live
                      </span>
                    )}
                  </div>
                  <span className="nearby-kitchens__arrow" aria-hidden="true">→</span>
                </button>
              </li>
            );
            })}
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
