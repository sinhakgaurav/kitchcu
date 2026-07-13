import { useRef } from "react";
import type { CSSProperties } from "react";
import { useInView, useItemParallax } from "../hooks/useParallax";
import { customerGallery } from "../data/content";

function GalleryItem({
  item,
  index,
}: {
  item: (typeof customerGallery)[number];
  index: number;
}) {
  const ref = useRef<figure>(null);
  const offset = useItemParallax(ref, 0.1 + (index % 3) * 0.06);

  return (
    <figure
      ref={ref}
      className="floating-gallery__item"
      style={{ "--i": index, "--rot": item.rotate } as CSSProperties}
    >
      <div
        className="floating-gallery__item-inner"
        style={{ transform: `translate3d(0, ${offset}px, 0)` }}
      >
        <img src={item.src} alt={item.alt} loading="lazy" draggable={false} />
        <figcaption>{item.label}</figcaption>
      </div>
    </figure>
  );
}

export function FloatingGallery() {
  const { ref, visible } = useInView(0.08);

  return (
    <section
      className={`floating-gallery ${visible ? "floating-gallery--visible" : ""}`}
      ref={ref as React.RefObject<HTMLElement>}
      aria-label="Featured dishes"
    >
      <div className="floating-gallery__glow" aria-hidden="true" />
      <div className="container">
        <div className="floating-gallery__header reveal reveal--visible">
          <span className="section__eyebrow">Taste the difference</span>
          <h2>Real food from real kitchens</h2>
          <p>Every photo below is the kind of live-capture dish you&apos;ll see on kitchCU menus.</p>
        </div>
        <div className="floating-gallery__grid">
          {customerGallery.map((item, i) => (
            <GalleryItem key={item.src} item={item} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
