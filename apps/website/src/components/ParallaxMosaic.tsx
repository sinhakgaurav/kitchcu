import { useRef } from "react";
import type { CSSProperties } from "react";
import { customerGallery, sampleDishImages } from "../data/content";
import { useInView, useItemParallax } from "../hooks/useParallax";

const mosaicItems = [
  ...customerGallery.map((item, i) => ({
    src: item.src,
    alt: item.alt,
    label: item.label,
    speed: 0.08 + (i % 4) * 0.04,
    rotate: item.rotate,
    wide: i === 0 || i === 5,
    tall: i === 3 || i === 6,
  })),
  ...Object.entries(sampleDishImages).map(([key, src], i) => ({
    src,
    alt: key.replace(/([A-Z])/g, " $1"),
    label: key.replace(/([A-Z])/g, " $1").trim(),
    speed: 0.1 + (i % 3) * 0.05,
    rotate: `${(i % 5) - 2}deg`,
    wide: i % 7 === 0,
    tall: i % 5 === 2,
  })),
];

function MosaicTile({
  item,
  index,
}: {
  item: (typeof mosaicItems)[number];
  index: number;
}) {
  const ref = useRef<figure>(null);
  const offset = useItemParallax(ref, item.speed);

  return (
    <figure
      ref={ref}
      className={`pl-mosaic__tile ${item.wide ? "pl-mosaic__tile--wide" : ""} ${item.tall ? "pl-mosaic__tile--tall" : ""}`}
      style={{ "--i": index, "--rot": item.rotate } as CSSProperties}
    >
      <div
        className="pl-mosaic__tile-inner"
        style={{ transform: `translate3d(0, ${offset}px, 0) rotate(var(--rot))` }}
      >
        <img src={item.src} alt={item.alt} loading="lazy" draggable={false} />
        <figcaption>{item.label}</figcaption>
      </div>
    </figure>
  );
}

export function ParallaxMosaic() {
  const { ref, visible } = useInView(0.08);

  return (
    <section className="pl-mosaic" ref={ref as React.RefObject<HTMLElement>} aria-label="Food gallery mosaic">
      <div className="pl-mosaic__glow pl-mosaic__glow--1" aria-hidden="true" />
      <div className="pl-mosaic__glow pl-mosaic__glow--2" aria-hidden="true" />

      <div className="container">
        <div className={`pl-mosaic__header reveal reveal--blur ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">Visual feast</span>
          <h2>Every dish tells a story</h2>
          <p>
            Scroll through live-capture quality — the same honest imagery your customers
            see on kitchCU menus.
          </p>
        </div>

        <div className={`pl-mosaic__grid ${visible ? "pl-mosaic__grid--visible" : ""}`}>
          {mosaicItems.map((item, i) => (
            <MosaicTile key={`${item.src}-${i}`} item={item} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
