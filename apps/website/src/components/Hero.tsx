import { Link } from "react-router-dom";
import { BrandHeroArt } from "./BrandHeroArt";
import { BrandLogo } from "./BrandLogo";
import { HeroCopyParallax } from "./HeroCopyParallax";
import { ParallaxScene } from "./ParallaxScene";
import { stats } from "../data/content";
import {
  APP_NAME,
  APP_POSITIONING_SHORT,
  CUSTOMER_HOST,
  KITCHEN_HOST,
} from "../shared/brand";
import { customerUrl } from "../shared/urls";

type Props = {
  variant: "customer" | "kitchen";
};

/** Full-bleed marketing banner with cursor-follow imagery. */
export function Hero({ variant }: Props) {
  const isKitchen = variant === "kitchen";

  return (
    <>
      <section className="hero hero--fullbleed" id="top">
        <ParallaxScene variant="hero" />
        <HeroCopyParallax fullBleed />

        <div className="container hero__overlay hero__overlay--centered">
          <div className="hero__content hero__content--parallax hero__content--centered">
            <BrandLogo variant="icon" className="hero__banner-icon" alt={APP_NAME} />
            <p className="hero__positioning">{APP_POSITIONING_SHORT}</p>

            <h1 className="hero__title">
              {isKitchen ? (
                <>
                  Grow your kitchen.
                  <br />
                  <span className="gradient-text">Own every order.</span>
                </>
              ) : (
                <>
                  Delicious food,
                  <br />
                  <span className="gradient-text">from real kitchens.</span>
                </>
              )}
            </h1>

            <p className="hero__subtitle">
              {isKitchen
                ? "WhatsApp orders, live-capture menus, and owner dashboard — zero food commission."
                : "Browse live-capture menus from trusted cloud kitchens near you — home taste, fair fees."}
            </p>

            <div className="hero__actions">
              {isKitchen ? (
                <>
                  <Link to="/login" className="btn btn--primary btn--lg">
                    Owner sign in
                  </Link>
                  <a href={customerUrl("/")} className="btn btn--ghost btn--lg" target="_blank" rel="noopener noreferrer">
                    Customer app →
                  </a>
                </>
              ) : (
                <>
                  <a href="/#near-you" className="btn btn--primary btn--lg">
                    Order now
                  </a>
                  <Link to="/login" className="btn btn--ghost btn--lg">
                    Sign in →
                  </Link>
                </>
              )}
            </div>

            <ul className="hero__trust" aria-label="Highlights">
              {isKitchen ? (
                <>
                  <li><span className="hero__trust-dot" /> Zero food commission</li>
                  <li><span className="hero__trust-dot" /> WhatsApp + PWA orders</li>
                  <li><span className="hero__trust-dot" /> Live-capture menus</li>
                </>
              ) : (
                <>
                  <li><span className="hero__trust-dot" /> Live-capture dish photos</li>
                  <li><span className="hero__trust-dot" /> Home-taste kitchens</li>
                  <li><span className="hero__trust-dot" /> Track every order</li>
                </>
              )}
            </ul>

            {isKitchen && (
              <div className="hero__stats">
                {stats.map((s) => (
                  <div key={s.label} className="hero__stat">
                    <strong>{s.value}</strong>
                    <span>{s.label}</span>
                  </div>
                ))}
              </div>
            )}

            {!isKitchen && (
              <p className="hero__host-note">Browsing on {CUSTOMER_HOST}</p>
            )}
            {isKitchen && (
              <p className="hero__host-note">Owner hub on {KITCHEN_HOST}</p>
            )}
          </div>
        </div>

        <div className="hero__scroll-hint">
          <span>Scroll to explore</span>
          <div className="hero__scroll-line" />
        </div>
      </section>

      <section className="section brand-body-section" aria-label={`${APP_NAME} brand`}>
        <div className="container brand-body-section__inner">
          <BrandHeroArt surface={isKitchen ? "kitchen" : "customer"} />
          <div className="brand-body-section__copy">
            <span className="section__eyebrow">Brand</span>
            <h2>{isKitchen ? "Run the kitchen you built" : "Food you can trust"}</h2>
            <p>
              {isKitchen
                ? "Orders, menu, CRM, and growth tools in one place — so you can focus on cooking and customers, not commissions."
                : "Live-capture menus and fair delivery quotes from neighbourhood kitchens you can trust."}
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
