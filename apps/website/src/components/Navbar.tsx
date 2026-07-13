import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { APP_NAME } from "../shared/brand";
import { useAuth } from "../lib/auth";

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
        <Link to="/" className="nav__brand">
          <span className="nav__logo">{APP_NAME}</span>
          <span className="nav__tagline">Cloud Kitchen Platform</span>
        </Link>

        <nav className={`nav__links ${open ? "nav__links--open" : ""}`}>
          {links.map((l) => (
            <a key={l.href} href={hashLink(l.href)} onClick={() => setOpen(false)}>{l.label}</a>
          ))}
          <Link to="/customers" className="btn btn--ghost btn--sm" onClick={() => setOpen(false)}>
            Customers
          </Link>
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
