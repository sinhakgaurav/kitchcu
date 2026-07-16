import { useRef } from "react";
import {
  parallaxTransform,
  useMouseParallax,
  useScrollProgress,
  useSectionParallax,
  useStaticMotion,
} from "../hooks/useParallax";
import { heroParallaxImages } from "../data/content";

type Props = {
  /** Spread cards across the full banner instead of copy-column only */
  fullBleed?: boolean;
};

/**
 * Cursor-following food cards for the home banner.
 * When fullBleed, spans the entire hero width (moves with cursor).
 * On phone / reduced-motion: static cards only (no scroll/cursor transforms).
 */
export function HeroCopyParallax({ fullBleed = false }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const staticMotion = useStaticMotion();
  const { scrollY } = useScrollProgress();
  const sectionOffset = useSectionParallax(ref);
  const mouse = useMouseParallax(staticMotion ? 0 : 0.62);
  const baseOffset = staticMotion ? 0 : scrollY * 0.55 + sectionOffset * 0.25;

  const layers = [
    {
      key: "a",
      ...heroParallaxImages.front,
      className: "hero-copy-parallax__card hero-copy-parallax__card--a",
      factor: 18,
      tilt: 0.09,
      speed: 0.45,
    },
    {
      key: "b",
      ...heroParallaxImages.accent,
      className: "hero-copy-parallax__card hero-copy-parallax__card--b",
      factor: 22,
      tilt: 0.11,
      speed: 0.66,
    },
    {
      key: "c",
      ...heroParallaxImages.mid,
      className: "hero-copy-parallax__card hero-copy-parallax__card--c",
      factor: 14,
      tilt: 0.07,
      speed: 0.38,
    },
    {
      key: "d",
      ...heroParallaxImages.back,
      className: "hero-copy-parallax__card hero-copy-parallax__card--d",
      factor: 16,
      tilt: 0.08,
      speed: 0.52,
    },
  ];

  return (
    <div
      ref={ref}
      className={`hero-copy-parallax${fullBleed ? " hero-copy-parallax--fullbleed" : ""}${staticMotion ? " hero-copy-parallax--static" : ""}`}
      aria-hidden="true"
    >
      {layers.map((layer) => (
        <div
          key={layer.key}
          className={layer.className}
          style={
            staticMotion
              ? undefined
              : {
                  transform: parallaxTransform(baseOffset, layer.speed, mouse, layer.factor, {
                    tilt: layer.tilt,
                  }),
                }
          }
        >
          <img src={layer.src} alt="" loading="lazy" draggable={false} />
        </div>
      ))}
    </div>
  );
}
