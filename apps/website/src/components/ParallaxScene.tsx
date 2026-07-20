import { useRef } from "react";
import type { CSSProperties } from "react";
import {
  parallaxTransform,
  useMouseParallax,
  useScrollProgress,
  useSectionParallax,
  useStaticMotion,
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
  const staticMotion = useStaticMotion();
  const { scrollY } = useScrollProgress();
  const sectionOffset = useSectionParallax(ref);
  const mouse = useMouseParallax(staticMotion ? 0 : variant === "hero" ? 0.68 : 0.14);

  const baseOffset = staticMotion
    ? 0
    : variant === "hero"
      ? scrollY * 1.2 + sectionOffset * 0.45
      : sectionOffset;
  const intensity = variant === "hero" ? 2.15 : 1.1;

  return (
    <div
      ref={ref}
      className={`parallax-scene parallax-scene--${variant}${staticMotion ? " parallax-scene--static" : ""}`}
      aria-hidden="true"
    >
      {gradientLayers.map((layer, i) => (
        <div
          key={layer.className}
          className={layer.className}
          style={
            staticMotion
              ? undefined
              : {
                  transform: parallaxTransform(
                    baseOffset,
                    layer.speed * intensity,
                    mouse,
                    (i + 1) * 2.5,
                  ),
                }
          }
        />
      ))}

      {variant === "hero" &&
        parallaxPhotos.map((photo, i) => {
          const t = staticMotion
            ? undefined
            : parallaxTransform(baseOffset, photo.speed * intensity, mouse, (i + 3) * 5);
          return (
            <div
              key={photo.src}
              className="pl-photo"
              style={
                {
                  "--i": i,
                  top: photo.top,
                  left: photo.left,
                  width: photo.width,
                  transform: t
                    ? `${t} rotate(${photo.rotate})`
                    : `rotate(${photo.rotate})`,
                } as unknown as CSSProperties
              }
            >
              <img src={photo.src} alt="" loading="eager" draggable={false} />
            </div>
          );
        })}

      <div
        className="pl-glow pl-glow--1"
        style={
          staticMotion
            ? undefined
            : { transform: parallaxTransform(baseOffset, 0.15 * intensity, mouse, 4) }
        }
      />
      <div
        className="pl-glow pl-glow--2"
        style={
          staticMotion
            ? undefined
            : { transform: parallaxTransform(baseOffset, 0.28 * intensity, mouse, 5) }
        }
      />
      <div
        className="pl-glow pl-glow--3"
        style={
          staticMotion
            ? undefined
            : { transform: parallaxTransform(baseOffset, 0.4 * intensity, mouse, 3) }
        }
      />
    </div>
  );
}
