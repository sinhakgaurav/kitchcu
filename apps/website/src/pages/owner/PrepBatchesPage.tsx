import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { ListingToolbar } from "../../components/ListingToolbar";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  createPrepBatch,
  fetchKitchenStockSettings,
  fetchMenu,
  fetchPrepBatches,
  markPrepBatchPrepared,
  updateKitchenStockSettings,
  updatePrepBatch,
  type PrepBatch,
  type PrepBatchIngredientLine,
  type StockDeductMode,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

export function PrepBatchesPage() {
  const { kitchen } = useKitchen();
  const [batches, setBatches] = useState<PrepBatch[]>([]);
  const [dishes, setDishes] = useState<{ id: string; name: string }[]>([]);
  const [deductMode, setDeductMode] = useState<StockDeductMode>("order_ready");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState("Morning bulk cook");
  const [batchType, setBatchType] = useState<"single_dish" | "combo">("combo");
  const [portions, setPortions] = useState("20");
  const [selectedDishIds, setSelectedDishIds] = useState<string[]>([]);
  const [editing, setEditing] = useState<PrepBatch | null>(null);
  const [editLines, setEditLines] = useState<PrepBatchIngredientLine[]>([]);
  const [batchSearch, setBatchSearch] = useState("");
  const [batchSort, setBatchSort] = useState<"newest" | "name_asc" | "portions_desc">("newest");
  const [batchFilter, setBatchFilter] = useState("");

  const load = async () => {
    if (!kitchen) return;
    setLoading(true);
    setError("");
    try {
      const [batchOut, menuOut, settingsOut] = await Promise.allSettled([
        fetchPrepBatches(kitchen.id),
        fetchMenu(kitchen.id),
        fetchKitchenStockSettings(kitchen.id),
      ]);
      if (batchOut.status === "fulfilled") setBatches(batchOut.value.batches);
      if (menuOut.status === "fulfilled") {
        setDishes(
          menuOut.value.dishes.filter((d) => d.is_active).map((d) => ({ id: d.id, name: d.name })),
        );
      }
      if (settingsOut.status === "fulfilled") setDeductMode(settingsOut.value.deduct_mode);
      const fails = [batchOut, menuOut, settingsOut].filter((r) => r.status === "rejected");
      if (fails.length === 3) {
        setError("Could not load bulk prep — check gateway/catalog is up.");
      } else if (fails.length) {
        const reason = fails[0].status === "rejected" ? String(fails[0].reason?.message || fails[0].reason) : "";
        setError(reason && reason !== "Not Found" ? reason : "Some bulk-prep data could not load.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bulk prep");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [kitchen]);

  const toggleDish = (id: string) => {
    setSelectedDishIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!kitchen) return;
    setBusy(true);
    setError("");
    setMsg("");
    try {
      const need = batchType === "combo" ? 2 : 1;
      if (selectedDishIds.length < need) {
        throw new Error(batchType === "combo" ? "Pick at least two dishes for a combo." : "Pick one dish.");
      }
      const dishIds =
        batchType === "single_dish" ? [selectedDishIds[0]] : selectedDishIds.slice(0, 8);
      await createPrepBatch(kitchen.id, {
        name: name.trim() || "Bulk prep",
        batch_type: batchType,
        portions: Number(portions) || 1,
        dishes: dishIds.map((dish_id) => ({ dish_id, quantity_per_portion: 1 })),
      });
      setMsg("Prep batch created — review ingredient totals, then mark prepared.");
      setSelectedDishIds([]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create batch");
    } finally {
      setBusy(false);
    }
  };

  const onSaveLines = async (e: FormEvent) => {
    e.preventDefault();
    if (!kitchen || !editing) return;
    setBusy(true);
    setError("");
    try {
      await updatePrepBatch(kitchen.id, editing.id, {
        ingredient_lines: editLines.map((l, idx) => ({
          ingredient_id: l.ingredient_id,
          quantity: Number(l.quantity),
          unit: l.unit,
          sort_order: idx,
        })),
      });
      setMsg("Ingredient quantities saved.");
      setEditing(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save lines");
    } finally {
      setBusy(false);
    }
  };

  const onMarkPrepared = async (batch: PrepBatch) => {
    if (!kitchen) return;
    if (!window.confirm(`Mark “${batch.name}” prepared and deduct pantry stock?`)) return;
    setBusy(true);
    setError("");
    try {
      await markPrepBatchPrepared(kitchen.id, batch.id);
      setMsg("Batch prepared — inventory updated.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not mark prepared");
    } finally {
      setBusy(false);
    }
  };

  const onModeChange = async (mode: StockDeductMode) => {
    if (!kitchen || mode === deductMode) return;
    setBusy(true);
    setError("");
    try {
      const updated = await updateKitchenStockSettings(kitchen.id, mode);
      setDeductMode(updated.deduct_mode);
      setMsg(
        mode === "prep_batch_only"
          ? "Orders will not deduct stock — only bulk prep marked prepared will."
          : "Orders deduct stock when marked Ready (prepared).",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update stock mode");
    } finally {
      setBusy(false);
    }
  };

  const shownBatches = useMemo(() => {
    let list = [...batches];
    if (batchSearch.trim()) {
      const n = batchSearch.trim().toLowerCase();
      list = list.filter(
        (b) =>
          b.name.toLowerCase().includes(n) ||
          b.dishes.some((d) => (d.dish_name || "").toLowerCase().includes(n)) ||
          b.ingredient_lines.some((l) => (l.ingredient_name || "").toLowerCase().includes(n)),
      );
    }
    if (batchFilter === "draft") list = list.filter((b) => b.status !== "prepared");
    if (batchFilter === "prepared") list = list.filter((b) => b.status === "prepared");
    list.sort((a, b) => {
      if (batchSort === "name_asc") return a.name.localeCompare(b.name);
      if (batchSort === "portions_desc") return b.portions - a.portions;
      return Date.parse(b.created_at || "") - Date.parse(a.created_at || "");
    });
    return list;
  }, [batches, batchSearch, batchSort, batchFilter]);

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Operations"
      title="Bulk prep"
      description="Cook once for many portions — expand recipes, edit totals, deduct inventory when prepared."
    >
      {error ? <p className="form-error">{error}</p> : null}
      {msg ? <div className="auth-card__success">{msg}</div> : null}

      {loading ? (
        <div className="app-loading">Loading bulk prep…</div>
      ) : (
        <>
          <OwnerPanel
            title="When does pantry deduct?"
            description="À la carte kitchens use Order Ready. Thali kitchens use bulk prep only to avoid double-counting."
          >
            <div className="owner-status-actions">
              <button
                type="button"
                className={`btn btn--sm ${deductMode === "order_ready" ? "btn--primary" : "btn--ghost"}`}
                disabled={busy}
                onClick={() => onModeChange("order_ready")}
              >
                Order Ready
              </button>
              <button
                type="button"
                className={`btn btn--sm ${deductMode === "prep_batch_only" ? "btn--primary" : "btn--ghost"}`}
                disabled={busy}
                onClick={() => onModeChange("prep_batch_only")}
              >
                Bulk prep only
              </button>
            </div>
            <p className="muted" style={{ marginTop: "0.85rem" }}>
              Set dish recipes under <Link to="/dashboard/ingredients">Ingredients</Link> first.
            </p>
          </OwnerPanel>

          <OwnerPanel title="New prep batch" description="Pick dishes and portions — recipes expand into editable totals">
            <form className="owner-form owner-form--grid" onSubmit={onCreate}>
              <label>
                Name
                <input value={name} onChange={(e) => setName(e.target.value)} required />
              </label>
              <label>
                Portions
                <input
                  type="number"
                  min={1}
                  value={portions}
                  onChange={(e) => setPortions(e.target.value)}
                  required
                />
              </label>
              <label>
                Type
                <select
                  value={batchType}
                  onChange={(e) => setBatchType(e.target.value as "single_dish" | "combo")}
                >
                  <option value="single_dish">Single dish</option>
                  <option value="combo">Combo / thali</option>
                </select>
              </label>

              <fieldset className="owner-form__fieldset owner-form__wide">
                <legend>Dishes in this cook</legend>
                <div className="owner-prep-dishes">
                  {dishes.length === 0 ? (
                    <p className="muted">No active dishes — add menu items first.</p>
                  ) : (
                    dishes.map((d) => (
                      <label key={d.id}>
                        <input
                          type="checkbox"
                          checked={selectedDishIds.includes(d.id)}
                          onChange={() => toggleDish(d.id)}
                        />
                        <span>{d.name}</span>
                      </label>
                    ))
                  )}
                </div>
              </fieldset>

              <div className="owner-form__actions owner-form__wide">
                <button type="submit" className="btn btn--primary" disabled={busy || dishes.length === 0}>
                  Create batch from recipes
                </button>
              </div>
            </form>
          </OwnerPanel>

          <OwnerPanel title="Batches">
            {batches.length === 0 ? (
              <OwnerEmpty message="No prep batches yet — create a morning cook above." />
            ) : (
              <>
              <ListingToolbar
                search={batchSearch}
                onSearchChange={setBatchSearch}
                searchPlaceholder="Search batches, dishes, ingredients…"
                sort={batchSort}
                onSortChange={(v) => setBatchSort(v as typeof batchSort)}
                sortOptions={[
                  { value: "newest", label: "Newest" },
                  { value: "name_asc", label: "Name A–Z" },
                  { value: "portions_desc", label: "Portions ↓" },
                ]}
                filterChips={[
                  { id: "draft", label: "Open" },
                  { id: "prepared", label: "Prepared" },
                ]}
                activeFilter={batchFilter}
                onFilterChange={setBatchFilter}
                resultCount={shownBatches.length}
              />
              {shownBatches.length === 0 ? (
                <OwnerEmpty message="No batches match this search or filter." />
              ) : (
              <div className="owner-table-wrap">
                <table className="owner-table">
                  <thead>
                    <tr>
                      <th>Batch</th>
                      <th>Dishes</th>
                      <th>Ingredients</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shownBatches.map((b) => (
                      <tr key={b.id}>
                        <td>
                          <strong>{b.name}</strong>
                          <div className="muted">
                            {b.batch_type} · {b.portions} portions
                          </div>
                        </td>
                        <td>{b.dishes.map((d) => d.dish_name || d.dish_id).join(", ")}</td>
                        <td>
                          <ul className="owner-detail-items" style={{ margin: 0 }}>
                            {b.ingredient_lines.slice(0, 4).map((l) => (
                              <li key={l.ingredient_id}>
                                <span className="owner-detail-items__row">
                                  <span>{l.ingredient_name}</span>
                                  <span>
                                    {l.quantity} {l.unit}
                                  </span>
                                </span>
                              </li>
                            ))}
                            {b.ingredient_lines.length > 4 ? (
                              <li className="muted">+{b.ingredient_lines.length - 4} more</li>
                            ) : null}
                          </ul>
                        </td>
                        <td>
                          <span className={`status-badge status-badge--${b.status === "prepared" ? "delivered" : "preparing"}`}>
                            {b.status}
                          </span>
                        </td>
                        <td>
                          {b.status !== "prepared" && b.status !== "cancelled" ? (
                            <div className="owner-status-actions">
                              <button
                                type="button"
                                className="btn btn--ghost btn--sm"
                                disabled={busy}
                                onClick={() => {
                                  setEditing(b);
                                  setEditLines(b.ingredient_lines.map((l) => ({ ...l })));
                                }}
                              >
                                Edit qty
                              </button>
                              <button
                                type="button"
                                className="btn btn--primary btn--sm"
                                disabled={busy}
                                onClick={() => onMarkPrepared(b)}
                              >
                                Mark prepared
                              </button>
                            </div>
                          ) : (
                            <span className="muted">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              )}
              </>
            )}
          </OwnerPanel>

          {editing ? (
            <OwnerPanel title={`Edit quantities — ${editing.name}`} description="Explicit totals for this cook (not per-portion)">
              <form className="owner-form owner-form--grid" onSubmit={onSaveLines}>
                {editLines.map((l, idx) => (
                  <label key={l.ingredient_id}>
                    {l.ingredient_name || l.ingredient_id} ({l.unit})
                    <input
                      type="number"
                      min={0.001}
                      step="any"
                      value={l.quantity}
                      onChange={(e) => {
                        const next = [...editLines];
                        next[idx] = { ...l, quantity: Number(e.target.value) };
                        setEditLines(next);
                      }}
                      required
                    />
                  </label>
                ))}
                <div className="owner-form__actions owner-form__wide">
                  <button type="submit" className="btn btn--primary" disabled={busy}>
                    Save quantities
                  </button>
                  <button type="button" className="btn btn--ghost" onClick={() => setEditing(null)}>
                    Cancel
                  </button>
                </div>
              </form>
            </OwnerPanel>
          ) : null}
        </>
      )}
    </OwnerPageShell>
  );
}
