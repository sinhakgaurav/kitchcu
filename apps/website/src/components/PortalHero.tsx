import { BrandHeroArt } from "./BrandHeroArt";
import { BrandLogo } from "./BrandLogo";
import { HeroCopyParallax } from "./HeroCopyParallax";
import { ParallaxScene } from "./ParallaxScene";
import { APP_NAME, APP_POSITIONING, APP_TAGLINE } from "../shared/brand";
import { customerUrl, kitchenUrl } from "../shared/urls";

/** Full-bleed home banner — cursor-follow images across entire width. */
export function PortalHero() {
  return (
    <>
      <section className="hero hero--fullbleed portal-hero-full" id="top">
        <ParallaxScene variant="hero" />
        <HeroCopyParallax fullBleed />

        <div className="container hero__overlay hero__overlay--centered">
          <div className="hero__content hero__content--parallax hero__content--centered">
            <BrandLogo variant="icon" height={64} className="hero__banner-icon" alt={APP_NAME} />
            <p className="hero__brand-tagline">{APP_TAGLINE}</p>
            <p className="hero__positioning">{APP_POSITIONING}</p>

            <h1 className="hero__title">
              Grow your kitchen.
              <br />
              <span className="gradient-text">Trust home-made food.</span>
            </h1>

            <p className="hero__subtitle">
              Subscription Growth OS for home chefs, tiffin services, and delivery-only
              kitchens — WhatsApp orders, live-capture menus, and{" "}
              <strong>zero food commission</strong>.
            </p>

            <div className="hero__actions">
              <a href={kitchenUrl("/login")} className="btn btn--primary btn--lg">
                Start as kitchen owner
              </a>
              <a href={customerUrl("/")} className="btn btn--ghost btn--lg">
                Browse as customer →
              </a>
            </div>

            <ul className="hero__trust" aria-label="Highlights">
              <li><span className="hero__trust-dot" /> India's first in this stack</li>
              <li><span className="hero__trust-dot" /> World's third platform</li>
              <li><span className="hero__trust-dot" /> Zero food commission</li>
            </ul>
          </div>
        </div>

        <div className="hero__scroll-hint">
          <span>Scroll to explore</span>
          <div className="hero__scroll-line" />
        </div>
      </section>

      <section className="section brand-body-section" aria-label={`${APP_NAME} brand`}>
        <div className="container brand-body-section__inner">
          <BrandHeroArt surface="portal" />
          <div className="brand-body-section__copy">
            <span className="section__eyebrow">Brand</span>
            <h2>Built for kitchens that want to grow</h2>
            <p>
              {APP_NAME} is a Growth OS — not an aggregator. Owners keep their customers,
              run honest live-capture menus, and never pay a per-order food commission.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
