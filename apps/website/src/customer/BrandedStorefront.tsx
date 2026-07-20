import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
} from "react";
import { Link, Navigate, Outlet, useParams } from "react-router-dom";
import { APP_NAME } from "../shared/brand";
import { fetchKitchenByCode, type KitchenPublic } from "../shared/api";
import { saveKitchenToSession } from "../shared/customerSession";
import { portalUrl } from "../shared/urls";

function cssUrl(url: string): string {
  return `url("${url.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}")`;
}

type BrandedCtx = {
  kitchen: KitchenPublic;
  basePath: string;
};

const BrandedStorefrontContext = createContext<BrandedCtx | null>(null);

export function useBrandedStorefront(): BrandedCtx | null {
  return useContext(BrandedStorefrontContext);
}

/** Kitchen-first shell: menu → checkout → bill, with Powered by kitchCU. */
export function BrandedStorefrontLayout() {
  const { code = "" } = useParams<{ code: string }>();
  const [kitchen, setKitchen] = useState<KitchenPublic | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!code.trim()) return;
    setLoading(true);
    setError("");
    fetchKitchenByCode(code)
      .then((k) => {
        // Active kitchens always get a kitchen-first page; owner "publish" flags the
        // primary share link. Menu → checkout → bill works either way.
        setKitchen(k);
        saveKitchenToSession(k);
      })
      .catch((err) => {
        setKitchen(null);
        setError(err instanceof Error ? err.message : "Kitchen not found.");
      })
      .finally(() => setLoading(false));
  }, [code]);

  const accent = kitchen?.branded_page?.accent_color || "#0F766E";
  const tagline =
    kitchen?.branded_page?.tagline ||
    kitchen?.description ||
    "Live-capture menu · order · bill";
  const logoUrl = kitchen?.branded_page?.logo_url || null;
  const backgroundUrl = kitchen?.branded_page?.background_url || null;

  const ctx = useMemo(
    () =>
      kitchen
        ? { kitchen, basePath: `/k/${kitchen.code}` }
        : null,
    [kitchen],
  );

  if (loading) {
    return (
      <div className="branded-store">
        <p className="app-loading">Loading kitchen…</p>
      </div>
    );
  }

  if (error || !kitchen || !ctx) {
    return (
      <div className="branded-store branded-store--empty">
        <div className="branded-store__empty-card">
          <h1>Storefront unavailable</h1>
          <p>{error || "Kitchen not found."}</p>
          <Link to="/" className="btn btn--primary">
            Discover on {APP_NAME}
          </Link>
        </div>
      </div>
    );
  }

  const shellStyle: CSSProperties = {
    ["--branded-accent" as string]: accent,
    ...(backgroundUrl
      ? {
          backgroundImage: `linear-gradient(180deg, rgba(250,248,245,0.9) 0%, rgba(243,240,234,0.94) 55%, rgba(243,240,234,0.98) 100%), ${cssUrl(backgroundUrl)}`,
          backgroundSize: "cover",
          backgroundPosition: "center top",
          backgroundRepeat: "no-repeat",
        }
      : {}),
  };

  return (
    <BrandedStorefrontContext.Provider value={ctx}>
      <div
        className={`branded-store${backgroundUrl ? " branded-store--has-bg" : ""}`}
        style={shellStyle}
      >
        <header className="branded-store__header">
          <div className="branded-store__brand">
            {logoUrl ? (
              <img src={logoUrl} alt="" className="branded-store__logo" />
            ) : null}
            <p className="branded-store__code">{kitchen.code}</p>
            <h1>{kitchen.name}</h1>
            <p className="branded-store__tagline">{tagline}</p>
          </div>
          <Link to={`${ctx.basePath}/menu`} className="branded-store__menu-link">
            Menu
          </Link>
        </header>
        <main className="branded-store__main">
          <Outlet />
        </main>
        <footer className="branded-store__footer">
          <span>
            Powered by <strong>{APP_NAME}</strong>
          </span>
          <a href={portalUrl("/")} target="_blank" rel="noreferrer">
            Grow your kitchen →
          </a>
        </footer>
      </div>
    </BrandedStorefrontContext.Provider>
  );
}

export function BrandedMenuRedirect() {
  const { code = "" } = useParams<{ code: string }>();
  return <Navigate to={`/k/${code.trim().toUpperCase()}/menu`} replace />;
}
