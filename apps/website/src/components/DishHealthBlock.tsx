import type { DishHealthSnapshot } from "../shared/api";

export function healthTone(score: number | null | undefined): "good" | "ok" | "rich" | "none" {
  if (score == null) return "none";
  if (score >= 70) return "good";
  if (score >= 50) return "ok";
  return "rich";
}

export function aggregateOrderedHealth(
  snapshots: DishHealthSnapshot[],
  qtyByDishId: Record<string, number>,
): DishHealthSnapshot | null {
  let weight = 0;
  let total = 0;
  const seen = new Set<string>();
  const ingredients: DishHealthSnapshot["ingredients"] = [];
  for (const snap of snapshots) {
    const dishId = snap.dish_id ? String(snap.dish_id) : "";
    if (snap.score == null || !dishId) continue;
    const qty = Math.max(1, qtyByDishId[dishId] ?? 1);
    weight += qty;
    total += snap.score * qty;
    for (const line of snap.ingredients) {
      if (seen.has(line.name)) continue;
      seen.add(line.name);
      ingredients.push(line);
    }
  }
  if (!weight) return snapshots[0] ?? null;
  const score = Math.round(total / weight);
  return {
    score,
    label:
      score >= 80 ? "Produce-forward" : score >= 65 ? "Balanced plate" : score >= 50 ? "Hearty plate" : "Richer plate",
    mapped: ingredients.length,
    total: ingredients.length,
    ingredients,
    disclaimer:
      snapshots[0]?.disclaimer ||
      "Typical home-kitchen use from the recipe map — not medical advice or a lab nutrition label.",
  };
}

export function DishHealthBlock({
  health,
  compact,
}: {
  health: DishHealthSnapshot | null | undefined;
  compact?: boolean;
}) {
  if (!health) return null;
  const tone = healthTone(health.score);
  return (
    <div className={`dish-health dish-health--${tone}${compact ? " dish-health--compact" : ""}`}>
      <p className="dish-health__score">
        {health.score != null ? (
          <>
            <strong>{health.score}</strong>
            <span>/100 · {health.label}</span>
          </>
        ) : (
          <span>{health.label}</span>
        )}
      </p>
      {!compact && health.ingredients.length > 0 ? (
        <ul className="dish-health__list">
          {health.ingredients.slice(0, 24).map((ing) => (
            <li key={ing.name}>
              <strong>
                {ing.name}
                {ing.quantity != null ? ` · ${ing.quantity}${ing.unit || ""}` : ""} · {ing.score}
              </strong>
              <span className="dish-health__pro">{ing.benefits}</span>
              <span className="dish-health__con">{ing.disadvantages}</span>
            </li>
          ))}
          {health.ingredients.length > 24 ? (
            <li>
              <span>And {health.ingredients.length - 24} more mapped ingredients</span>
            </li>
          ) : null}
        </ul>
      ) : null}
      {!compact ? <p className="dish-health__disclaimer">{health.disclaimer}</p> : null}
    </div>
  );
}
