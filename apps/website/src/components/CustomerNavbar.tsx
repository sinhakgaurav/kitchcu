import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrandNavMark } from "./BrandNavMark";
import { LanguageSwitcher } from "../i18n/LanguageSwitcher";
import { CUSTOMER_HOST } from "../shared/brand";
import { useCustomerAuth } from "../shared/customerAuth";
import { kitchenUrl } from "../shared/urls";

export function CustomerNavbar() {
  const { t } = useTranslation();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const { session } = useCustomerAuth();
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const hashLink = (href: string) => (location.pathname !== "/" ? href : href.replace(/^\//, ""));

  return (
    <header className={`nav nav--customer ${scrolled ? "nav--scrolled" : ""}`}>
      <div className="nav__inner container">
        <BrandNavMark to="/" subtitle={CUSTOMER_HOST} height={44} />

        <nav className={`nav__links ${open ? "nav__links--open" : ""}`}>
          <a href={hashLink("/#near-you")} onClick={() => setOpen(false)}>{t("customer.nav.nearYou")}</a>
          <a href={hashLink("/#featured")} onClick={() => setOpen(false)}>{t("customer.nav.featured")}</a>
          <a href={hashLink("/#cheapest")} onClick={() => setOpen(false)}>{t("customer.nav.bestPrices")}</a>
          <a href={hashLink("/#by-code")} onClick={() => setOpen(false)}>{t("customer.nav.kitchenCode")}</a>
          <Link to="/orders" onClick={() => setOpen(false)}>{t("customer.nav.myOrders")}</Link>
          <Link to="/dashboard" onClick={() => setOpen(false)}>{t("customer.nav.dashboard")}</Link>
          <Link to="/account" onClick={() => setOpen(false)}>{t("customer.nav.account")}</Link>
          <Link to="/login" className="btn btn--ghost btn--sm" onClick={() => setOpen(false)}>
            {session ? session.name : t("customer.nav.signIn")}
          </Link>
          <a
            href={kitchenUrl("/login")}
            className="btn btn--primary btn--sm"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            {t("common.kitchenOwner")}
          </a>
          <LanguageSwitcher />
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
