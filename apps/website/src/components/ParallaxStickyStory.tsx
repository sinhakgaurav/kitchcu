import { useRef, type MutableRefObject } from "react";
import type { CSSProperties } from "react";
import { customerShowcase, features } from "../data/content";
import { useInView, useSectionScrollProgress } from "../hooks/useParallax";

const STORY_PANELS = [
  {
    eyebrow: "Truth in media",
    title: "Live-capture menus customers trust",
    desc: customerShowcase[0].desc,
    image: customerShowcase[0].image,
    accent: "teal" as const,
  },
  {
    eyebrow: "WhatsApp-first",
    title: "Turn chat into confirmed orders",
    desc: features[0].desc,
    image: features[0].image,
    accent: "orange" as const,
  },
  {
    eyebrow: "Owner control",
    title: "Run every kitchen from one dashboard",
    desc: features[3].desc,
    image: features[3].image,
    accent: "orange" as const,
  },
  {
    eyebrow: "Local & honest",
    title: "Support neighbourhood cloud kitchens",
    desc: customerShowcase[1].desc,
    image: customerShowcase[1].image,
    accent: "teal" as const,
  },
];

export function ParallaxStickyStory() {
  const wrapRef = useRef<HTMLElement>(null);
  const progress = useSectionScrollProgress(wrapRef);
  const { ref: inViewRef, visible } = useInView(0.05);

  const activeIdx = Math.min(
    STORY_PANELS.length - 1,
    Math.floor(progress * STORY_PANELS.length),
  );

  return (
    <section
      className="pl-sticky-story"
      id="story"
      ref={(node) => {
        wrapRef.current = node;
        (inViewRef as MutableRefObject<HTMLElement | null>).current = node;
      }}
    >
      <div className="pl-sticky-story__pin">
        <div className="pl-sticky-story__visual" aria-hidden="true">
          {STORY_PANELS.map((panel, i) => {
            const distance = Math.abs(i - progress * (STORY_PANELS.length - 1));
            const opacity = Math.max(0, 1 - distance * 0.85);
            const scale = 1 + (1 - Math.min(1, distance)) * 0.06;
            const y = (i - progress * (STORY_PANELS.length - 1)) * 48;

            return (
              <div
                key={panel.title}
                className={`pl-sticky-story__frame pl-sticky-story__frame--${panel.accent}`}
                style={{
                  opacity,
                  transform: `translate3d(0, ${y}px, 0) scale(${scale})`,
                  zIndex: STORY_PANELS.length - i,
                }}
              >
                <img src={panel.image.src} alt="" loading="lazy" draggable={false} />
                <div className="pl-sticky-story__frame-shade" />
              </div>
            );
          })}
        </div>

        <div className={`pl-sticky-story__content ${visible ? "pl-sticky-story__content--visible" : ""}`}>
          <span className="section__eyebrow">The kitchCU story</span>
          {STORY_PANELS.map((panel, i) => (
            <article
              key={panel.title}
              className={`pl-sticky-story__panel ${i === activeIdx ? "pl-sticky-story__panel--active" : ""}`}
              style={{ "--i": i } as CSSProperties}
            >
              <span className="pl-sticky-story__step">0{i + 1}</span>
              <p className="pl-sticky-story__eyebrow">{panel.eyebrow}</p>
              <h2>{panel.title}</h2>
              <p>{panel.desc}</p>
            </article>
          ))}
        </div>

        <div className="pl-sticky-story__dots" aria-hidden="true">
          {STORY_PANELS.map((_, i) => (
            <span key={i} className={i === activeIdx ? "active" : ""} />
          ))}
        </div>
      </div>
    </section>
  );
}
