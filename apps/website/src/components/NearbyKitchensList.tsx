import { useCallback, useEffect, useMemo, useState, type CSSProperties, type RefObject } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ListingToolbar } from "./ListingToolbar";
import { DeliveryAddressPicker } from "./DeliveryAddressPicker";
import { ReportFoodFilter } from "./ReportFoodFilter";
import { kitchenCardImage } from "../data/content";
import type { KitchenNearby, LiveKitchenSummary } from "../shared/api";
import { fetchLiveKitchens } from "../shared/api";
import { fetchPublicNearbyKitchens } from "../shared/publicApi";
import { useCustomerAuth } from "../shared/customerAuth";
import { useCustomerDelivery } from "../shared/customerDelivery";
import { saveKitchenToSession } from "../shared/customerSession";
import { useInView } from "../hooks/useParallax";
import {
  DIET_FILTER_CHANGED,
  type ReportFoodChangeDetail,
} from "../hooks/useReportFoodFilter";
import {
  discoveryMapEmbedUrl,
  googleMapsNearbyStaticUrl,
  googleMapsUrl,
  hasGoogleMapsApiKey,
} from "../lib/locationMaps";

type SortOrder = "asc" | "desc";
type DietFilter = "" | "veg" | "non_veg" | "vegan";
type ListSort = "distance_asc" | "distance_desc" | "name_asc" | "name_desc";

export function NearbyKitchensList() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { updateSession } = useCustomerAuth();
  const { ref, visible } = useInView(0.06);
  const { coords, selectedAddress, geoStatus, geoError, loading: deliveryLoading, useGps, useDemo } = useCustomerDelivery();
  const [kitchens, setKitchens] = useState<KitchenNearby[]>([]);
  const [nearest, setNearest] = useState<KitchenNearby[]>([]);
  const [liveByKitchen, setLiveByKitchen] = useState<Record<string, LiveKitchenSummary>>({});
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [sort, setSort] = useState<SortOrder>("asc");
  const [listSort, setListSort] = useState<ListSort>("distance_asc");
  const [search, setSearch] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [maxKm, setMaxKm] = useState(25);
  const [diet, setDiet] = useState<DietFilter>("");
  const [liveCaptureOnly, setLiveCaptureOnly] = useState(false);
  const [liveOnly, setLiveOnly] = useState(false);
  const [dietFilterApplied, setDietFilterApplied] = useState(false);

  const mapsEnabled = hasGoogleMapsApiKey();

  const staticMapSrc = useMemo(() => {
    if (!mapsEnabled) return null;
    return googleMapsNearbyStaticUrl(
      coords.latitude,
      coords.longitude,
      kitchens.map((k) => ({
        latitude: k.latitude,
        longitude: k.longitude,
        label: k.name,
      })),
      { zoom: kitchens.length ? 12 : 11 },
    );
  }, [mapsEnabled, coords.latitude, coords.longitude, kitchens]);

  const embedMapSrc = useMemo(
    () => discoveryMapEmbedUrl(coords.latitude, coords.longitude),
    [coords.latitude, coords.longitude],
  );

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
          q: activeSearch || undefined,
        }),
        fetchLiveKitchens().catch(() => ({ kitchens: [] as LiveKitchenSummary[], total: 0 })),
      ]);
      setKitchens(data.kitchens);
      setNearest(data.nearest ?? []);
      setDietFilterApplied(Boolean(data.diet_filter_applied));
      const map: Record<string, LiveKitchenSummary> = {};
      for (const live of liveRes.kitchens) {
        map[live.kitchen_id] = live;
      }
      setLiveByKitchen(map);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Could not load nearby kitchens");
      setKitchens([]);
      setNearest([]);
    } finally {
      setLoading(false);
    }
  }, [coords.latitude, coords.longitude, maxKm, sort, diet, liveCaptureOnly, liveOnly, activeSearch]);

  useEffect(() => {
    if (deliveryLoading) return;
    void load();
  }, [load, deliveryLoading]);

  useEffect(() => {
    const onChange = (event: Event) => {
      const nextDiet = (event as CustomEvent<ReportFoodChangeDetail>).detail?.diet;
      if (nextDiet !== undefined && nextDiet !== diet) {
        setDiet(nextDiet as DietFilter);
        return;
      }
      void load();
    };
    window.addEventListener(DIET_FILTER_CHANGED, onChange);
    return () => window.removeEventListener(DIET_FILTER_CHANGED, onChange);
  }, [diet, load]);

  // Search hits the API so dish and cuisine names match, not just kitchen names.
  useEffect(() => {
    const trimmed = search.trim();
    if (trimmed === activeSearch) return;
    const timer = window.setTimeout(() => setActiveSearch(trimmed), 350);
    return () => window.clearTimeout(timer);
  }, [search, activeSearch]);

  const openKitchen = (kitchen: KitchenNearby) => {
    const next = saveKitchenToSession(kitchen);
    updateSession(next);
    navigate(kitchen.code ? `/k/${kitchen.code}/menu` : `/kitchen/${kitchen.id}/menu`);
  };

  const useDemoLocation = () => {
    useDemo();
    setMaxKm((km) => (km < 50 ? 50 : km));
  };

  const placeLabel = selectedAddress
    ? `${selectedAddress.label}, ${selectedAddress.city}`
    : null;

  const displayed = useMemo(() => {
    const list = [...kitchens];
    if (dietFilterApplied && (listSort === "distance_asc" || listSort === "distance_desc")) {
      return listSort === "distance_desc" ? [...list].reverse() : list;
    }
    if (listSort === "name_asc") list.sort((a, b) => a.name.localeCompare(b.name));
    else if (listSort === "name_desc") list.sort((a, b) => b.name.localeCompare(a.name));
    else if (listSort === "distance_desc") list.sort((a, b) => b.distance_km - a.distance_km);
    else list.sort((a, b) => a.distance_km - b.distance_km);
    return list;
  }, [kitchens, listSort, dietFilterApplied]);

  const onListSortChange = (v: string) => {
    const next = v as ListSort;
    setListSort(next);
    if (next === "distance_asc") setSort("asc");
    if (next === "distance_desc") setSort("desc");
  };

  const fallbackNearest = !loading && kitchens.length === 0 && nearest.length > 0;
  const nothingAnywhere = !loading && kitchens.length === 0 && nearest.length === 0;

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
            <h2>{placeLabel ? `Cloud kitchens near ${placeLabel}` : "Cloud kitchens nearby"}</h2>
            <p>
              {mapsEnabled ? "Google Map" : "Map"} + list sorted by distance. Filter by diet,
              checkup report food, live-capture menu photos, or kitchens streaming now.
              {geoError && <span className="nearby-kitchens__geo-hint"> {geoError}</span>}
            </p>
            {dietFilterApplied ? (
              <p className="nearby-kitchens__geo-hint">{t("customer.discovery.dietFilterOn")}</p>
            ) : null}
          </div>
          <div className="nearby-kitchens__controls">
            <DeliveryAddressPicker variant="bar" />
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
            <ReportFoodFilter diet={diet} onDietChange={(next) => setDiet(next as DietFilter)} />
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
            <button type="button" className="btn btn--ghost btn--sm" onClick={() => void useGps()} disabled={geoStatus === "loading"}>
              {geoStatus === "loading" ? "Locating…" : "Use my location"}
            </button>
            <button type="button" className="btn btn--primary btn--sm" onClick={useDemoLocation}>
              Demo: Pune kitchens
            </button>
          </div>
        </div>

        <div className="nearby-kitchens__map glass">
          {staticMapSrc ? (
            <a
              className="nearby-kitchens__map-link"
              href={googleMapsUrl(coords.latitude, coords.longitude, "Near me")}
              target="_blank"
              rel="noopener noreferrer"
              title="Open in Google Maps"
            >
              <img
                src={staticMapSrc}
                alt="Map of kitchens near you"
                className="nearby-kitchens__map-img"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
              />
            </a>
          ) : (
            <iframe
              title="Kitchen discovery map"
              src={embedMapSrc}
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
              allow="geolocation"
            />
          )}
        </div>

        {fetchError && <div className="auth-card__error">{fetchError}</div>}

        <ListingToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search a dish, cuisine, kitchen, or city…"
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
        ) : nothingAnywhere ? (
          <div className="glass nearby-kitchens__empty">
            <p>
              {dietFilterApplied
                ? t("customer.discovery.dietFilterEmpty")
                : activeSearch
                ? `No kitchen on kitchCU matches “${activeSearch}” yet.`
                : "No active kitchens with these filters."}
            </p>
            <div className="nearby-kitchens__empty-actions">
              {activeSearch && (
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => setSearch("")}>
                  Clear search
                </button>
              )}
              <button type="button" className="btn btn--primary btn--sm" onClick={useDemoLocation}>
                Demo: Pune kitchens
              </button>
            </div>
          </div>
        ) : (
          <>
            {fallbackNearest && (
              <div className="glass nearby-kitchens__empty nearby-kitchens__empty--hint">
                <p>
                  {activeSearch
                    ? `No kitchen within ${maxKm} km serves “${activeSearch}”.`
                    : `No kitchens within ${maxKm} km of you yet.`}
                </p>
                <p className="nearby-kitchens__empty-hint">
                  Closest is {formatDistance(nearest[0].distance_km)} away
                  {nearest[0].city ? ` in ${nearest[0].city}` : ""} — here is where kitchCU is live
                  right now.
                </p>
                <div className="nearby-kitchens__empty-actions">
                  {activeSearch && (
                    <button type="button" className="btn btn--ghost btn--sm" onClick={() => setSearch("")}>
                      Clear search
                    </button>
                  )}
                  <button type="button" className="btn btn--primary btn--sm" onClick={useDemoLocation}>
                    Demo: Pune kitchens
                  </button>
                </div>
              </div>
            )}
            <ul className={`nearby-kitchens__list reveal-stagger ${visible ? "reveal--visible" : ""}`}>
            {(fallbackNearest ? nearest : displayed).map((k, i) => {
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
                      {k.avg_rating != null && (k.rating_count ?? 0) > 0
                        ? ` · ★ ${k.avg_rating.toFixed(1)}${k.rating_count ? ` (${k.rating_count})` : ""}`
                        : ""}
                      {live?.dish_name
                        ? ` · cooking ${live.dish_name}${
                            live.showcase_phase && live.showcase_phase !== "idle"
                              ? ` (${live.showcase_phase})`
                              : ""
                          }`
                        : ""}
                    </span>
                    <span className="nearby-kitchens__badges">
                      {k.better_for_report && (
                        <span className="nearby-kitchens__badge nearby-kitchens__badge--better">
                          {t("customer.discovery.betterForReport")}
                        </span>
                      )}
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
          </>
        )}
      </div>
    </section>
  );
}

function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(km < 10 ? 1 : 0)} km`;
}
