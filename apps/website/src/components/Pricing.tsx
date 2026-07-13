import type { RefObject } from "react";
import { useInView } from "../hooks/useParallax";
import { pricingPlans } from "../data/content";
import { PricingParallaxBg } from "./PricingParallaxBg";

export function Pricing() {
  const { ref, visible } = useInView();

  return (
    <section className="section pricing pricing--parallax" id="pricing" ref={ref as RefObject<HTMLElement>}>
      <PricingParallaxBg />
      <div className="container pricing__inner">
        <div className={`section__header reveal reveal--blur ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">Pricing</span>
          <h2>Subscription plans — no food commission</h2>
          <p>
            Pay a flat monthly fee. Keep 100% of your food revenue. Scale when your kitchen grows.
          </p>
        </div>

        <div className={`pricing__grid reveal-stagger ${visible ? "reveal--visible" : ""}`}>
          {pricingPlans.map((plan) => (
            <article
              key={plan.id}
              className={`pricing-card glass ${plan.featured ? "pricing-card--featured" : ""}`}
            >
              {plan.featured && <span className="pricing-card__badge">Most popular</span>}
              <h3>{plan.name}</h3>
              <p className="pricing-card__desc">{plan.description}</p>
              <div className="pricing-card__price">
                <strong>₹{plan.price.toLocaleString("en-IN")}</strong>
                <span>/{plan.period}</span>
              </div>
              <ul className="pricing-card__features">
                {plan.features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              <a href="#contact" className={`btn ${plan.featured ? "btn--primary" : "btn--ghost"} btn--lg`}>
                {plan.cta}
              </a>
            </article>
          ))}
        </div>

        <p className={`pricing__note reveal ${visible ? "reveal--visible" : ""}`}>
          All plans include order lifecycle, live-capture menus, and customer menu links.
          Pilot kitchens get onboarding support. No hidden fees on orders.
        </p>
      </div>
    </section>
  );
}
