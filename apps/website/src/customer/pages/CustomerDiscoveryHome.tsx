import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useGeolocation } from "../../hooks/useGeolocation";
import { DEMO } from "../../shared/demo";
import type { KitchenPublic } from "../../shared/api";
import { useCustomerAuth } from "../../shared/customerAuth";
import { saveKitchenToSession } from "../../shared/customerSession";
import {
  fetchDiscoveryHome,
  fetchKitchenByCode,
  type DiscoveryDishCard,
  type DiscoveryHome,
  type DiscoveryKitchenCard,
} from "../../shared/publicApi";
import { distanceKm } from "../../lib/locationMaps";

const PATHWAYS = [
  { id: "near-you", labelKey: "customer.nav.nearYou" },
  { id: "featured", labelKey: "customer.nav.featured" },
  { id: "most-liked", labelKey: "customer.nav.featured" },
  { id: "live-now", labelKey: "owner.nav.stream" },
  { id: "cheapest", labelKey: "customer.nav.bestPrices" },
  { id: "by-code", labelKey: "customer.nav.kitchenCode" },
] as const;

function formatKm(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(1)} km`;
}

function formatPrice(n: number | null | undefined): string {
  if (n == null) return "—";
  return `₹${Math.round(n)}`;
}

function KitchenCard({
  kitchen,
  onOpen,
  badge,
}: {
  kitchen: DiscoveryKitchenCard;
  onOpen: (k: DiscoveryKitchenCard) => void;
  badge?: string;
}) {
  return (
    <button type="button" className="disc-card" onClick={() => onOpen(kitchen)}>
      <div className="disc-card__media">
        {kitchen.logo_url ? (
          <img src={kitchen.logo_url} alt="" loading="lazy" />
        ) : (
          <span className="disc-card__monogram" aria-hidden>
            {(kitchen.name || "K").slice(0, 1).toUpperCase()}
          </span>
        )}
        {badge ? <span className="disc-card__badge">{badge}</span> : null}
        {kitchen.is_live_now ? <span className="disc-card__live">LIVE</span> : null}
      </div>
      <div className="disc-card__body">
        <strong>{kitchen.name}</strong>
        <span className="disc-card__meta">
          {formatKm(kitchen.distance_km)}
          {kitchen.city ? ` · ${kitchen.city}` : ""}
          {kitchen.avg_rating != null ? ` · ★ ${kitchen.avg_rating.toFixed(1)}` : ""}
        </span>
        {kitchen.tagline ? <span className="disc-card__tagline">{kitchen.tagline}</span> : null}
        <span className="disc-card__price">
          {kitchen.min_dish_price != null ? `From ${formatPrice(kitchen.min_dish_price)}` : kitchen.code}
        </span>
      </div>
    </button>
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
          <span className="disc-card__monogram" aria-hidden>
            {(dish.dish_name || "D").slice(0, 1).toUpperCase()}
          </span>
        )}
        <span className="disc-card__badge disc-card__badge--price">{formatPrice(dish.price)}</span>
      </div>
      <div className="disc-card__body">
        <strong>{dish.dish_name}</strong>
        <span className="disc-card__meta">
          {dish.kitchen_name} · {formatKm(dish.distance_km)}
        </span>
        {dish.is_live_capture_hero ? (
          <span className="disc-card__tagline">Live-capture photo</span>
        ) : null}
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
  const { coords, status, error: geoError, refresh, setCoords } = useGeolocation(DEMO.defaultLocation);
  const [maxKm, setMaxKm] = useState(25);
  const [feed, setFeed] = useState<DiscoveryHome | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");
  const [query, setQuery] = useState("");
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState("");
  const [codeBusy, setCodeBusy] = useState(false);

  const kmFromDemo = distanceKm(coords, DEMO.defaultLocation);
  const farFromDemo = kmFromDemo > 80;

  const load = useCallback(async () => {
    setLoading(true);
    setFetchError("");
    try {
      const data = await fetchDiscoveryHome({
        latitude: coords.latitude,
        longitude: coords.longitude,
        max_km: maxKm,
        section_limit: 12,
      });
      setFeed(data);
    } catch (err) {
      setFeed(null);
      setFetchError(err instanceof Error ? err.message : "Could not load kitchens near you");
    } finally {
      setLoading(false);
    }
  }, [coords.latitude, coords.longitude, maxKm]);

  useEffect(() => {
    void load();
  }, [load]);

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

  const filterKitchens = useCallback(
    (list: DiscoveryKitchenCard[]) => {
      const q = query.trim().toLowerCase();
      if (!q) return list;
      return list.filter(
        (k) =>
          k.name.toLowerCase().includes(q) ||
          k.code.toLowerCase().includes(q) ||
          (k.city || "").toLowerCase().includes(q) ||
          (k.tagline || "").toLowerCase().includes(q),
      );
    },
    [query],
  );

  const nearYou = useMemo(() => filterKitchens(feed?.near_you ?? []), [feed, filterKitchens]);
  const featured = useMemo(() => filterKitchens(feed?.featured ?? []), [feed, filterKitchens]);
  const mostLiked = useMemo(() => filterKitchens(feed?.most_liked ?? []), [feed, filterKitchens]);
  const liveNow = useMemo(() => filterKitchens(feed?.live_now ?? []), [feed, filterKitchens]);
  const cheapest = useMemo(() => {
    const list = feed?.cheapest_dishes ?? [];
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (d) =>
        d.dish_name.toLowerCase().includes(q) ||
        d.kitchen_name.toLowerCase().includes(q) ||
        d.kitchen_code.toLowerCase().includes(q),
    );
  }, [feed, query]);

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
    setCoords(DEMO.defaultLocation);
    setMaxKm((km) => (km < 50 ? 50 : km));
  };

  return (
    <div className="disc-home">
      <header className="disc-home__hero">
        <div className="container disc-home__hero-inner">
          <p className="disc-home__eyebrow">Order paths · cloud kitchens</p>
          <h1>
            {session?.name?.trim()
              ? `What are you ordering, ${session.name.split(" ")[0]}?`
              : t("customer.discovery.title")}
          </h1>
          <p className="disc-home__lede">
            Nearby kitchens, featured picks, top-rated home taste, live prep, and the best prices in your
            area — pick a path and order.
          </p>

          <div className="disc-home__search">
            <label className="disc-home__search-field">
              <span className="visually-hidden">{t("common.search")}</span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t("customer.discovery.searchPlaceholder")}
                autoComplete="off"
              />
            </label>
            <div className="disc-home__loc">
              <button type="button" className="btn btn--ghost btn--sm" onClick={refresh} disabled={status === "loading"}>
                {status === "loading" ? t("common.loading") : t("customer.discovery.useLocation")}
              </button>
              <label>
                Radius
                <select value={maxKm} onChange={(e) => setMaxKm(Number(e.target.value))}>
                  <option value={10}>10 km</option>
                  <option value={25}>25 km</option>
                  <option value={50}>50 km</option>
                  <option value={100}>100 km</option>
                </select>
              </label>
            </div>
          </div>

          {geoError ? <p className="disc-home__hint">{geoError}</p> : null}
          {farFromDemo && (feed?.total_kitchens ?? 0) === 0 ? (
            <div className="disc-home__banner">
              <p>
                No kitchens within {maxKm} km of your GPS ({Math.round(kmFromDemo)} km from the Pune demo
                cluster).
              </p>
              <button type="button" className="btn btn--primary btn--sm" onClick={useDemoPin}>
                Show Pune demo kitchens
              </button>
            </div>
          ) : null}

          <nav className="disc-pathways" aria-label="Order pathways">
            {PATHWAYS.map((p) => (
              <a key={p.id} href={`#${p.id}`} className="disc-pathways__chip">
                {t(p.labelKey)}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <div className="container disc-home__body">
        {session && session.savedKitchens.length > 0 ? (
          <section className="disc-rail" id="saved">
            <header className="disc-rail__head">
              <div>
                <h2>Your kitchens</h2>
                <p>Saved from previous visits — jump back in.</p>
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
        {loading ? <p className="app-loading">Finding order options near you…</p> : null}

        {!loading && feed ? (
          <>
            <Rail
              id="near-you"
              title="Near you"
              subtitle={`${feed.total_kitchens} active kitchen${feed.total_kitchens === 1 ? "" : "s"} within ${maxKm} km`}
              empty="No kitchens in this radius. Widen the search or try the Pune demo pin."
            >
              {nearYou.map((k) => (
                <KitchenCard key={k.id} kitchen={k} onOpen={openDiscoveryKitchen} badge="Near" />
              ))}
            </Rail>

            <Rail
              id="featured"
              title="Featured kitchens"
              subtitle="Published brand pages and chef-featured menus"
              empty="No featured kitchens here yet — try nearby."
            >
              {featured.map((k) => (
                <KitchenCard key={`f-${k.id}`} kitchen={k} onOpen={openDiscoveryKitchen} badge="Featured" />
              ))}
            </Rail>

            <Rail
              id="most-liked"
              title="Most liked"
              subtitle="Home-taste ratings from verified orders"
              empty="Ratings will appear after customers rate delivered dishes."
            >
              {mostLiked.map((k) => (
                <KitchenCard
                  key={`l-${k.id}`}
                  kitchen={k}
                  onOpen={openDiscoveryKitchen}
                  badge={k.avg_rating != null ? `★ ${k.avg_rating.toFixed(1)}` : "Trusted"}
                />
              ))}
            </Rail>

            <Rail
              id="live-now"
              title="Live now"
              subtitle="Watch prep as it happens — then order the same kitchen"
              empty="No kitchens are live in this area right now."
            >
              {liveNow.map((k) => (
                <KitchenCard key={`live-${k.id}`} kitchen={k} onOpen={openDiscoveryKitchen} badge="Live" />
              ))}
            </Rail>

            <Rail
              id="cheapest"
              title="Best prices near you"
              subtitle="Lowest active dish prices within your radius"
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
              <h2>Have a kitchen code?</h2>
              <p>Owners share codes like {DEMO.kitchenCode} on WhatsApp and flyers.</p>
            </div>
          </header>
          <form className="disc-code__form" onSubmit={onCodeSubmit}>
            <label>
              Kitchen code
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
                Demo {DEMO.kitchenCode}
              </button>
              <Link to="/browse" className="btn btn--ghost">
                Full code page
              </Link>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
