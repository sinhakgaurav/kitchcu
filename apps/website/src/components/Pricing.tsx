import type { RefObject } from "react";
import { useTranslation } from "react-i18next";
import { useInView } from "../hooks/useParallax";
import { pricingPlans } from "../data/content";
import { PricingParallaxBg } from "./PricingParallaxBg";

export function Pricing() {
  const { t } = useTranslation();
  const { ref, visible } = useInView();

  return (
    <section className="section pricing pricing--parallax" id="pricing" ref={ref as RefObject<HTMLElement>}>
      <PricingParallaxBg />
      <div className="container pricing__inner">
        <div className={`section__header reveal reveal--blur ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">{t("portal.pricingEyebrow")}</span>
          <h2>{t("portal.pricingTitle")}</h2>
          <p>{t("portal.pricingBody")}</p>
        </div>

        <div className={`pricing__grid reveal-stagger ${visible ? "reveal--visible" : ""}`}>
          {pricingPlans.map((plan) => (
            <article
              key={plan.id}
              className={`pricing-card glass ${plan.featured ? "pricing-card--featured" : ""}`}
            >
              {plan.featured && (
                <span className="pricing-card__badge">{t("portal.pricingPopular")}</span>
              )}
              <h3>{t(plan.nameKey)}</h3>
              <p className="pricing-card__desc">{t(plan.descKey)}</p>
              <div className="pricing-card__price">
                <strong>₹{plan.price.toLocaleString("en-IN")}</strong>
                <span>/{t("portal.pricingMonth")}</span>
              </div>
              <ul className="pricing-card__features">
                {plan.featureKeys.map((key) => (
                  <li key={key}>{t(key)}</li>
                ))}
              </ul>
              <a
                href="#contact"
                className={`btn ${plan.featured ? "btn--primary" : "btn--ghost"} btn--lg`}
              >
                {t(plan.ctaKey)}
              </a>
            </article>
          ))}
        </div>

        <p className={`pricing__note reveal ${visible ? "reveal--visible" : ""}`}>
          {t("portal.pricingNote")}
        </p>
      </div>
    </section>
  );
}
