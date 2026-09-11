import { useEffect, useRef, useState, type RefObject } from "react";

/** True on narrow screens, touch/coarse pointers, or prefers-reduced-motion — skip JS parallax. */
export function useStaticMotion(): boolean {
  const [staticMotion, setStaticMotion] = useState(() => {
    if (typeof window === "undefined") return false;
    return (
      window.matchMedia("(max-width: 900px)").matches ||
      window.matchMedia("(pointer: coarse)").matches ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  });

  useEffect(() => {
    const mq = [
      window.matchMedia("(max-width: 900px)"),
      window.matchMedia("(pointer: coarse)"),
      window.matchMedia("(prefers-reduced-motion: reduce)"),
    ];
    const sync = () => setStaticMotion(mq.some((m) => m.matches));
    sync();
    mq.forEach((m) => m.addEventListener("change", sync));
    return () => mq.forEach((m) => m.removeEventListener("change", sync));
  }, []);

  return staticMotion;
}

/** Scroll-driven hooks re-render on every animation frame, so skip them entirely where
 *  parallax is not rendered anyway: small screens, touch, and reduced-motion. */
function skipScrollWork(): boolean {
  if (typeof window === "undefined") return true;
  return (
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
    window.matchMedia("(pointer: coarse)").matches ||
    window.matchMedia("(max-width: 900px)").matches
  );
}

const scrollSubscribers = new Set<() => void>();
let scrollRaf = 0;
let scrollBound = false;

function flushScrollSubscribers() {
  scrollRaf = 0;
  for (const run of scrollSubscribers) run();
}

function onSharedScroll() {
  if (scrollRaf) return;
  scrollRaf = requestAnimationFrame(flushScrollSubscribers);
}

/**
 * One scroll/resize listener and one animation frame for every parallax hook on the page.
 *
 * The portal home mounts around twenty of these hooks. Giving each its own listener,
 * its own frame, and its own `getBoundingClientRect()` interleaved reads with React
 * writes on every frame, which is what made scrolling stutter. Batching the reads into
 * a single frame also lets React collapse the resulting state updates into one render.
 */
function subscribeToScroll(run: () => void): () => void {
  scrollSubscribers.add(run);
  if (!scrollBound) {
    window.addEventListener("scroll", onSharedScroll, { passive: true });
    window.addEventListener("resize", onSharedScroll, { passive: true });
    scrollBound = true;
  }
  run();
  return () => {
    scrollSubscribers.delete(run);
    if (scrollSubscribers.size > 0 || !scrollBound) return;
    window.removeEventListener("scroll", onSharedScroll);
    window.removeEventListener("resize", onSharedScroll);
    scrollBound = false;
    if (scrollRaf) {
      cancelAnimationFrame(scrollRaf);
      scrollRaf = 0;
    }
  };
}

/** Subscribe to the shared scroll frame; exported for non-parallax scroll state. */
export function useScrollEffect(run: () => void, deps: unknown[] = []) {
  useEffect(() => {
    if (typeof window === "undefined") return;
    return subscribeToScroll(run);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

export function useScrollProgress() {
  const [progress, setProgress] = useState(0);
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      (window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
        window.matchMedia("(max-width: 900px)").matches)
    ) {
      return;
    }
    return subscribeToScroll(() => {
      const doc = document.documentElement;
      const max = doc.scrollHeight - window.innerHeight;
      setScrollY(Math.round(window.scrollY));
      setProgress(max > 0 ? Math.round((window.scrollY / max) * 1000) / 1000 : 0);
    });
  }, []);

  return { progress, scrollY };
}

/** Section-relative offset: positive when section center is below viewport center */
export function useSectionParallax(ref: RefObject<HTMLElement | null>) {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el || skipScrollWork()) return;

    return subscribeToScroll(() => {
      const rect = el.getBoundingClientRect();
      const centerY = rect.top + rect.height * 0.5;
      // Whole pixels only — sub-pixel churn re-renders without changing what is drawn.
      setOffset(Math.round(centerY - window.innerHeight * 0.5));
    });
  }, [ref]);

  return offset;
}

export function useInView(threshold = 0.15) {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setVisible(true);
      },
      { threshold, rootMargin: "0px 0px -8% 0px" },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);

  return { ref, visible };
}

export function useMouseParallax(intensity = 0.06) {
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      (window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
        window.matchMedia("(pointer: coarse)").matches ||
        window.matchMedia("(max-width: 900px)").matches)
    ) {
      return;
    }
    let raf = 0;
    let latest: MouseEvent | null = null;
    const flush = () => {
      raf = 0;
      if (!latest) return;
      const e = latest;
      latest = null;
      const x = (e.clientX / window.innerWidth - 0.5) * intensity * 100;
      const y = (e.clientY / window.innerHeight - 0.5) * intensity * 100;
      setOffset({ x, y });
    };
    const onMove = (e: MouseEvent) => {
      latest = e;
      if (!raf) raf = requestAnimationFrame(flush);
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMove);
    };
  }, [intensity]);

  return offset;
}

export function parallaxTransform(
  scrollOffset: number,
  speed: number,
  mouse: { x: number; y: number },
  mouseFactor: number,
  options?: { tilt?: number },
): string {
  const y = scrollOffset * speed + mouse.y * mouseFactor;
  const x = mouse.x * mouseFactor * 0.85;
  const tilt = options?.tilt ? mouse.x * options.tilt : 0;
  return `translate3d(${x}px, ${y}px, 0) rotate(${tilt}deg)`;
}

/** 0→1 progress while scrolling through a tall section (for sticky parallax stories) */
export function useSectionScrollProgress(ref: RefObject<HTMLElement | null>) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el || skipScrollWork()) return;

    return subscribeToScroll(() => {
      const rect = el.getBoundingClientRect();
      const scrollable = el.offsetHeight - window.innerHeight;
      if (scrollable <= 0) {
        setProgress(0);
        return;
      }
      const scrolled = Math.min(scrollable, Math.max(0, -rect.top));
      setProgress(Math.round((scrolled / scrollable) * 1000) / 1000);
    });
  }, [ref]);

  return progress;
}

/** Per-element vertical shift based on viewport position */
export function useItemParallax(ref: RefObject<HTMLElement | null>, speed = 0.12) {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el || skipScrollWork()) return;

    return subscribeToScroll(() => {
      const rect = el.getBoundingClientRect();
      const center = rect.top + rect.height * 0.5;
      const viewCenter = window.innerHeight * 0.5;
      setOffset(Math.round((center - viewCenter) * speed));
    });
  }, [ref, speed]);

  return offset;
}
