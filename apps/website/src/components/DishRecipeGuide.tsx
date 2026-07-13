import { useEffect, useState } from "react";
import { fetchDishRecipe, type DishRecipe } from "../lib/api";

type Props = {
  kitchenId: string;
  dishId: string;
  dishName: string;
  quantity?: number;
  defaultOpen?: boolean;
};

export function DishRecipeGuide({
  kitchenId,
  dishId,
  dishName,
  quantity = 1,
  defaultOpen = false,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [recipe, setRecipe] = useState<DishRecipe | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || recipe) return;
    setLoading(true);
    setError("");
    fetchDishRecipe(kitchenId, dishId)
      .then(setRecipe)
      .catch(() => setError("Could not load recipe"))
      .finally(() => setLoading(false));
  }, [open, kitchenId, dishId, recipe]);

  const hasContent =
    recipe && (recipe.lines.length > 0 || (recipe.prep_steps?.length ?? 0) > 0);

  return (
    <div className="owner-recipe-guide">
      <button type="button" className="owner-recipe-guide__toggle" onClick={() => setOpen((v) => !v)}>
        <span>
          {quantity > 1 ? `${quantity}× ` : ""}
          {dishName} — prep guide
        </span>
        <span>{open ? "Hide" : "Show"}</span>
      </button>

      {open && (
        <div className="owner-recipe-guide__body">
          {loading && <p className="owner-page__code">Loading recipe…</p>}
          {error && <p className="auth-card__error">{error}</p>}
          {!loading && !error && recipe && !hasContent && (
            <p className="owner-page__code">No recipe mapped yet — add ingredients & steps in Ingredients.</p>
          )}
          {recipe && hasContent && (
            <>
              {recipe.lines.length > 0 && (
                <div className="owner-recipe-guide__section">
                  <h4>Ingredients {quantity > 1 ? `(×${quantity})` : ""}</h4>
                  <ul className="owner-recipe-guide__lines">
                    {recipe.lines.map((line) => (
                      <li key={`${line.ingredient_id}-${line.sort_order}`}>
                        {line.photo_url && (
                          <img src={line.photo_url} alt="" className="owner-recipe-guide__thumb" />
                        )}
                        <span>
                          <strong>{line.ingredient_name}</strong> — {(line.quantity * quantity).toFixed(1)}
                          {line.unit}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {(recipe.prep_steps?.length ?? 0) > 0 && (
                <div className="owner-recipe-guide__section">
                  <h4>Preparation steps</h4>
                  <ol className="owner-recipe-guide__steps">
                    {recipe.prep_steps.map((step) => (
                      <li key={step.step_order}>
                        <div className="owner-recipe-guide__step-head">
                          <strong>
                            {step.step_order}. {step.title || "Step"}
                          </strong>
                          {step.duration_min != null && step.duration_min > 0 && (
                            <span className="owner-page__code">{step.duration_min} min</span>
                          )}
                        </div>
                        {step.body_html && (
                          <div
                            className="owner-recipe-guide__html"
                            dangerouslySetInnerHTML={{ __html: step.body_html }}
                          />
                        )}
                        {step.photo_url && (
                          <img src={step.photo_url} alt="" className="owner-recipe-preview" />
                        )}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );

}
