import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { BrandNavMark } from "./BrandNavMark";
import { CUSTOMER_HOST } from "../shared/brand";
import { useCustomerAuth } from "../shared/customerAuth";
import { kitchenUrl } from "../shared/urls";

export function CustomerNavbar() {
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
        <BrandNavMark to="/" subtitle={CUSTOMER_HOST} height={32} />

        <nav className={`nav__links ${open ? "nav__links--open" : ""}`}>
          <a href={hashLink("/#nearby")} onClick={() => setOpen(false)}>Nearby</a>
          <Link to="/orders" onClick={() => setOpen(false)}>My orders</Link>
          <Link to="/dashboard" onClick={() => setOpen(false)}>Dashboard</Link>
          <Link to="/account" onClick={() => setOpen(false)}>Payout details</Link>
          <a href={hashLink("/#discover")} onClick={() => setOpen(false)}>Find by code</a>
          <a href={hashLink("/#how")} onClick={() => setOpen(false)}>How it works</a>
          <Link to="/login" className="btn btn--ghost btn--sm" onClick={() => setOpen(false)}>
            {session ? session.name : "Customer sign in"}
          </Link>
          <a
            href={kitchenUrl("/login")}
            className="btn btn--primary btn--sm"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => setOpen(false)}
          >
            Kitchen owner →
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
