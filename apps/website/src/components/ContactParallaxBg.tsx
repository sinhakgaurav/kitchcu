import { useRef } from "react";
import { heroParallaxImages, images } from "../data/content";
import { useItemParallax, useSectionParallax } from "../hooks/useParallax";

const LAYERS = [
  { src: heroParallaxImages.back.src, speed: 0.06, scale: 1.15, opacity: 0.22, className: "pl-contact-bg__layer--back" },
  { src: images.contact.src, speed: 0.12, scale: 1.08, opacity: 0.35, className: "pl-contact-bg__layer--main" },
  { src: heroParallaxImages.mid.src, speed: 0.18, scale: 1.05, opacity: 0.2, className: "pl-contact-bg__layer--mid" },
  { src: images.onboardMenu.src, speed: 0.24, scale: 1, opacity: 0.28, className: "pl-contact-bg__layer--accent" },
];

function ContactLayer({
  layer,
}: {
  layer: (typeof LAYERS)[number];
}) {
  const ref = useRef<HTMLDivElement>(null);
  const offset = useItemParallax(ref, layer.speed);

  return (
    <div
      ref={ref}
      className={`pl-contact-bg__layer ${layer.className}`}
      style={{
        opacity: layer.opacity,
        transform: `translate3d(0, ${offset}px, 0) scale(${layer.scale})`,
      }}
    >
      <img src={layer.src} alt="" loading="lazy" draggable={false} />
    </div>
  );
}

export function ContactParallaxBg() {
  const ref = useRef<HTMLDivElement>(null);
  const sectionOffset = useSectionParallax(ref);

  return (
    <div
      ref={ref}
      className="pl-contact-bg"
      aria-hidden="true"
      style={{ transform: `translate3d(0, ${sectionOffset * 0.05}px, 0)` }}
    >
      {LAYERS.map((layer) => (
        <ContactLayer key={layer.src} layer={layer} />
      ))}
      <div className="pl-contact-bg__veil" />
    </div>
  );
}
