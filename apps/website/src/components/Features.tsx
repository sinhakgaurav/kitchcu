import type { CSSProperties, RefObject } from "react";
import { useTranslation } from "react-i18next";
import { useInView } from "../hooks/useParallax";
import { featureCards } from "../data/content";
import { ParallaxScene } from "./ParallaxScene";

export function Features() {
  const { t } = useTranslation();
  const { ref, visible } = useInView();

  return (
    <section className="section features" id="features" ref={ref as RefObject<HTMLElement>}>
      <ParallaxScene variant="section" />

      <div className="container">
        <div className={`section__header reveal reveal--blur ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">{t("portal.featuresEyebrow")}</span>
          <h2>{t("portal.featuresTitle")}</h2>
          <p>{t("portal.featuresBody")}</p>
        </div>

        <div className={`features__grid reveal-stagger ${visible ? "reveal--visible" : ""}`}>
          {featureCards.map((f, i) => (
            <article
              key={f.titleKey}
              className="feature-card glass feature-card--with-image"
              style={{ "--i": i } as CSSProperties}
            >
              <div className="feature-card__image-wrap">
                <img src={f.image.src} alt={t(f.titleKey)} loading="lazy" />
              </div>
              <div className="feature-card__body">
                <h3>{t(f.titleKey)}</h3>
                <p>{t(f.descKey)}</p>
              </div>
              <div className="feature-card__shine" />
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
