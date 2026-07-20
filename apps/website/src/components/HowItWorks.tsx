import type { CSSProperties, RefObject } from "react";
import { useTranslation } from "react-i18next";
import { useInView } from "../hooks/useParallax";
import { howItWorksSteps } from "../data/content";
import { ParallaxScene } from "./ParallaxScene";

type Props = {
  ctaHref?: string;
  ctaLabel?: string;
};

export function HowItWorks({ ctaHref = "/login", ctaLabel }: Props) {
  const { t } = useTranslation();
  const { ref, visible } = useInView();
  const isCrossApp = ctaHref.startsWith("http");
  const label = ctaLabel ?? t("portal.ctaOwner");

  return (
    <section className="section how-it-works how-it-works--parallax" id="how" ref={ref as RefObject<HTMLElement>}>
      <ParallaxScene variant="section" />
      <div className="container how-it-works__inner">
        <div className={`section__header reveal reveal--blur ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">{t("portal.howEyebrow")}</span>
          <h2>{t("portal.howTitle")}</h2>
          <p>{t("portal.howBody")}</p>
        </div>

        <div className={`how-it-works__grid reveal-stagger ${visible ? "reveal--visible" : ""}`}>
          {howItWorksSteps.map((step, i) => (
            <article
              key={step.step}
              className="how-card glass"
              style={{ "--i": i } as CSSProperties}
            >
              <div className="how-card__image">
                <img src={step.image.src} alt={t(step.titleKey)} loading="lazy" />
                <span className="how-card__step">{step.step}</span>
              </div>
              <div className="how-card__body">
                <h3>{t(step.titleKey)}</h3>
                <p>{t(step.descKey)}</p>
              </div>
            </article>
          ))}
        </div>

        <div className={`how-it-works__cta reveal ${visible ? "reveal--visible" : ""}`}>
          <a
            href={ctaHref}
            className="btn btn--primary btn--lg"
            {...(isCrossApp ? { target: "_blank", rel: "noopener noreferrer" } : {})}
          >
            {label}
          </a>
        </div>
      </div>
    </section>
  );
}
