/** Animated gradient orbs for auth / section backgrounds */
export function AnimatedMesh({ variant = "default" }: { variant?: "default" | "customer" | "kitchen" }) {
  return (
    <div className={`animated-mesh animated-mesh--${variant}`} aria-hidden="true">
      <span className="animated-mesh__orb animated-mesh__orb--1" />
      <span className="animated-mesh__orb animated-mesh__orb--2" />
      <span className="animated-mesh__orb animated-mesh__orb--3" />
    </div>
  );
}
