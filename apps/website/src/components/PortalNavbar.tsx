import { useEffect, useState } from "react";
import { customerUrl, kitchenUrl } from "../shared/urls";

const links = [
  { href: "#features", label: "Features" },
  { href: "#pricing", label: "Pricing" },
  { href: "#support", label: "Support" },
  { href: "#contact", label: "Contact" },
  { href: "#apps", label: "Apps" },
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
        <a href="#top" className="nav__brand">
          <span className="nav__logo">kitchCU</span>
          <span className="nav__tagline">Cloud Kitchen Platform</span>
        </a>

        <nav className={`nav__links ${open ? "nav__links--open" : ""}`}>
          {links.map((l) => (
            <a key={l.href} href={l.href} onClick={() => setOpen(false)}>
              {l.label}
            </a>
          ))}
          <a href={customerUrl("/")} className="btn btn--ghost btn--sm" onClick={() => setOpen(false)}>
            Customer app
          </a>
          <a href={kitchenUrl("/login")} className="btn btn--primary btn--sm" onClick={() => setOpen(false)}>
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
