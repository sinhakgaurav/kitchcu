import { ParallaxScene } from "./ParallaxScene";
import { stats } from "../data/content";
import { customerUrl, kitchenUrl } from "../shared/urls";

export function PortalHero() {
  return (
    <section className="hero portal-hero-full" id="top">
      <ParallaxScene variant="hero" />

      <div className="container hero__layout">
        <div className="hero__content hero__content--parallax">
          <div className="hero__badge">
            <span className="pulse" />
            Built for cloud kitchens &amp; home food
          </div>

          <h1 className="hero__title">
            Grow your kitchen.
            <br />
            <span className="gradient-text">Trust home-made food.</span>
          </h1>

          <p className="hero__subtitle">
            kitchCU is the subscription platform for home chefs, tiffin services, and
            delivery-only kitchens — WhatsApp orders, live-capture menus, growth analytics,
            and <strong>zero food commission</strong>.
          </p>

          <div className="hero__actions">
            <a href={kitchenUrl("/login")} className="btn btn--primary btn--lg">
              Start as kitchen owner
            </a>
            <a href={customerUrl("/")} className="btn btn--ghost btn--lg">
              Browse as customer →
            </a>
          </div>

          <div className="hero__stats">
            {stats.map((s) => (
              <div key={s.label} className="hero__stat">
                <strong>{s.value}</strong>
                <span>{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="hero__scroll-hint">
        <span>Scroll to explore</span>
        <div className="hero__scroll-line" />
      </div>
    </section>
  );
}
