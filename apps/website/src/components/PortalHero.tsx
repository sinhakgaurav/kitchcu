import { BrandLogo } from "./BrandLogo";
import { HeroCopyParallax } from "./HeroCopyParallax";
import { ParallaxScene } from "./ParallaxScene";
import { APP_NAME, APP_POSITIONING } from "../shared/brand";
import { customerUrl, kitchenUrl } from "../shared/urls";

/** Full-bleed home banner — brand-first, single CTA group. */
export function PortalHero() {
  return (
    <section className="hero hero--fullbleed portal-hero-full" id="top">
      <ParallaxScene variant="hero" />
      <HeroCopyParallax fullBleed />

      <div className="container hero__overlay hero__overlay--centered">
        <div className="hero__content hero__content--parallax hero__content--centered">
          <BrandLogo variant="icon" className="hero__banner-icon" alt={APP_NAME} />
          <p className="hero__positioning">{APP_POSITIONING}</p>

          <h1 className="hero__title">
            <span className="gradient-text">{APP_NAME}</span>
          </h1>

          <p className="hero__subtitle">
            Growth OS for home chefs, tiffin services, and delivery-only kitchens —
            WhatsApp orders, live-capture menus, <strong>zero food commission</strong>.
          </p>

          <div className="hero__actions">
            <a
              href={kitchenUrl("/login")}
              className="btn btn--primary btn--lg"
              target="_blank"
              rel="noopener noreferrer"
            >
              Start as kitchen owner
            </a>
            <a
              href={customerUrl("/")}
              className="btn btn--ghost btn--lg"
              target="_blank"
              rel="noopener noreferrer"
            >
              Browse as customer →
            </a>
          </div>

          <ul className="hero__trust" aria-label="Highlights">
            <li>
              <span className="hero__trust-dot" /> Zero food commission
            </li>
            <li>
              <span className="hero__trust-dot" /> Owner-owned CRM
            </li>
            <li>
              <span className="hero__trust-dot" /> Honest prep & delivery times
            </li>
          </ul>
        </div>
      </div>

      <div className="hero__scroll-hint">
        <span>Scroll to explore</span>
        <div className="hero__scroll-line" />
      </div>
    </section>
  );
}
