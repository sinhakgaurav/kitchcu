import { useRef } from "react";
import type { CSSProperties } from "react";
import { heroParallaxImages, images } from "../data/content";
import { useScrollProgress, useSectionParallax, useStaticMotion } from "../hooks/useParallax";

const STRIP = [
  images.menu,
  images.sushi,
  images.steak,
  images.heroSecondary,
  images.onboardMenu,
  images.customers,
  images.tacos,
  { src: heroParallaxImages.front.src, alt: heroParallaxImages.front.alt },
];

const slides = [...STRIP, ...STRIP];

type Props = {
  reverse?: boolean;
};

export function ParallaxDivider({ reverse = false }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const staticMotion = useStaticMotion();
  const { scrollY } = useScrollProgress();
  const sectionOffset = useSectionParallax(ref);
  const drift = staticMotion ? 0 : scrollY * 0.04 + sectionOffset * 0.12;

  return (
    <div
      ref={ref}
      className={`parallax-divider ${reverse ? "parallax-divider--reverse" : ""}${staticMotion ? " parallax-divider--static" : ""}`}
      aria-hidden="true"
    >
      <div
        className="parallax-divider__shift"
        style={
          staticMotion
            ? undefined
            : { transform: `translate3d(0, ${reverse ? drift * -0.5 : drift * 0.35}px, 0)` }
        }
      >
        <div className="parallax-divider__track">
          {slides.map((img, i) => (
            <div
              key={`${img.src}-${i}`}
              className="parallax-divider__slide"
              style={{ "--i": i % STRIP.length } as CSSProperties}
            >
              <img src={img.src} alt="" loading="lazy" draggable={false} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
