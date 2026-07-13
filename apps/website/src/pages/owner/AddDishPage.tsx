import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LiveCapturePhotoField } from "../../components/LiveCapturePhotoField";
import { createDish, fetchCategories, fetchCuisines, type Category, type Cuisine } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function AddDishPage() {
  const { kitchen } = useKitchen();
  const navigate = useNavigate();
  const [categories, setCategories] = useState<Category[]>([]);
  const [cuisines, setCuisines] = useState<Cuisine[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [heroUrl, setHeroUrl] = useState("");

  useEffect(() => {
    if (!kitchen) return;
    Promise.all([fetchCategories(kitchen.id), fetchCuisines(kitchen.id)])
      .then(([cats, cuis]) => {
        setCategories(cats);
        setCuisines(cuis);
      })
      .catch(() => {});
  }, [kitchen]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!kitchen) return;
    if (!heroUrl) {
      setError("Add a live-capture hero photo before saving.");
      return;
    }
    const fd = new FormData(e.currentTarget);
    setError("");
    setBusy(true);
    try {
      await createDish(kitchen.id, {
        name: String(fd.get("name")),
        price: Number(fd.get("price")),
        prep_time_min: Number(fd.get("prep_time_min") || 30),
        cuisine_id: String(fd.get("cuisine_id")),
        category_id: String(fd.get("category_id")),
        description: String(fd.get("description") || "") || undefined,
        ingredients_description: String(fd.get("ingredients") || "") || undefined,
        media: {
          url: heroUrl,
          is_hero: true,
          is_live_capture: true,
          captured_at: new Date().toISOString(),
        },
      });
      navigate("/dashboard/menu");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add dish");
    } finally {
      setBusy(false);
    }
  };

  if (!kitchen) return null;

  return (
    <div className="owner-page">
      <Link to="/dashboard/menu" className="owner-back">← Back to menu</Link>
      <header className="owner-page__head"><h1>Add dish</h1></header>

      <form className="glass owner-form owner-form--narrow" onSubmit={handleSubmit}>
        {error && <div className="auth-card__error">{error}</div>}
        <label>Dish name<input name="name" required placeholder="Butter Chicken" /></label>
        <div className="form-row">
          <label>Price (₹)<input name="price" type="number" min="1" step="1" required /></label>
          <label>Prep time (min)<input name="prep_time_min" type="number" min="5" defaultValue="30" /></label>
        </div>
        <label>
          Cuisine
          <select name="cuisine_id" required defaultValue={cuisines[0]?.id}>
            {cuisines.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <label>
          Diet (Veg / Non Veg)
          <select name="category_id" required defaultValue={categories.find((c) => c.slug === "veg")?.id}>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <label>Description<textarea name="description" rows={2} /></label>
        <label>Ingredients<textarea name="ingredients" rows={2} placeholder="Optional quality notes" /></label>

        <LiveCapturePhotoField
          kitchenId={kitchen.id}
          context="dish"
          label="Hero photo (live capture)"
          value={heroUrl}
          onChange={setHeroUrl}
          requireLiveCapture
        />

        <p className="auth-card__hint">
          Menu hierarchy: cuisine → veg/non-veg → dish. Hero images must be live-capture.
        </p>
        <button type="submit" className="btn btn--primary btn--lg" disabled={busy || !heroUrl}>
          {busy ? "Saving..." : "Add to menu"}
        </button>
      </form>
    </div>
  );
}
