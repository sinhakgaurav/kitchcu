import type { CSSProperties, RefObject } from "react";
import { useInView } from "../hooks/useParallax";
import { howItWorks } from "../data/content";
import { ParallaxScene } from "./ParallaxScene";

type Props = {
  ctaHref?: string;
  ctaLabel?: string;
};

export function HowItWorks({ ctaHref = "/login", ctaLabel = "Start as kitchen owner" }: Props) {
  const { ref, visible } = useInView();

  return (
    <section className="section how-it-works how-it-works--parallax" id="how" ref={ref as RefObject<HTMLElement>}>
      <ParallaxScene variant="section" />
      <div className="container how-it-works__inner">
        <div className={`section__header reveal reveal--blur ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">How It Works</span>
          <h2>Go live in three simple steps</h2>
          <p>From registration to your first WhatsApp order in under five minutes.</p>
        </div>

        <div className={`how-it-works__grid reveal-stagger ${visible ? "reveal--visible" : ""}`}>
          {howItWorks.map((step, i) => (
            <article
              key={step.step}
              className="how-card glass"
              style={{ "--i": i } as CSSProperties}
            >
              <div className="how-card__image">
                <img src={step.image.src} alt={step.image.alt} loading="lazy" />
                <span className="how-card__step">{step.step}</span>
              </div>
              <div className="how-card__body">
                <h3>{step.title}</h3>
                <p>{step.desc}</p>
              </div>
            </article>
          ))}
        </div>

        <div className={`how-it-works__cta reveal ${visible ? "reveal--visible" : ""}`}>
          <a href={ctaHref} className="btn btn--primary btn--lg">
            {ctaLabel}
          </a>
        </div>
      </div>
    </section>
  );
}