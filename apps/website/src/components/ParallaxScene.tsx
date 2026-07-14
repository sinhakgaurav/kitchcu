import { useRef } from "react";
import type { CSSProperties } from "react";
import {
  parallaxTransform,
  useMouseParallax,
  useScrollProgress,
  useSectionParallax,
} from "../hooks/useParallax";
import { parallaxPhotos } from "../data/content";

type Props = {
  variant?: "hero" | "section";
};

const gradientLayers = [
  { speed: 0.08, className: "pl-layer pl-layer--deep" },
  { speed: 0.22, className: "pl-layer pl-layer--orbs" },
  { speed: 0.38, className: "pl-layer pl-layer--grid" },
  { speed: 0.52, className: "pl-layer pl-layer--shapes" },
  { speed: 0.68, className: "pl-layer pl-layer--particles" },
  { speed: 0.88, className: "pl-layer pl-layer--foreground" },
];

export function ParallaxScene({ variant = "hero" }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollY } = useScrollProgress();
  const sectionOffset = useSectionParallax(ref);
  const mouse = useMouseParallax(variant === "hero" ? 0.42 : 0.14);

  const baseOffset =
    variant === "hero" ? scrollY * 1.2 + sectionOffset * 0.45 : sectionOffset;
  const intensity = variant === "hero" ? 2.15 : 1.1;

  return (
    <div
      ref={ref}
      className={`parallax-scene parallax-scene--${variant}`}
      aria-hidden="true"
    >
      {gradientLayers.map((layer, i) => (
        <div
          key={layer.className}
          className={layer.className}
          style={{
            transform: parallaxTransform(
              baseOffset,
              layer.speed * intensity,
              mouse,
              (i + 1) * 2.5,
            ),
          }}
        />
      ))}

      {variant === "hero" &&
        parallaxPhotos.map((photo, i) => {
          const t = parallaxTransform(baseOffset, photo.speed * intensity, mouse, (i + 2) * 3);
          return (
            <div
              key={photo.src}
              className="pl-photo"
              style={{
                "--i": i,
                top: photo.top,
                left: photo.left,
                right: photo.right,
                width: photo.width,
                transform: `${t} rotate(${photo.rotate})`,
              } as CSSProperties}
            >
              <img src={photo.src} alt="" loading="eager" draggable={false} />
            </div>
          );
        })}

      <div
        className="pl-glow pl-glow--1"
        style={{
          transform: parallaxTransform(baseOffset, 0.15 * intensity, mouse, 4),
        }}
      />
      <div
        className="pl-glow pl-glow--2"
        style={{
          transform: parallaxTransform(baseOffset, 0.28 * intensity, mouse, 5),
        }}
      />
      <div
        className="pl-glow pl-glow--3"
        style={{
          transform: parallaxTransform(baseOffset, 0.4 * intensity, mouse, 3),
        }}
      />
    </div>
  );
}
