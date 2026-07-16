import { useEffect, useState } from "react";
import { BrandNavMark } from "./BrandNavMark";
import { APP_TAGLINE } from "../shared/brand";
import { customerUrl, kitchenUrl } from "../shared/urls";

const links = [
  { href: "#features", label: "Features" },
  { href: "#pricing", label: "Pricing" },
  { href: "#support", label: "Support" },
  { href: "#contact", label: "Contact" },
  { href: "#apps", label: "Apps" },
  { href: "/openapi", label: "API" },
];

export function PortalNavbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={`nav ${scrolled ? "nav--scrolled" : ""}`}>
      <div className="nav__inner container">
        <BrandNavMark href="#top" subtitle={APP_TAGLINE} height={34} />

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
            className="btn btn--ghost btn--sm"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            Customer app
          </a>
          <a
            href={kitchenUrl("/login")}
            className="btn btn--primary btn--sm"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            Owner login
          </a>
        </nav>

        <button
          type="button"
          className="nav__toggle"
          aria-label="Toggle menu"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <span /><span /><span />
        </button>
      </div>
    </header>
  );
}
