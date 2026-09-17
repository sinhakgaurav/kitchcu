import { useTranslation } from "react-i18next";
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
  let kcal = 0;
  let kcalKnown = false;
  let incomplete = false;
  let healthyAll = snapshots.length > 0;
  const seen = new Set<string>();
  const ingredients: DishHealthSnapshot["ingredients"] = [];
  for (const snap of snapshots) {
    const dishId = snap.dish_id ? String(snap.dish_id) : "";
    const qty = Math.max(1, (dishId ? qtyByDishId[dishId] : undefined) ?? 1);
    if (snap.calories_kcal != null) {
      kcal += snap.calories_kcal * qty;
      kcalKnown = true;
    }
    if (snap.calories_incomplete) incomplete = true;
    if (!snap.healthy_tag) healthyAll = false;
    if (snap.score == null || !dishId) continue;
    weight += qty;
    total += snap.score * qty;
    for (const line of snap.ingredients) {
      if (seen.has(line.name)) continue;
      seen.add(line.name);
      ingredients.push(line);
    }
  }
  if (!weight && !kcalKnown) return snapshots[0] ?? null;
  const score = weight ? Math.round(total / weight) : snapshots.find((s) => s.score != null)?.score ?? null;
  return {
    score,
    label:
      score == null
        ? snapshots[0]?.label || "Recipe not mapped"
        : score >= 80
          ? "Produce-forward"
          : score >= 65
            ? "Balanced plate"
            : score >= 50
              ? "Hearty plate"
              : "Richer plate",
    mapped: ingredients.length,
    total: ingredients.length,
    ingredients,
    calories_kcal: kcalKnown ? Math.round(kcal) : null,
    calories_incomplete: incomplete,
    healthy_tag: Boolean(healthyAll && kcalKnown && !incomplete),
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
  const { t } = useTranslation();
  if (!health) return null;
  const tone = healthTone(health.score);
  const kcal = health.calories_kcal;
  return (
    <div className={`dish-health dish-health--${tone}${compact ? " dish-health--compact" : ""}`}>
      <p className="dish-health__score">
        {health.healthy_tag ? <span className="dish-health__tag">{t("customer.dashboard.healthTag")}</span> : null}
        {kcal != null ? (
          <span className="dish-health__kcal">
            {t(
              health.calories_incomplete
                ? "customer.dashboard.healthCaloriesPartial"
                : "customer.dashboard.healthCalories",
              { kcal },
            )}
          </span>
        ) : null}
        {health.score != null ? (
          <>
            <strong>{health.score}</strong>
            <span>/100 · {health.label}</span>
          </>
        ) : (
          <span>{health.label}</span>
        )}
      </p>
      {!compact && health.calories_description ? (
        <p className="dish-health__note">{health.calories_description}</p>
      ) : null}
      {!compact && health.ingredients.length > 0 ? (
        <ul className="dish-health__list">
          {health.ingredients.slice(0, 24).map((ing) => (
            <li key={ing.name}>
              <strong>
                {ing.name}
                {ing.quantity != null ? ` · ${ing.quantity}${ing.unit || ""}` : ""}
                {ing.score > 0 ? ` · ${ing.score}` : ""}
                {ing.kcal != null ? ` · ${ing.kcal} kcal` : ""}
              </strong>
              {ing.benefits ? <span className="dish-health__pro">{ing.benefits}</span> : null}
              {ing.disadvantages ? <span className="dish-health__con">{ing.disadvantages}</span> : null}
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
