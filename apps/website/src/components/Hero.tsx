import { Link } from "react-router-dom";
import { ParallaxScene } from "./ParallaxScene";
import { ParallaxHeroVisual } from "./ParallaxHeroVisual";
import { stats } from "../data/content";
import { CUSTOMER_HOST, KITCHEN_HOST } from "../shared/brand";
import { customerUrl, kitchenUrl } from "../shared/urls";

type Props = {
  variant: "customer" | "kitchen";
};

export function Hero({ variant }: Props) {
  const isKitchen = variant === "kitchen";

  return (
    <section className="hero" id="top">
      <ParallaxScene variant="hero" />

      <div className="container hero__layout">
        <div className="hero__content hero__content--parallax">
          <div className="hero__badge">
            <span className="pulse" />
            {isKitchen ? "For cloud kitchen owners" : "For hungry customers"}
          </div>

          <h1 className="hero__title">
            {isKitchen ? (
              <>
                Run your cloud kitchen
                <br />
                <span className="gradient-text">on {KITCHEN_HOST}</span>
              </>
            ) : (
              <>
                Discover home kitchens
                <br />
                <span className="gradient-text">on {CUSTOMER_HOST}</span>
              </>
            )}
          </h1>

          <p className="hero__subtitle">
            {isKitchen
              ? "WhatsApp orders, live-capture menus, and owner dashboard — zero food commission."
              : "Browse live-capture menus, trust what you order, and support local cloud kitchens."}
          </p>

          <div className="hero__actions">
            {isKitchen ? (
              <>
                <Link to="/login" className="btn btn--primary btn--lg">
                  Owner sign in
                </Link>
                <a href={customerUrl("/")} className="btn btn--ghost btn--lg">
                  Customer app →
                </a>
              </>
            ) : (
              <>
                <Link to="/login" className="btn btn--primary btn--lg">
                  Customer sign in
                </Link>
                <Link to="/#nearby" className="btn btn--ghost btn--lg">
                  Find a kitchen
                </Link>
              </>
            )}
          </div>

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
        </div>

        <ParallaxHeroVisual />
      </div>

      <div className="hero__scroll-hint">
        <span>Scroll to explore</span>
        <div className="hero__scroll-line" />
      </div>
    </section>
  );
}
