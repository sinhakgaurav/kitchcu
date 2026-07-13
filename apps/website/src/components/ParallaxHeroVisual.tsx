import { useRef } from "react";
import { useScrollProgress, useMouseParallax, useSectionParallax, parallaxTransform } from "../hooks/useParallax";
import { heroParallaxImages } from "../data/content";

export function ParallaxHeroVisual() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollY } = useScrollProgress();
  const sectionOffset = useSectionParallax(ref);
  const mouse = useMouseParallax(0.32);

  const baseOffset = scrollY * 0.85 + sectionOffset * 0.35;

  const layers = [
    { key: "back", ...heroParallaxImages.back, className: "hero-parallax__card hero-parallax__card--back", factor: 6, tilt: 0.04 },
    { key: "mid", ...heroParallaxImages.mid, className: "hero-parallax__card hero-parallax__card--mid", factor: 10, tilt: 0.06 },
    { key: "front", ...heroParallaxImages.front, className: "hero-parallax__card hero-parallax__card--main", factor: 14, tilt: 0.08 },
    { key: "accent", ...heroParallaxImages.accent, className: "hero-parallax__card hero-parallax__card--accent", factor: 18, tilt: 0.1 },
  ];

  return (
    <div ref={ref} className="hero-parallax">
      <div className="hero-parallax__frame" aria-hidden="true" />
      {layers.map((layer, i) => (
        <div
          key={layer.key}
          className={layer.className}
          style={{
            transform: parallaxTransform(baseOffset, layer.speed, mouse, layer.factor, { tilt: layer.tilt }),
            zIndex: i + 1,
          }}
        >
          <img src={layer.src} alt={layer.alt} loading={i === 0 ? "eager" : "lazy"} draggable={false} />
        </div>
      ))}
    </div>
  );
}
