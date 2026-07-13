import type { CSSProperties, RefObject } from "react";
import { useInView } from "../hooks/useParallax";
import { customerShowcase } from "../data/content";
import { ParallaxImage } from "./ParallaxImage";

export function CustomerShowcase() {
  const { ref, visible } = useInView(0.1);

  return (
    <section className="section customer-showcase" ref={ref as RefObject<HTMLElement>}>
      <div className="container">
        <div className={`section__header reveal ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">Why customers love kitchCU</span>
          <h2>Honest menus. Zero markup games.</h2>
        </div>
        <div className={`customer-showcase__grid reveal-stagger ${visible ? "reveal--visible" : ""}`}>
          {customerShowcase.map((item, i) => (
            <article
              key={item.title}
              className="customer-showcase__card glass"
              style={{ "--i": i } as CSSProperties}
            >
              <ParallaxImage src={item.image.src} alt={item.image.alt} />
              <div className="customer-showcase__body">
                <h3>{item.title}</h3>
                <p>{item.desc}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
