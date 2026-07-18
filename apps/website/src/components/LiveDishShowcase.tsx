import { useEffect, useState } from "react";
import {
  fetchLiveShowcase,
  type LiveShowcase,
  type ShowcasePhase,
} from "../shared/api";

const PHASE_LABEL: Record<string, string> = {
  idle: "Idle",
  ingredients: "Ingredients",
  prep: "Prep",
  prepared: "Prepared",
};

type Props = {
  sessionId: string;
  /** Compact card for nearby lists; full panel for menu page */
  compact?: boolean;
  className?: string;
  pollMs?: number;
};

export function LiveDishShowcase({
  sessionId,
  compact = false,
  className = "",
  pollMs = 8000,
}: Props) {
  const [showcase, setShowcase] = useState<LiveShowcase | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await fetchLiveShowcase(sessionId);
        if (!cancelled) {
          setShowcase(data);
          setError("");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Live showcase unavailable");
          setShowcase(null);
        }
      }
    };
    load();
    const t = window.setInterval(load, pollMs);
    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, [sessionId, pollMs]);

  if (error && !showcase) {
    return compact ? null : (
      <div className={`live-showcase live-showcase--empty ${className}`}>
        <p>{error}</p>
      </div>
    );
  }
  if (!showcase?.dish_name) {
    return compact ? null : (
      <div className={`live-showcase live-showcase--empty ${className}`}>
        <p className="live-showcase__live">LIVE</p>
        <p>{showcase?.title || "Kitchen is live"}</p>
      </div>
    );
  }

  const phase = (showcase.showcase_phase || "idle") as ShowcasePhase | string;
  const phaseLabel = PHASE_LABEL[phase] || String(phase);

  if (compact) {
    return (
      <div className={`live-showcase live-showcase--compact ${className}`}>
        <span className="live-showcase__live">LIVE</span>
        <strong>{showcase.dish_name}</strong>
        <span className="live-showcase__phase">{phaseLabel}</span>
      </div>
    );
  }

  return (
    <section className={`live-showcase ${className}`} aria-live="polite">
      <header className="live-showcase__header">
        <span className="live-showcase__live">LIVE</span>
        <div>
          <h2>{showcase.dish_name}</h2>
          <p>
            {showcase.title} · <strong>{phaseLabel}</strong>
          </p>
        </div>
      </header>

      {phase === "ingredients" && (
        <div className="live-showcase__panel">
          <h3>Ingredients going in</h3>
          {showcase.ingredients.length === 0 ? (
            <p className="live-showcase__hint">Chef is lining up ingredients…</p>
          ) : (
            <ul className="live-showcase__list">
              {showcase.ingredients.map((ing) => (
                <li key={`${ing.sort_order}-${ing.ingredient_name}`}>
                  <strong>{ing.ingredient_name}</strong>
                  <span>
                    {ing.quantity} {ing.unit}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {phase === "prep" && (
        <div className="live-showcase__panel">
          <h3>Prep in progress</h3>
          {showcase.prep_steps.length === 0 ? (
            <p className="live-showcase__hint">Prep steps will appear as the chef advances.</p>
          ) : (
            <ol className="live-showcase__steps">
              {showcase.prep_steps.map((step) => {
                const active = showcase.active_prep_step_order === step.step_order;
                return (
                  <li
                    key={step.step_order}
                    className={active ? "live-showcase__step--active" : undefined}
                  >
                    <strong>{step.title || `Step ${step.step_order}`}</strong>
                    {step.body_html ? (
                      <span dangerouslySetInnerHTML={{ __html: step.body_html }} />
                    ) : null}
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      )}

      {phase === "prepared" && (
        <div className="live-showcase__panel live-showcase__panel--prepared">
          <h3>Prepared</h3>
          <p>
            {showcase.dish_name} is ready
            {showcase.prepared_at
              ? ` · marked ${new Date(showcase.prepared_at).toLocaleTimeString()}`
              : ""}
            .
          </p>
        </div>
      )}
    </section>
  );
}
