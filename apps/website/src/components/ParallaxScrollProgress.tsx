import { useScrollProgress } from "../hooks/useParallax";

export function ParallaxScrollProgress() {
  const { progress } = useScrollProgress();

  return (
    <div className="pl-scroll-progress" aria-hidden="true">
      <div className="pl-scroll-progress__bar" style={{ transform: `scaleX(${progress})` }} />
    </div>
  );
}
