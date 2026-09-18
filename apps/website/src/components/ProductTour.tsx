import { useCallback, useEffect, useState } from "react";

export type ProductTourStep = {
  title: string;
  body: string;
};

function storageKey(id: string): string {
  return `kitchcu_tour_${id}_v3`;
}

export function isTourDismissed(id: string): boolean {
  try {
    return localStorage.getItem(storageKey(id)) === "1";
  } catch {
    return false;
  }
}

export function dismissTour(id: string): void {
  try {
    localStorage.setItem(storageKey(id), "1");
  } catch {
    /* private mode */
  }
}

export function resetTour(id: string): void {
  try {
    localStorage.removeItem(storageKey(id));
  } catch {
    /* private mode */
  }
  window.dispatchEvent(new CustomEvent("kitchcu-tour-replay", { detail: { id } }));
}

export function ProductTour({
  id,
  steps,
  skipLabel = "Skip",
  nextLabel = "Next",
  backLabel = "Back",
  doneLabel = "Got it",
  stepLabel,
}: {
  id: string;
  steps: ProductTourStep[];
  skipLabel?: string;
  nextLabel?: string;
  backLabel?: string;
  doneLabel?: string;
  stepLabel?: (current: number, total: number) => string;
}) {
  const [open, setOpen] = useState(() => !isTourDismissed(id));
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const onReplay = (ev: Event) => {
      const detail = (ev as CustomEvent<{ id?: string }>).detail;
      if (detail?.id && detail.id !== id) return;
      setIndex(0);
      setOpen(true);
    };
    window.addEventListener("kitchcu-tour-replay", onReplay);
    return () => window.removeEventListener("kitchcu-tour-replay", onReplay);
  }, [id]);

  const close = useCallback(() => {
    dismissTour(id);
    setOpen(false);
  }, [id]);

  if (!open || steps.length === 0) return null;
  const step = steps[index];
  const last = index === steps.length - 1;

  return (
    <div className="kc-tour" role="dialog" aria-modal="true" aria-labelledby={`kc-tour-${id}-title`}>
      <div className="kc-tour__card">
        <p className="kc-tour__count">
          {stepLabel ? stepLabel(index + 1, steps.length) : `${index + 1} / ${steps.length}`}
        </p>
        <h2 id={`kc-tour-${id}-title`}>{step.title}</h2>
        <p className="kc-tour__body">{step.body}</p>
        <div className="kc-tour__actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={close}>
            {skipLabel}
          </button>
          <div className="kc-tour__nav">
            {index > 0 ? (
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => setIndex((i) => i - 1)}>
                {backLabel}
              </button>
            ) : null}
            {last ? (
              <button type="button" className="btn btn--primary btn--sm" onClick={close}>
                {doneLabel}
              </button>
            ) : (
              <button type="button" className="btn btn--primary btn--sm" onClick={() => setIndex((i) => i + 1)}>
                {nextLabel}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function TourReplayButton({
  id,
  label = "Show tips",
}: {
  id: string;
  label?: string;
}) {
  return (
    <button type="button" className="btn btn--ghost btn--sm" onClick={() => resetTour(id)}>
      {label}
    </button>
  );
}
