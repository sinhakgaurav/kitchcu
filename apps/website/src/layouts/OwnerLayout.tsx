import { useEffect, useState } from "react";
import { Navigate, Outlet, Link, useLocation } from "react-router-dom";
import { BrandNavMark } from "../components/BrandNavMark";
import { KITCHEN_HOST } from "../shared/brand";
import { useKitchenAuth } from "../shared/kitchenAuth";
import { useKitchen } from "../shared/kitchenContext";
import { customerUrl } from "../shared/urls";

const NAV_SECTIONS = [
  {
    label: "Operations",
    items: [
      { to: "/dashboard", label: "Overview", end: true },
      { to: "/dashboard/orders", label: "Orders" },
      { to: "/dashboard/menu", label: "Menu" },
      { to: "/dashboard/ingredients", label: "Ingredients" },
    ],
  },
  {
    label: "Growth",
    items: [
      { to: "/dashboard/reports", label: "Reports" },
      { to: "/dashboard/growth", label: "Intelligence" },
      { to: "/dashboard/crm", label: "CRM" },
      { to: "/dashboard/coupons", label: "Coupons" },
      { to: "/dashboard/stream", label: "Live stream" },
    ],
  },
  {
    label: "Learn & connect",
    items: [
      { to: "/dashboard/learning", label: "Learning" },
      { to: "/dashboard/community", label: "Community" },
    ],
  },
  {
    label: "Account",
    items: [
      { to: "/dashboard/subscription", label: "Subscription" },
      { to: "/dashboard/payment-gateway", label: "Payment gateway" },
      { to: "/dashboard/gst", label: "GST & finance" },
      { to: "/dashboard/setup", label: "Kitchen setup" },
    ],
  },
] as const;

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token, loading } = useKitchenAuth();
  if (loading) return <div className="app-loading">Loading...</div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function OwnerLayout() {
  const { owner, logout } = useKitchenAuth();
  const { kitchen, kitchens, setKitchenId, loading } = useKitchen();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.body.style.overflow = navOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [navOpen]);

  const currentSection = NAV_SECTIONS.flatMap((s) => s.items).find((item) =>
    item.end ? location.pathname === item.to : location.pathname.startsWith(item.to),
  );

  return (
    <div className={`owner-app${navOpen ? " owner-app--nav-open" : ""}`}>
      <button
        type="button"
        className="owner-app__backdrop"
        aria-label="Close menu"
        onClick={() => setNavOpen(false)}
      />

      <aside className="owner-app__sidebar" aria-label="Owner navigation">
        <div className="owner-app__sidebar-top">
          <div className="owner-app__brand">
            <BrandNavMark to="/" subtitle={KITCHEN_HOST} height={28} />
          </div>
          <button
            type="button"
            className="owner-app__nav-close"
            aria-label="Close menu"
            onClick={() => setNavOpen(false)}
          >
            ×
          </button>
        </div>

        {kitchens.length > 1 && (
          <label className="kc-field owner-app__kitchen-field">
            <span className="kc-field__label">Active kitchen</span>
            <select
              className="kc-select owner-app__kitchen-select"
              value={kitchen?.id ?? ""}
              onChange={(e) => setKitchenId(e.target.value)}
            >
              {kitchens.map((k) => (
                <option key={k.id} value={k.id}>{k.name}</option>
              ))}
            </select>
          </label>
        )}

        <nav className="owner-app__nav">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="owner-app__nav-group">
              <span className="owner-app__nav-label">{section.label}</span>
              {section.items.map((item) => {
                const active = item.end
                  ? location.pathname === item.to
                  : location.pathname.startsWith(item.to);
                return (
                  <Link key={item.to} to={item.to} className={active ? "active" : ""}>
                    {item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="owner-app__sidebar-foot">
          <span>{owner?.name}</span>
          <a href={customerUrl("/")} className="owner-app__customer-link">Customer app</a>
          <button type="button" className="owner-app__signout btn btn--ghost btn--sm" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="owner-app__shell">
        <header className="owner-app__topbar">
          <button
            type="button"
            className="owner-app__menu-btn"
            aria-expanded={navOpen}
            aria-label="Open menu"
            onClick={() => setNavOpen(true)}
          >
            <span /><span /><span />
          </button>
          <div className="owner-app__topbar-text">
            <strong>{currentSection?.label ?? "Dashboard"}</strong>
            {kitchen && <span>{kitchen.name}</span>}
          </div>
        </header>

        <div className="owner-app__main">
          {loading ? (
            <div className="app-loading">Loading kitchen...</div>
          ) : (
            <Outlet context={{ kitchen }} />
          )}
        </div>
      </div>
    </div>
  );
}
