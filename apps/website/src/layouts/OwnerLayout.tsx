import { useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, Link, useLocation } from "react-router-dom";
import { BrandNavMark } from "../components/BrandNavMark";
import { LanguageSwitcher } from "../i18n/LanguageSwitcher";
import { KITCHEN_HOST } from "../shared/brand";
import { fetchKitchenEntitlements } from "../shared/api";
import { useKitchenAuth } from "../shared/kitchenAuth";
import { useKitchen } from "../shared/kitchenContext";
import { customerUrl } from "../shared/urls";

type NavItem = { to: string; label: string; end?: boolean; module?: string };

const NAV_SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: "Operations",
    items: [
      { to: "/dashboard", label: "Overview", end: true },
      { to: "/dashboard/orders", label: "Orders" },
      { to: "/dashboard/menu", label: "Menu" },
      { to: "/dashboard/brand", label: "Brand page" },
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
      { to: "/dashboard/tiffin", label: "Tiffin plans", module: "tiffin_plans" },
      { to: "/dashboard/templates", label: "Templates", module: "marketing_broadcast" },
      { to: "/dashboard/stream", label: "Live stream", module: "streaming" },
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
      { to: "/dashboard/whatsapp", label: "WhatsApp", module: "whatsapp" },
      { to: "/dashboard/payment-gateway", label: "Payment gateway", module: "razorpay" },
      { to: "/dashboard/gst", label: "GST & finance" },
      { to: "/dashboard/setup", label: "Kitchen setup" },
    ],
  },
];

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token, loading } = useKitchenAuth();
  if (loading) return <div className="app-loading">Loading...</div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function OwnerLayout() {
  const { owner, logout, token } = useKitchenAuth();
  const { kitchen, kitchens, setKitchenId, loading } = useKitchen();
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const [modules, setModules] = useState<Record<string, boolean> | null>(null);

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.body.style.overflow = navOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [navOpen]);

  useEffect(() => {
    if (!kitchen?.id || !token) {
      setModules(null);
      return;
    }
    let cancelled = false;
    fetchKitchenEntitlements(kitchen.id)
      .then((ent) => {
        if (!cancelled) setModules(ent.modules || {});
      })
      .catch(() => {
        // Soft-fail: show all nav if entitlements unavailable (legacy kitchens).
        if (!cancelled) setModules(null);
      });
    return () => {
      cancelled = true;
    };
  }, [kitchen?.id, token]);

  const visibleSections = useMemo(() => {
    return NAV_SECTIONS.map((section) => ({
      ...section,
      items: section.items.filter((item) => {
        if (!item.module || modules == null) return true;
        return modules[item.module] !== false;
      }),
    })).filter((section) => section.items.length > 0);
  }, [modules]);

  const currentSection = visibleSections.flatMap((s) => s.items).find((item) =>
    item.end ? location.pathname === item.to : location.pathname.startsWith(item.to),
  );

  const gatedItem = NAV_SECTIONS.flatMap((s) => s.items).find(
    (item) =>
      item.module &&
      (item.end
        ? location.pathname === item.to
        : location.pathname.startsWith(item.to)),
  );
  if (
    modules != null &&
    gatedItem?.module &&
    modules[gatedItem.module] === false
  ) {
    return <Navigate to="/dashboard" replace />;
  }

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
            <BrandNavMark to="/" subtitle={KITCHEN_HOST} height={40} />
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
          {visibleSections.map((section) => (
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
          <LanguageSwitcher />
          <span>{owner?.name}</span>
          <a href={customerUrl("/")} className="owner-app__customer-link" target="_blank" rel="noopener noreferrer">Customer app</a>
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
