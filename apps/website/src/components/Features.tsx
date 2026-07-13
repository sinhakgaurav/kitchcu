import type { CSSProperties, RefObject } from "react";
import { useInView } from "../hooks/useParallax";
import { features } from "../data/content";
import { ParallaxScene } from "./ParallaxScene";

export function Features() {
  const { ref, visible } = useInView();

  return (
    <section className="section features" id="features" ref={ref as RefObject<HTMLElement>}>
      <ParallaxScene variant="section" />

      <div className="container">
        <div className={`section__header reveal reveal--blur ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">Platform Features</span>
          <h2>Built for how cloud kitchens actually work</h2>
          <p>
            WhatsApp-first operations, honest menus, and owner control —
            without paying commission on every order.
          </p>
        </div>

        <div className={`features__grid reveal-stagger ${visible ? "reveal--visible" : ""}`}>
          {features.map((f, i) => (
            <article
              key={f.title}
              className="feature-card glass feature-card--with-image"
              style={{ "--i": i } as CSSProperties}
            >
              <div className="feature-card__image-wrap">
                <img src={f.image.src} alt={f.image.alt} loading="lazy" />
              </div>
              <div className="feature-card__body">
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
              <div className="feature-card__shine" />
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
