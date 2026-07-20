import { useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { BrandNavMark } from "../components/BrandNavMark";
import { LanguageSwitcher } from "../i18n/LanguageSwitcher";
import { KITCHEN_HOST } from "../shared/brand";
import { fetchKitchenEntitlements } from "../shared/api";
import { useKitchenAuth } from "../shared/kitchenAuth";
import { useKitchen } from "../shared/kitchenContext";
import { customerUrl } from "../shared/urls";

type NavItem = { to: string; labelKey: string; end?: boolean; module?: string };

const NAV_SECTIONS: { labelKey: string; items: NavItem[] }[] = [
  {
    labelKey: "owner.nav.operations",
    items: [
      { to: "/dashboard", labelKey: "owner.nav.overview", end: true },
      { to: "/dashboard/orders", labelKey: "owner.nav.orders" },
      { to: "/dashboard/menu", labelKey: "owner.nav.menu" },
      { to: "/dashboard/brand", labelKey: "owner.nav.brand" },
      { to: "/dashboard/ingredients", labelKey: "owner.nav.ingredients" },
    ],
  },
  {
    labelKey: "owner.nav.growth",
    items: [
      { to: "/dashboard/reports", labelKey: "owner.nav.reports" },
      { to: "/dashboard/growth", labelKey: "owner.nav.intelligence" },
      { to: "/dashboard/crm", labelKey: "owner.nav.crm" },
      { to: "/dashboard/coupons", labelKey: "owner.nav.coupons" },
      { to: "/dashboard/tiffin", labelKey: "owner.nav.tiffin", module: "tiffin_plans" },
      { to: "/dashboard/templates", labelKey: "owner.nav.templates", module: "marketing_broadcast" },
      { to: "/dashboard/stream", labelKey: "owner.nav.stream", module: "streaming" },
    ],
  },
  {
    labelKey: "owner.nav.learn",
    items: [
      { to: "/dashboard/learning", labelKey: "owner.nav.learning" },
      { to: "/dashboard/community", labelKey: "owner.nav.community" },
    ],
  },
  {
    labelKey: "owner.nav.account",
    items: [
      { to: "/dashboard/subscription", labelKey: "owner.nav.subscription" },
      { to: "/dashboard/referrals", labelKey: "owner.nav.referrals" },
      { to: "/dashboard/whatsapp", labelKey: "owner.nav.whatsapp", module: "whatsapp" },
      { to: "/dashboard/payment-gateway", labelKey: "owner.nav.paymentGateway", module: "razorpay" },
      { to: "/dashboard/gst", labelKey: "owner.nav.gst" },
      { to: "/dashboard/setup", labelKey: "owner.nav.setup" },
    ],
  },
];

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token, loading } = useKitchenAuth();
  const { t } = useTranslation();
  if (loading) return <div className="app-loading">{t("owner.shell.loadingAuth")}</div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function OwnerLayout() {
  const { t } = useTranslation();
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
        if (!cancelled) setModules(null);
      });
    return () => {
      cancelled = true;
    };
  }, [kitchen?.id, token]);

  const visibleSections = useMemo(() => {
    return NAV_SECTIONS.map((section) => ({
      ...section,
      label: t(section.labelKey),
      items: section.items
        .filter((item) => {
          if (!item.module || modules == null) return true;
          return modules[item.module] !== false;
        })
        .map((item) => ({ ...item, label: t(item.labelKey) })),
    })).filter((section) => section.items.length > 0);
  }, [modules, t]);

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
        aria-label={t("common.closeMenu")}
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
            aria-label={t("common.closeMenu")}
            onClick={() => setNavOpen(false)}
          >
            ×
          </button>
        </div>

        {kitchens.length > 1 && (
          <label className="kc-field owner-app__kitchen-field">
            <span className="kc-field__label">{t("owner.shell.activeKitchen")}</span>
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
            <div key={section.labelKey} className="owner-app__nav-group">
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
          <a href={customerUrl("/")} className="owner-app__customer-link" target="_blank" rel="noopener noreferrer">
            {t("common.customerApp")}
          </a>
          <button type="button" className="owner-app__signout btn btn--ghost btn--sm" onClick={logout}>
            {t("common.signOut")}
          </button>
        </div>
      </aside>

      <div className="owner-app__shell">
        <header className="owner-app__topbar">
          <button
            type="button"
            className="owner-app__menu-btn"
            aria-expanded={navOpen}
            aria-label={t("common.openMenu")}
            onClick={() => setNavOpen(true)}
          >
            <span /><span /><span />
          </button>
          <div className="owner-app__topbar-text">
            <strong>{currentSection?.label ?? t("common.dashboard")}</strong>
            {kitchen && <span>{kitchen.name}</span>}
          </div>
        </header>

        <div className="owner-app__main">
          {loading ? (
            <div className="app-loading">{t("owner.shell.loadingKitchen")}</div>
          ) : (
            <Outlet context={{ kitchen }} />
          )}
        </div>
      </div>
    </div>
  );
}
