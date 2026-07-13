import { useRef } from "react";
import { parallaxTransform, useMouseParallax, useSectionParallax } from "../hooks/useParallax";

type Props = {
  src: string;
  alt: string;
  className?: string;
};

export function ParallaxImage({ src, alt, className = "" }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const offset = useSectionParallax(ref);
  const mouse = useMouseParallax(0.18);

  return (
    <div ref={ref} className={`parallax-image ${className}`.trim()}>
      <div
        className="parallax-image__inner"
        style={{
          transform: parallaxTransform(offset, 0.35, mouse, 12, { tilt: 0.05 }),
        }}
      >
        <img src={src} alt={alt} loading="lazy" draggable={false} />
      </div>
    </div>
  );
}
