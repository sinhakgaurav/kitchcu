import { useRef } from "react";
import { images, sampleDishImages } from "../data/content";
import { useItemParallax, useSectionParallax } from "../hooks/useParallax";

const FLOATERS = [
  { src: images.sushi.src, top: "8%", left: "4%", width: "200px", speed: 0.14, rotate: "-8deg" },
  { src: images.tacos.src, top: "62%", left: "2%", width: "170px", speed: 0.2, rotate: "6deg" },
  { src: sampleDishImages.biryani, top: "18%", right: "3%", width: "190px", speed: 0.16, rotate: "10deg" },
  { src: sampleDishImages.thali, top: "70%", right: "6%", width: "160px", speed: 0.22, rotate: "-5deg" },
  { src: sampleDishImages.lassi, top: "42%", left: "38%", width: "130px", speed: 0.11, rotate: "4deg" },
];

function PricingFloater({
  photo,
}: {
  photo: (typeof FLOATERS)[number];
}) {
  const ref = useRef<HTMLDivElement>(null);
  const offset = useItemParallax(ref, photo.speed);

  return (
    <div
      ref={ref}
      className="pl-pricing-bg__photo"
      style={{
        top: photo.top,
        left: photo.left,
        right: photo.right,
        width: photo.width,
        transform: `translate3d(0, ${offset}px, 0) rotate(${photo.rotate})`,
      }}
    >
      <img src={photo.src} alt="" loading="lazy" draggable={false} />
    </div>
  );
}

export function PricingParallaxBg() {
  const ref = useRef<HTMLDivElement>(null);
  const sectionOffset = useSectionParallax(ref);

  return (
    <div
      ref={ref}
      className="pl-pricing-bg"
      aria-hidden="true"
      style={{ transform: `translate3d(0, ${sectionOffset * 0.08}px, 0)` }}
    >
      {FLOATERS.map((photo) => (
        <PricingFloater key={photo.src} photo={photo} />
      ))}
    </div>
  );
}
