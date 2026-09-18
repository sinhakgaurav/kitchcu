import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LiveCapturePhotoField } from "../../components/LiveCapturePhotoField";
import { RichTextEditor } from "../../components/RichTextEditor";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  bulkImportDishes,
  createDish,
  downloadDishBulkTemplate,
  fetchCategories,
  fetchCuisines,
  type BulkDishImportResult,
  type Category,
  type Cuisine,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";
import { useTranslation } from "react-i18next";

export function AddDishPage() {
  const { t } = useTranslation();
  const { kitchen } = useKitchen();
  const navigate = useNavigate();
  const [categories, setCategories] = useState<Category[]>([]);
  const [cuisines, setCuisines] = useState<Cuisine[]>([]);
  const [cuisineId, setCuisineId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [heroUrl, setHeroUrl] = useState("");
  const [descriptionHtml, setDescriptionHtml] = useState("");
  const [ingredientsHtml, setIngredientsHtml] = useState("");
  const [caloriesNote, setCaloriesNote] = useState("");
  const [isFeatured, setIsFeatured] = useState(false);
  const [isChefsSpecial, setIsChefsSpecial] = useState(false);
  const [isUniqueRecipe, setIsUniqueRecipe] = useState(false);

  const [bulkSpreadsheet, setBulkSpreadsheet] = useState<File | null>(null);
  const [bulkImages, setBulkImages] = useState<File[]>([]);
  const [bulkZip, setBulkZip] = useState<File | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkError, setBulkError] = useState("");
  const [bulkResult, setBulkResult] = useState<BulkDishImportResult | null>(null);
  const [metaBusy, setMetaBusy] = useState(false);
  const sheetRef = useRef<HTMLInputElement>(null);
  const imagesRef = useRef<HTMLInputElement>(null);
  const zipRef = useRef<HTMLInputElement>(null);
  const metaReq = useRef(0);

  const loadMetadata = useCallback(() => {
    if (!kitchen) return;
    const kid = kitchen.id;
    const req = ++metaReq.current;
    setMetaBusy(true);
    Promise.all([fetchCategories(kid), fetchCuisines(kid)])
      .then(([catsRaw, cuisRaw]) => {
        if (req !== metaReq.current) return;
        const cats = Array.isArray(catsRaw) ? catsRaw : [];
        const cuis = Array.isArray(cuisRaw) ? cuisRaw : [];
        setCategories(cats);
        setCuisines(cuis);
        setCuisineId((prev) => prev || cuis[0]?.id || "");
        setCategoryId(
          (prev) => prev || cats.find((c) => c.slug === "veg")?.id || cats[0]?.id || "",
        );
        setError(cats.length && cuis.length ? "" : "Categories and cuisines did not load.");
      })
      .catch((err) => {
        if (req !== metaReq.current) return;
        setCategories([]);
        setCuisines([]);
        setError(err instanceof Error ? err.message : "Could not load categories and cuisines");
      })
      .finally(() => {
        if (req === metaReq.current) setMetaBusy(false);
      });
  }, [kitchen]);

  useEffect(() => {
    setCuisineId("");
    setCategoryId("");
  }, [kitchen?.id]);

  useEffect(() => {
    loadMetadata();
  }, [loadMetadata]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!kitchen) return;
    if (!categories.length || !cuisines.length || !cuisineId || !categoryId) {
      setError("Categories and cuisines are still loading. Retry if this persists.");
      return;
    }
    if (!heroUrl) {
      setError("Add a live-capture hero photo before saving.");
      return;
    }
    const fd = new FormData(e.currentTarget);
    setError("");
    setBusy(true);
    try {
      const prep = Number(fd.get("prep_time_min") || 30);
      const deliveryRaw = fd.get("delivery_time_min");
      const delivery =
        deliveryRaw === null || String(deliveryRaw).trim() === ""
          ? undefined
          : Number(deliveryRaw);
      const maxRaw = fd.get("max_time_min");
      const maxTime =
        maxRaw === null || String(maxRaw).trim() === ""
          ? prep + (delivery || 0)
          : Number(maxRaw);
      await createDish(kitchen.id, {
        name: String(fd.get("name")),
        price: Number(fd.get("price")),
        prep_time_min: prep,
        delivery_time_min: delivery,
        max_time_min: maxTime,
        cuisine_id: cuisineId,
        category_id: categoryId,
        description: descriptionHtml.trim() || undefined,
        ingredients_description: ingredientsHtml.trim() || undefined,
        calories_description: caloriesNote.trim() || undefined,
        is_featured: isFeatured,
        is_chefs_special: isChefsSpecial,
        is_unique_recipe: isUniqueRecipe,
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

  const onDownloadTemplate = async () => {
    if (!kitchen) return;
    setBulkError("");
    try {
      await downloadDishBulkTemplate(kitchen.id);
    } catch (err) {
      setBulkError(err instanceof Error ? err.message : "Template download failed");
    }
  };

  const onBulkImport = async () => {
    if (!kitchen || !bulkSpreadsheet) {
      setBulkError("Choose the filled Excel spreadsheet first.");
      return;
    }
    setBulkBusy(true);
    setBulkError("");
    setBulkResult(null);
    try {
      const result = await bulkImportDishes(kitchen.id, {
        spreadsheet: bulkSpreadsheet,
        images: bulkImages,
        imagesZip: bulkZip,
      });
      setBulkResult(result);
      if (result.accepted > 0) {
        setBulkSpreadsheet(null);
        setBulkImages([]);
        setBulkZip(null);
        if (sheetRef.current) sheetRef.current.value = "";
        if (imagesRef.current) imagesRef.current.value = "";
        if (zipRef.current) zipRef.current.value = "";
      }
    } catch (err) {
      setBulkError(err instanceof Error ? err.message : "Bulk import failed");
    } finally {
      setBulkBusy(false);
    }
  };

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow={t("owner.nav.operations")}
      title={t("owner.pages.addDish")}
      description={t("owner.pageDesc.addDish")}
      backTo="/dashboard/menu"
      backLabel="← Back to menu"
    >
      <OwnerPanel
        title={t("owner.panels.bulkUpload")}
        description="Download the sample Excel, fill rows, upload photos whose file names match the image_filename column."
      >
        {bulkError && <div className="auth-card__error">{bulkError}</div>}
        <ol className="owner-steps" style={{ marginTop: 0 }}>
          <li>Download the sample Excel (predefined column names + example rows).</li>
          <li>
            Fill dish details. Put the exact photo file name in <code>image_filename</code> (e.g.{" "}
            <code>paneer_butter_masala.jpg</code>).
          </li>
          <li>Upload the Excel plus images (multi-select) and/or a ZIP of images.</li>
          <li>
            Imported dishes stay <strong>inactive</strong> until you replace the gallery photo with a
            live-capture hero in Menu (truth in media).
          </li>
        </ol>
        <div className="owner-actions" style={{ flexWrap: "wrap", gap: "0.5rem" }}>
          <button type="button" className="btn btn--secondary" onClick={onDownloadTemplate}>
            Download sample Excel
          </button>
          <label className="btn btn--ghost">
            Choose Excel (.xlsx)
            <input
              ref={sheetRef}
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              hidden
              onChange={(e) => setBulkSpreadsheet(e.target.files?.[0] ?? null)}
            />
          </label>
          <label className="btn btn--ghost">
            Choose images
            <input
              ref={imagesRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              hidden
              onChange={(e) => setBulkImages(Array.from(e.target.files || []))}
            />
          </label>
          <label className="btn btn--ghost">
            Choose images ZIP
            <input
              ref={zipRef}
              type="file"
              accept=".zip,application/zip"
              hidden
              onChange={(e) => setBulkZip(e.target.files?.[0] ?? null)}
            />
          </label>
          <button
            type="button"
            className="btn btn--primary"
            disabled={bulkBusy || !bulkSpreadsheet}
            onClick={onBulkImport}
          >
            {bulkBusy ? "Importing…" : "Import dishes"}
          </button>
        </div>
        <p className="report-hint" style={{ marginTop: "0.75rem" }}>
          {bulkSpreadsheet ? `Sheet: ${bulkSpreadsheet.name}` : "No spreadsheet selected."}
          {bulkImages.length > 0 ? ` · ${bulkImages.length} image(s)` : ""}
          {bulkZip ? ` · ZIP: ${bulkZip.name}` : ""}
        </p>
        {bulkResult && (
          <div className="auth-card__success" style={{ marginTop: "0.75rem" }}>
            <p>
              Accepted {bulkResult.accepted} · rejected {bulkResult.rejected} · images mapped{" "}
              {bulkResult.images_mapped}
            </p>
            <p className="report-hint">{bulkResult.note}</p>
            {bulkResult.results.some((r) => r.status === "rejected") && (
              <ul className="owner-detail-items">
                {bulkResult.results
                  .filter((r) => r.status === "rejected")
                  .slice(0, 20)
                  .map((r) => (
                    <li key={`${r.row}-${r.name}`}>
                      Row {r.row}
                      {r.name ? ` (${r.name})` : ""}: {r.detail}
                    </li>
                  ))}
              </ul>
            )}
            {bulkResult.accepted > 0 && (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => navigate("/dashboard/menu")}
              >
                Open menu to add live heroes
              </button>
            )}
          </div>
        )}
      </OwnerPanel>

      <form className="dash-card owner-form owner-form--narrow" onSubmit={handleSubmit}>
        <h2 className="owner-panel__title" style={{ marginTop: 0 }}>
          Add one dish
        </h2>
        {error && <div className="auth-card__error">{error}</div>}
        {(!categories.length || !cuisines.length) && (
          <p className="owner-muted">
            {metaBusy ? "Loading categories and cuisines…" : "Menu metadata did not load."}{" "}
            <button type="button" className="btn btn--ghost btn--sm" onClick={loadMetadata} disabled={metaBusy}>
              Retry
            </button>
          </p>
        )}
        <label>Dish name<input name="name" required placeholder="Butter Chicken" /></label>
        <div className="form-row">
          <label>Price (₹)<input name="price" type="number" min="1" step="1" required /></label>
          <label>
            Prep time (min)
            <input name="prep_time_min" type="number" min="5" defaultValue="30" required />
          </label>
        </div>
        <div className="form-row">
          <label>
            Delivery time (min)
            <input
              name="delivery_time_min"
              type="number"
              min="0"
              defaultValue="20"
              placeholder="e.g. 20"
            />
          </label>
          <label>
            Max time customers see (min)
            <input
              name="max_time_min"
              type="number"
              min="5"
              defaultValue="50"
              title="Projected ready-within time. Defaults to prep + delivery. Cart uses the max across dishes."
              required
            />
          </label>
        </div>
        <p className="auth-card__hint">
          Prep is kitchen work. Delivery is the travel window. Max time is what customers see as
          “ready within” — multi-dish carts use the longest max (quality-first, not a race).
        </p>
        <label>
          Cuisine
          <select name="cuisine_id" required value={cuisineId} onChange={(e) => setCuisineId(e.target.value)}>
            {cuisines.length === 0 ? <option value="">Loading…</option> : null}
            {cuisines.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <label>
          Diet (Veg / Non Veg)
          <select name="category_id" required value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            {categories.length === 0 ? <option value="">Loading…</option> : null}
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>
        <div className="kc-field">
          <span className="kc-field__label">Description</span>
          <RichTextEditor
            value={descriptionHtml}
            onChange={setDescriptionHtml}
            kitchenId={kitchen.id}
            uploadContext="dish"
            placeholder="What makes this dish special — texture, spice level, serving size…"
            minHeight={100}
          />
        </div>

        <div className="kc-field">
          <span className="kc-field__label">Ingredients & quality notes</span>
          <RichTextEditor
            value={ingredientsHtml}
            onChange={setIngredientsHtml}
            kitchenId={kitchen.id}
            uploadContext="dish"
            placeholder="Key ingredients, allergens, quality notes — add photos inline if helpful"
            minHeight={100}
          />
        </div>

        <label>
          Calories note (optional)
          <input
            value={caloriesNote}
            maxLength={500}
            onChange={(e) => setCaloriesNote(e.target.value)}
            placeholder="Light lunch bowl — dal + greens. The kcal number comes from the recipe map."
          />
        </label>
        <p className="auth-card__hint">
          Plate calories are calculated from pantry kcal × recipe amounts on Ingredients. This note
          is shown next to that total — you cannot type the number or pin a Healthy tag.
        </p>

        <LiveCapturePhotoField
          kitchenId={kitchen.id}
          context="dish"
          label="Hero photo (live capture)"
          value={heroUrl}
          onChange={setHeroUrl}
          requireLiveCapture
        />

        <fieldset className="dish-highlight-fieldset">
          <legend>Menu highlights</legend>
          <p className="auth-card__hint">
            Customers see these as Featured, Chef&apos;s special, and Unique recipe sections.
          </p>
          <label className="dish-highlight-check">
            <input
              type="checkbox"
              checked={isFeatured}
              onChange={(e) => setIsFeatured(e.target.checked)}
            />
            Featured
          </label>
          <label className="dish-highlight-check">
            <input
              type="checkbox"
              checked={isChefsSpecial}
              onChange={(e) => setIsChefsSpecial(e.target.checked)}
            />
            Chef&apos;s special
          </label>
          <label className="dish-highlight-check">
            <input
              type="checkbox"
              checked={isUniqueRecipe}
              onChange={(e) => setIsUniqueRecipe(e.target.checked)}
            />
            Unique recipe
          </label>
        </fieldset>

        <p className="auth-card__hint">
          Menu hierarchy: cuisine → veg/non-veg → dish. Hero images must be live-capture.
        </p>
        {!heroUrl ? (
          <p className="auth-card__hint">Open the camera and capture a live hero photo to save this dish.</p>
        ) : null}
        <button
          type="submit"
          className="btn btn--primary btn--lg"
          disabled={busy}
          aria-busy={busy}
        >
          {busy ? "Saving..." : "Add to menu"}
        </button>
      </form>
    </OwnerPageShell>
  );
}
