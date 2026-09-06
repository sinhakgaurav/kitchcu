import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrandNavMark } from "./BrandNavMark";
import { LanguageSwitcher } from "../i18n/LanguageSwitcher";
import { CUSTOMER_HOST } from "../shared/brand";
import { useCustomerAuth } from "../shared/customerAuth";
import { kitchenUrl } from "../shared/urls";
import { SuperAdminLink } from "./SuperAdminAccess";

export function CustomerNavbar() {
  const { t } = useTranslation();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const { session, logout } = useCustomerAuth();
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const hashLink = (href: string) => (location.pathname !== "/" ? href : href.replace(/^\//, ""));
  const accountLabel = (() => {
    const raw = (session?.name || "").trim();
    if (!raw) return t("customer.nav.account");
    const first = raw.split(/\s+/)[0] || raw;
    return first.length > 14 ? `${first.slice(0, 12)}…` : first;
  })();

  return (
    <header className={`nav nav--customer ${scrolled ? "nav--scrolled" : ""}`}>
      <div className="nav__inner container">
        <BrandNavMark to="/" subtitle={CUSTOMER_HOST} height={40} />

        <nav className={`nav__links ${open ? "nav__links--open" : ""}`}>
          <a href={hashLink("/#near-you")} onClick={() => setOpen(false)}>
            {t("customer.nav.nearYou")}
          </a>
          <a href={hashLink("/#cities")} onClick={() => setOpen(false)}>
            {t("cities.nav")}
          </a>
          <a href={hashLink("/#by-code")} onClick={() => setOpen(false)}>
            {t("customer.nav.kitchenCode")}
          </a>
          {session ? (
            <>
              <Link to="/orders" onClick={() => setOpen(false)}>
                {t("customer.nav.myOrders")}
              </Link>
              <Link to="/dashboard" onClick={() => setOpen(false)}>
                {t("customer.nav.dashboard")}
              </Link>
              <div className="nav__account">
                <Link
                  to="/dashboard?tab=account"
                  className="btn btn--primary btn--sm nav__auth-btn"
                  onClick={() => setOpen(false)}
                >
                  {accountLabel}
                </Link>
                <div className="nav__account-menu" role="menu" aria-label={t("customer.nav.account")}>
                  <Link to="/dashboard?tab=account" role="menuitem" onClick={() => setOpen(false)}>
                    {t("customer.nav.profile")}
                  </Link>
                  <Link
                    to="/dashboard?tab=account#notifications"
                    role="menuitem"
                    onClick={() => setOpen(false)}
                  >
                    {t("customer.nav.notifications")}
                  </Link>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      logout();
                      setOpen(false);
                    }}
                  >
                    {t("customer.nav.logout")}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <Link to="/login" className="btn btn--primary btn--sm nav__auth-btn" onClick={() => setOpen(false)}>
              {t("customer.nav.signIn")}
            </Link>
          )}
          <a
            href={kitchenUrl("/login")}
            className="nav__owner-link"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            {t("common.kitchenOwner")}
          </a>
          <SuperAdminLink className="nav__owner-link" onClick={() => setOpen(false)} />
          <LanguageSwitcher className="lang-switcher--nav" />
        </nav>

        <button
          type="button"
          className="nav__toggle"
          aria-label={t("common.toggleMenu")}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <span /><span /><span />
        </button>
      </div>
    </header>
  );
}
