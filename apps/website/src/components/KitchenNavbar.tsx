import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { BrandNavMark } from "./BrandNavMark";
import { KITCHEN_HOST } from "../shared/brand";
import { useKitchenAuth } from "../shared/kitchenAuth";
import { customerUrl } from "../shared/urls";

export function KitchenNavbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const { token } = useKitchenAuth();
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const hashLink = (href: string) => (location.pathname !== "/" ? href : href.replace(/^\//, ""));

  return (
    <header className={`nav nav--kitchen ${scrolled ? "nav--scrolled" : ""}`}>
      <div className="nav__inner container">
        <BrandNavMark to="/" subtitle={KITCHEN_HOST} height={32} />

        <nav className={`nav__links ${open ? "nav__links--open" : ""}`}>
          <a href={hashLink("/#features")} onClick={() => setOpen(false)}>Features</a>
          <a href={hashLink("/#how")} onClick={() => setOpen(false)}>How it works</a>
          <a href={customerUrl("/")} className="btn btn--ghost btn--sm" onClick={() => setOpen(false)}>
            Customer app →
          </a>
          <Link
            to={token ? "/dashboard" : "/login"}
            className="btn btn--primary btn--sm"
            onClick={() => setOpen(false)}
          >
            {token ? "Dashboard" : "Owner sign in"}
          </Link>
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
