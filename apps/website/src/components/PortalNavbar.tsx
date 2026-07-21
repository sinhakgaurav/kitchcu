import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrandNavMark } from "./BrandNavMark";
import { LanguageSwitcher } from "../i18n/LanguageSwitcher";
import { APP_TAGLINE } from "../shared/brand";
import { customerUrl, kitchenUrl } from "../shared/urls";

export function PortalNavbar() {
  const { t } = useTranslation();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const links = [
    { href: "#apps", label: t("portal.navApps") },
    { href: "#features", label: t("portal.navFeatures") },
    { href: "#pricing", label: t("portal.navPricing") },
    { href: "#support", label: t("portal.navSupport") },
    { href: "#contact", label: t("portal.navContact") },
  ];

  return (
    <header className={`nav ${scrolled ? "nav--scrolled" : ""}`}>
      <div className="nav__inner container">
        <BrandNavMark href="/" subtitle={APP_TAGLINE} height={40} />

        <nav className={`nav__links ${open ? "nav__links--open" : ""}`}>
          {links.map((l) => {
            const href = l.href.startsWith("#") ? `/${l.href}` : l.href;
            return (
              <a key={l.href} href={href} onClick={() => setOpen(false)}>
                {l.label}
              </a>
            );
          })}
          <a
            href={customerUrl("/")}
            className="btn btn--ghost btn--sm nav__auth-btn"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            {t("common.customerApp")}
          </a>
          <a
            href={kitchenUrl("/login")}
            className="btn btn--primary btn--sm nav__auth-btn"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            {t("common.ownerLogin")}
          </a>
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
