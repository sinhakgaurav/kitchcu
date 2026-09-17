import { FormEvent, useCallback, useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { BrandLogo } from "../../components/BrandLogo";
import { DeliveryAddressPicker } from "../../components/DeliveryAddressPicker";
import { NearbyKitchensList } from "../../components/NearbyKitchensList";
import { ReportFoodFilter } from "../../components/ReportFoodFilter";
import { ProductTour, TourReplayButton } from "../../components/ProductTour";
import { SuperAdminLink } from "../../components/SuperAdminAccess";
import { CitiesPresence } from "../../components/CitiesPresence";
import { images } from "../../data/content";
import { DEMO } from "../../shared/demo";
import { useCustomerDelivery } from "../../shared/customerDelivery";
import type { KitchenPublic, LiveKitchenSummary } from "../../shared/api";
import { fetchLiveKitchens } from "../../shared/api";
import { isCustomerSignedIn, useCustomerAuth } from "../../shared/customerAuth";
import { saveKitchenToSession } from "../../shared/customerSession";
import {
  fetchDiscoveryHome,
  fetchKitchenByCode,
  type DiscoveryDishCard,
  type DiscoveryHome,
  type DiscoveryKitchenCard,
} from "../../shared/publicApi";
import { distanceKm } from "../../lib/locationMaps";
import { DIET_FILTER_CHANGED } from "../../hooks/useReportFoodFilter";

function formatKm(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(1)} km`;
}

function formatPrice(n: number | null | undefined): string {
  if (n == null) return "—";
  return `₹${Math.round(n)}`;
}

const FALLBACK_FOOD = [
  images.customers.src,
  images.menu.src,
  images.steak.src,
  images.tacos.src,
  images.sushi.src,
  images.hero.src,
  images.heroSecondary.src,
  images.owners.src,
] as const;

function fallbackFood(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) h = (h + seed.charCodeAt(i) * (i + 1)) % 997;
  return FALLBACK_FOOD[h % FALLBACK_FOOD.length];
}

function KitchenCard({
  kitchen,
  onOpen,
}: {
  kitchen: DiscoveryKitchenCard;
  onOpen: (k: DiscoveryKitchenCard) => void;
}) {
  const { t } = useTranslation();
  return (
    <button type="button" className="disc-card" onClick={() => onOpen(kitchen)}>
      <div className="disc-card__media">
        <img
          src={kitchen.logo_url || fallbackFood(kitchen.id || kitchen.code || kitchen.name)}
          alt=""
          loading="lazy"
          className={kitchen.logo_url ? undefined : "disc-card__fallback"}
        />
        {kitchen.is_live_now ? <span className="disc-card__live">LIVE</span> : null}
      </div>
      <div className="disc-card__body">
        <strong>{kitchen.name}</strong>
        <span className="disc-card__meta">
          {formatKm(kitchen.distance_km)}
          {kitchen.city ? ` · ${kitchen.city}` : ""}
          {kitchen.avg_rating != null ? ` · ★ ${kitchen.avg_rating.toFixed(1)}` : ""}
        </span>
        <span className="disc-card__badges">
          {kitchen.has_veg ? <span className="disc-card__badge">Veg</span> : null}
          {kitchen.better_for_report ? (
            <span className="disc-card__badge disc-card__badge--better">
              {t("customer.discovery.betterForReport")}
            </span>
          ) : null}
          {kitchen.has_live_capture ? <span className="disc-card__badge">Live photo</span> : null}
        </span>
        <span className="disc-card__price">
          {kitchen.min_dish_price != null ? `From ${formatPrice(kitchen.min_dish_price)}` : kitchen.code}
        </span>
      </div>
    </button>
  );
}

function LiveRailCard({
  kitchen,
  sessionId,
  onMenu,
  onWatch,
}: {
  kitchen: DiscoveryKitchenCard;
  sessionId?: string;
  onMenu: (k: DiscoveryKitchenCard) => void;
  onWatch: (sessionId: string) => void;
}) {
  const primary = () => {
    if (sessionId) onWatch(sessionId);
    else onMenu(kitchen);
  };
  return (
    <article className="disc-card disc-card--live">
      <button type="button" className="disc-card__media" onClick={primary}>
        <img
          src={kitchen.logo_url || fallbackFood(kitchen.id || kitchen.code || kitchen.name)}
          alt=""
          loading="lazy"
          className={kitchen.logo_url ? undefined : "disc-card__fallback"}
        />
        <span className="disc-card__live">LIVE</span>
      </button>
      <div className="disc-card__body">
        <strong>{kitchen.name}</strong>
        <span className="disc-card__meta">
          {formatKm(kitchen.distance_km)}
          {kitchen.city ? ` · ${kitchen.city}` : ""}
        </span>
        <span className="disc-card__badges">
          {kitchen.has_veg ? <span className="disc-card__badge">Veg</span> : null}
          {kitchen.has_live_capture ? <span className="disc-card__badge">Live photo</span> : null}
        </span>
        <div className="disc-card__actions">
          {sessionId ? (
            <button type="button" className="btn btn--primary btn--sm" onClick={() => onWatch(sessionId)}>
              Watch live
            </button>
          ) : null}
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => onMenu(kitchen)}>
            Menu
          </button>
        </div>
      </div>
    </article>
  );
}

function DishCard({
  dish,
  onOpen,
}: {
  dish: DiscoveryDishCard;
  onOpen: (d: DiscoveryDishCard) => void;
}) {
  return (
    <button type="button" className="disc-card disc-card--dish" onClick={() => onOpen(dish)}>
      <div className="disc-card__media">
        {dish.image_url ? (
          <img src={dish.image_url} alt="" loading="lazy" />
        ) : (
          <img src={images.hero.src} alt="" loading="lazy" className="disc-card__fallback" />
        )}
      </div>
      <div className="disc-card__body">
        <strong>{dish.dish_name}</strong>
        <span className="disc-card__meta">
          {dish.kitchen_name} · {formatKm(dish.distance_km)}
        </span>
        <span className="disc-card__price">{formatPrice(dish.price)}</span>
      </div>
    </button>
  );
}

function Rail({
  id,
  title,
  subtitle,
  children,
  empty,
}: {
  id: string;
  title: string;
  subtitle: string;
  children: ReactNode;
  empty?: string;
}) {
  const hasKids = Array.isArray(children) ? children.length > 0 : Boolean(children);
  return (
    <section className="disc-rail" id={id}>
      <header className="disc-rail__head">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </header>
      {hasKids ? <div className="disc-rail__track">{children}</div> : <p className="disc-rail__empty">{empty}</p>}
    </section>
  );
}

export function CustomerDiscoveryHome() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { session, updateSession } = useCustomerAuth();
  const {
    coords,
    source,
    selectedAddress,
    geoStatus,
    geoError,
    loading: deliveryLoading,
    useGps,
    useDemo,
  } = useCustomerDelivery();
  const [maxKm, setMaxKm] = useState(25);
  const [feed, setFeed] = useState<DiscoveryHome | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState("");
  const [codeBusy, setCodeBusy] = useState(false);
  const [liveByKitchen, setLiveByKitchen] = useState<Record<string, LiveKitchenSummary>>({});

  const kmFromDemo = distanceKm(coords, DEMO.defaultLocation);
  const farFromDemo = kmFromDemo > 80 && source !== "address";
  const placeLabel = selectedAddress
    ? `${selectedAddress.label}, ${selectedAddress.city}`
    : source === "demo"
      ? DEMO.defaultLocation.label
      : null;

  const load = useCallback(async () => {
    setLoading(true);
    setFetchError("");
    try {
      const [data, liveRes] = await Promise.all([
        fetchDiscoveryHome({
          latitude: coords.latitude,
          longitude: coords.longitude,
          max_km: maxKm,
          section_limit: 12,
          q: activeQuery || undefined,
        }),
        fetchLiveKitchens().catch(() => ({ kitchens: [] as LiveKitchenSummary[], total: 0 })),
      ]);
      setFeed(data);
      const map: Record<string, LiveKitchenSummary> = {};
      for (const live of liveRes.kitchens) {
        map[live.kitchen_id] = live;
      }
      setLiveByKitchen(map);
    } catch (err) {
      setFeed(null);
      setFetchError(err instanceof Error ? err.message : "Could not load kitchens near you");
    } finally {
      setLoading(false);
    }
  }, [coords.latitude, coords.longitude, maxKm, activeQuery]);

  useEffect(() => {
    if (deliveryLoading) return;
    void load();
  }, [load, deliveryLoading]);

  useEffect(() => {
    const onChange = () => {
      void load();
    };
    window.addEventListener(DIET_FILTER_CHANGED, onChange);
    return () => window.removeEventListener(DIET_FILTER_CHANGED, onChange);
  }, [load]);

  // Search runs server-side across every kitchen in radius, so typing (not just Enter)
  // is enough — the client only debounces to keep the request rate sane.
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed === activeQuery) return;
    const timer = setTimeout(() => setActiveQuery(trimmed), 350);
    return () => clearTimeout(timer);
  }, [query, activeQuery]);

  const openKitchen = (kitchen: {
    id: string;
    code: string;
    name: string;
    city?: string | null;
  }) => {
    const publicKitchen: KitchenPublic = {
      id: kitchen.id,
      code: kitchen.code,
      name: kitchen.name,
      city: kitchen.city ?? null,
      state: null,
      status: "active",
    };
    const next = saveKitchenToSession(publicKitchen);
    updateSession(next);
    navigate(`/k/${kitchen.code}/menu`);
  };

  const openDiscoveryKitchen = (k: DiscoveryKitchenCard) => openKitchen(k);

  const openDish = (d: DiscoveryDishCard) => {
    openKitchen({
      id: d.kitchen_id,
      code: d.kitchen_code,
      name: d.kitchen_name,
    });
  };

  // The feed is already scoped to the search term by the API — filtering again here
  // would only re-narrow the 12-item rail slices and hide real matches.
  const nearYou = feed?.near_you ?? [];
  const featured = feed?.featured ?? [];
  const mostLiked = feed?.most_liked ?? [];
  const liveNow = (() => {
    const fromFeed = feed?.live_now ?? [];
    const byId = new Map(fromFeed.map((k) => [k.id, k]));
    for (const live of Object.values(liveByKitchen)) {
      if (byId.has(live.kitchen_id)) continue;
      byId.set(live.kitchen_id, {
        id: live.kitchen_id,
        code: live.kitchen_code,
        name: live.kitchen_name,
        city: null,
        distance_km: 0,
        latitude: 0,
        longitude: 0,
        has_veg: false,
        has_non_veg: false,
        has_live_capture: false,
        is_live_now: true,
        is_featured: false,
        avg_rating: null,
        rating_count: 0,
        min_dish_price: null,
        tagline: live.dish_name ?? null,
        logo_url: null,
      });
    }
    return [...byId.values()];
  })();
  const cheapest = feed?.cheapest_dishes ?? [];

  const onCodeSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setCodeError("");
    setCodeBusy(true);
    try {
      const kitchen = await fetchKitchenByCode(code);
      openKitchen(kitchen);
    } catch (err) {
      setCodeError(err instanceof Error ? err.message : "Kitchen not found");
    } finally {
      setCodeBusy(false);
    }
  };

  const useDemoPin = () => {
    useDemo();
    setMaxKm((km) => (km < 50 ? 50 : km));
  };

  const heroName = session?.name?.trim()?.split(" ")[0];

  return (
    <div className="disc-home">
      <ProductTour
        id="customer"
        skipLabel={t("customer.tour.skip")}
        nextLabel={t("customer.tour.next")}
        backLabel={t("customer.tour.back")}
        doneLabel={t("customer.tour.done")}
        stepLabel={(current, total) => t("customer.tour.step", { current, total })}
        steps={[
          { title: t("customer.tour.s1Title"), body: t("customer.tour.s1Body") },
          { title: t("customer.tour.s2Title"), body: t("customer.tour.s2Body") },
          { title: t("customer.tour.s3Title"), body: t("customer.tour.s3Body") },
          { title: t("customer.tour.s4Title"), body: t("customer.tour.s4Body") },
        ]}
      />
      <header className="disc-home__hero">
        <div
          className="disc-home__hero-bg"
          style={{ backgroundImage: `url(${images.hero.src})` }}
          role="img"
          aria-label={images.hero.alt}
        />
        <div className="disc-home__hero-scrim" aria-hidden />
        <div className="container disc-home__hero-inner">
          <BrandLogo variant="wordmark" className="brand-logo--lg disc-home__brand" />
          <h1>
            {heroName
              ? t("customer.discovery.helloName", { name: heroName })
              : t("customer.discovery.title")}
          </h1>
          <p className="disc-home__lede">{t("customer.discovery.lede")}</p>
          <p className="disc-home__ops">
            <TourReplayButton id="customer" label={t("customer.tour.replay")} />
          </p>
          {isCustomerSignedIn(session) ? (
            <div className="disc-home__welcome">
              <Link to="/dashboard">{t("customer.nav.dashboard")}</Link>
              <Link to="/orders">{t("customer.nav.myOrders")}</Link>
              <Link to="/dashboard?tab=account">{t("customer.nav.profile")}</Link>
            </div>
          ) : null}
          <p className="disc-home__ops">
            <SuperAdminLink className="disc-home__ops-link" />
          </p>

          <form
            className="disc-home__search"
            onSubmit={(e) => {
              e.preventDefault();
              const trimmed = query.trim();
              // Enter should not wait out the debounce.
              if (trimmed === activeQuery) void load();
              else setActiveQuery(trimmed);
            }}
          >
            <label className="disc-home__search-field">
              <span className="visually-hidden">{t("common.search")}</span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t("customer.discovery.searchPlaceholder")}
                autoComplete="off"
                enterKeyHint="search"
              />
            </label>
            <div className="disc-home__loc">
              <DeliveryAddressPicker variant="hero" />
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => {
                  void useGps();
                }}
                disabled={geoStatus === "loading"}
              >
                {geoStatus === "loading" ? t("common.loading") : t("customer.discovery.useLocation")}
              </button>
              <label>
                <span className="visually-hidden">Radius</span>
                <select
                  value={maxKm}
                  onChange={(e) => setMaxKm(Number(e.target.value))}
                  aria-label="Search radius"
                >
                  <option value={10}>10 km</option>
                  <option value={25}>25 km</option>
                  <option value={50}>50 km</option>
                  <option value={100}>100 km</option>
                </select>
              </label>
              <ReportFoodFilter variant="hero" />
            </div>
          </form>

          {geoError ? <p className="disc-home__hint">{geoError}</p> : null}
          {feed?.diet_filter_applied ? (
            <p className="disc-home__hint">{t("customer.discovery.dietFilterOn")}</p>
          ) : null}
          {!loading && !fetchError && (feed?.total_kitchens ?? 0) === 0 ? (
            <div className="disc-home__banner">
              {feed?.diet_filter_applied ? (
                <p>{t("customer.discovery.dietFilterEmpty")}</p>
              ) : activeQuery ? (
                <>
                  <p>
                    Nothing matches “{activeQuery}” within {maxKm} km. Try a kitchen name, a dish
                    like Samosa, or a cuisine.
                  </p>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => {
                      setQuery("");
                      setActiveQuery("");
                    }}
                  >
                    Clear search
                  </button>
                </>
              ) : farFromDemo ? (
                <>
                  {/* Widening cannot help here — the nearest kitchens are hundreds of km away. */}
                  <p>
                    We are not live near this location yet. Browse our demo kitchens in Pune to see
                    how kitchCU works.
                  </p>
                  <button type="button" className="btn btn--primary btn--sm" onClick={useDemoPin}>
                    Show demo kitchens
                  </button>
                </>
              ) : (
                <>
                  <p>
                    No kitchens within {maxKm} km
                    {placeLabel ? ` of ${placeLabel}` : " of you"} yet.
                  </p>
                  {maxKm < 100 ? (
                    <button
                      type="button"
                      className="btn btn--primary btn--sm"
                      onClick={() => setMaxKm(maxKm < 25 ? 25 : maxKm < 50 ? 50 : 100)}
                    >
                      Search wider
                    </button>
                  ) : null}
                  <button type="button" className="btn btn--ghost btn--sm" onClick={useDemoPin}>
                    Show demo kitchens
                  </button>
                </>
              )}
            </div>
          ) : null}
        </div>
      </header>

      <NearbyKitchensList />

      <div className="container disc-home__body">
        {session && session.savedKitchens.length > 0 ? (
          <section className="disc-rail" id="saved">
            <header className="disc-rail__head">
              <div>
                <h2>Your kitchens</h2>
                <p>Jump back in</p>
              </div>
            </header>
            <div className="disc-rail__track">
              {session.savedKitchens.map((k) => (
                <button
                  key={k.id}
                  type="button"
                  className="disc-card disc-card--compact"
                  onClick={() => openKitchen(k)}
                >
                  <div className="disc-card__body">
                    <strong>{k.name}</strong>
                    <span className="disc-card__meta">
                      {k.code}
                      {k.city ? ` · ${k.city}` : ""}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </section>
        ) : null}

        {fetchError ? <div className="auth-card__error">{fetchError}</div> : null}
        {loading ? <p className="app-loading">Finding kitchens near you…</p> : null}

        {!loading && feed ? (
          <>
            <Rail
              id="near-you"
              title="Near you"
              subtitle={
                placeLabel
                  ? `${feed.total_kitchens} near ${placeLabel}`
                  : `${feed.total_kitchens} within ${maxKm} km`
              }
              empty="No kitchens in this radius. Widen search or try demo kitchens."
            >
              {nearYou.map((k) => (
                <KitchenCard key={k.id} kitchen={k} onOpen={openDiscoveryKitchen} />
              ))}
            </Rail>

            <Rail
              id="featured"
              title="Featured"
              subtitle="Published brand pages"
              empty="No featured kitchens here yet."
            >
              {featured.map((k) => (
                <KitchenCard key={`f-${k.id}`} kitchen={k} onOpen={openDiscoveryKitchen} />
              ))}
            </Rail>

            <Rail
              id="most-liked"
              title="Most liked"
              subtitle="Home-taste ratings"
              empty="Ratings appear after delivered orders."
            >
              {mostLiked.map((k) => (
                <KitchenCard key={`l-${k.id}`} kitchen={k} onOpen={openDiscoveryKitchen} />
              ))}
            </Rail>

            <Rail
              id="live-now"
              title="Live now"
              subtitle="Watch prep, then order"
              empty="No kitchens live nearby right now."
            >
              {liveNow.map((k) => (
                <LiveRailCard
                  key={`live-${k.id}`}
                  kitchen={k}
                  sessionId={liveByKitchen[k.id]?.session_id}
                  onMenu={openDiscoveryKitchen}
                  onWatch={(sessionId) => navigate(`/live/${sessionId}`)}
                />
              ))}
            </Rail>

            <Rail
              id="cheapest"
              title="Best prices"
              subtitle="Lowest active dishes nearby"
              empty="No priced dishes in range yet."
            >
              {cheapest.map((d) => (
                <DishCard key={d.dish_id} dish={d} onOpen={openDish} />
              ))}
            </Rail>
          </>
        ) : null}

        <section className="disc-code" id="by-code">
          <header className="disc-rail__head">
            <div>
              <h2>Kitchen code</h2>
              <p>Enter a code from WhatsApp or a flyer — e.g. {DEMO.kitchenCode}</p>
            </div>
          </header>
          <form className="disc-code__form" onSubmit={onCodeSubmit}>
            <label>
              Code
              <input
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder={DEMO.kitchenCode}
                required
              />
            </label>
            {codeError ? <div className="auth-card__error">{codeError}</div> : null}
            <div className="disc-code__actions">
              <button type="submit" className="btn btn--primary" disabled={codeBusy}>
                {codeBusy ? "Opening…" : "Open menu"}
              </button>
              <button
                type="button"
                className="btn btn--ghost"
                disabled={codeBusy}
                onClick={() => {
                  setCode(DEMO.kitchenCode);
                  void (async () => {
                    setCodeBusy(true);
                    try {
                      const kitchen = await fetchKitchenByCode(DEMO.kitchenCode);
                      openKitchen(kitchen);
                    } catch (err) {
                      setCodeError(err instanceof Error ? err.message : "Demo kitchen not found");
                    } finally {
                      setCodeBusy(false);
                    }
                  })();
                }}
              >
                Try {DEMO.kitchenCode}
              </button>
            </div>
          </form>
        </section>

        <CitiesPresence variant="inline" id="cities" />
      </div>
    </div>
  );
}
