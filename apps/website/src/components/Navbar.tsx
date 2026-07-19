import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { BrandNavMark } from "./BrandNavMark";
import { APP_TAGLINE } from "../shared/brand";
import { useAuth } from "../lib/auth";
import { customerUrl } from "../shared/urls";

const links = [
  { href: "/#for-owners", label: "Owners" },
  { href: "/#customers", label: "Customers" },
  { href: "/#features", label: "Features" },
  { href: "/#contact", label: "Contact" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const { token } = useAuth();
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const hashLink = (href: string) => (location.pathname !== "/" ? href : href.replace(/^\//, ""));

  return (
    <header className={`nav ${scrolled ? "nav--scrolled" : ""}`}>
      <div className="nav__inner container">
        <BrandNavMark to="/" subtitle={APP_TAGLINE} height={48} />

        <nav className={`nav__links ${open ? "nav__links--open" : ""}`}>
          {links.map((l) => (
            <a key={l.href} href={hashLink(l.href)} onClick={() => setOpen(false)}>{l.label}</a>
          ))}
          <a
            href={customerUrl("/browse")}
            className="btn btn--ghost btn--sm"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            Customers
          </a>
          <Link
            to={token ? "/dashboard" : "/login"}
            className="btn btn--primary btn--sm"
            onClick={() => setOpen(false)}
          >
            {token ? "Dashboard" : "Owner Login"}
          </Link>
        </nav>

        <button type="button" className="nav__toggle" aria-label="Toggle menu" aria-expanded={open} onClick={() => setOpen(!open)}>
          <span /><span /><span />
        </button>
      </div>
    </header>
  );
}
