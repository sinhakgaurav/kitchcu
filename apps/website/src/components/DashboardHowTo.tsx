import { useState } from "react";

function storageKey(id: string): string {
  return `kitchcu_howto_${id}_v1`;
}

function readOpen(id: string, defaultOpen: boolean): boolean {
  try {
    const raw = localStorage.getItem(storageKey(id));
    if (raw === "0") return false;
    if (raw === "1") return true;
  } catch {
    /* private mode */
  }
  return defaultOpen;
}

export function DashboardHowTo({
  id,
  title,
  steps,
  defaultOpen = true,
}: {
  id: string;
  title: string;
  steps: string[];
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(() => readOpen(id, defaultOpen));
  if (steps.length === 0) return null;

  const toggle = () => {
    const next = !open;
    setOpen(next);
    try {
      localStorage.setItem(storageKey(id), next ? "1" : "0");
    } catch {
      /* private mode */
    }
  };

  return (
    <section className="kc-howto">
      <button type="button" className="kc-howto__toggle" onClick={toggle} aria-expanded={open}>
        <span>{title}</span>
        <span className="kc-howto__chevron" aria-hidden>
          {open ? "−" : "+"}
        </span>
      </button>
      {open ? (
        <ol className="kc-howto__steps">
          {steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

export function numberedI18n(
  t: (key: string, options?: Record<string, unknown>) => string,
  prefix: string,
  count: number,
): string[] {
  return Array.from({ length: count }, (_, i) => t(`${prefix}.s${i + 1}`));
}

export function tourI18n(
  t: (key: string, options?: Record<string, unknown>) => string,
  prefix: string,
  count: number,
): { title: string; body: string }[] {
  return Array.from({ length: count }, (_, i) => ({
    title: t(`${prefix}.s${i + 1}Title`),
    body: t(`${prefix}.s${i + 1}Body`),
  }));
}
