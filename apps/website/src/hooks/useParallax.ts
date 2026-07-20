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

export function useScrollProgress() {
  const [progress, setProgress] = useState(0);
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const doc = document.documentElement;
        const max = doc.scrollHeight - window.innerHeight;
        setScrollY(window.scrollY);
        setProgress(max > 0 ? window.scrollY / max : 0);
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  return { progress, scrollY };
}

/** Section-relative offset: positive when section center is below viewport center */
export function useSectionParallax(ref: RefObject<HTMLElement | null>) {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let raf = 0;
    const update = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const centerY = rect.top + rect.height * 0.5;
        setOffset(centerY - window.innerHeight * 0.5);
      });
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
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

export function useMouseParallax(intensity = 0.12) {
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth - 0.5) * intensity * 100;
      const y = (e.clientY / window.innerHeight - 0.5) * intensity * 100;
      setOffset({ x, y });
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
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
    if (!el) return;

    let raf = 0;
    const update = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const scrollable = el.offsetHeight - window.innerHeight;
        if (scrollable <= 0) {
          setProgress(0);
          return;
        }
        const scrolled = Math.min(scrollable, Math.max(0, -rect.top));
        setProgress(scrolled / scrollable);
      });
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [ref]);

  return progress;
}

/** Per-element vertical shift based on viewport position */
export function useItemParallax(ref: RefObject<HTMLElement | null>, speed = 0.12) {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let raf = 0;
    const update = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const center = rect.top + rect.height * 0.5;
        const viewCenter = window.innerHeight * 0.5;
        setOffset((center - viewCenter) * speed);
      });
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [ref, speed]);

  return offset;
}
