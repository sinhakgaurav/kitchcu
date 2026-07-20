import { FormEvent, useEffect, useRef, useState } from "react";
import { RichHtml, RichTextEditor } from "../../components/RichTextEditor";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  createSubscriptionPlan,
  decideKitchenSubscription,
  fetchKitchenSubscriptions,
  fetchKitchenSubscriptionPlans,
  fetchMenu,
  fetchSubscriptionSummary,
  updateSubscriptionPlan,
  uploadKitchenMedia,
  type CustomerKitchenSubscription,
  type Dish,
  type KitchenMealPlan,
  type SubscriptionSummary,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const PLAN_TYPES = [
  { value: "thali", label: "Thali" },
  { value: "tiffin", label: "Tiffin" },
  { value: "combo", label: "Combo" },
  { value: "single_dish", label: "Single dish pack" },
] as const;

const WEEKDAYS = [
  { value: 0, label: "Mon" },
  { value: 1, label: "Tue" },
  { value: 2, label: "Wed" },
  { value: 3, label: "Thu" },
  { value: 4, label: "Fri" },
  { value: 5, label: "Sat" },
  { value: 6, label: "Sun" },
] as const;

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

export function TiffinSubscriptionsPage() {
  const { kitchen } = useKitchen();
  const [plans, setPlans] = useState<KitchenMealPlan[]>([]);
  const [subs, setSubs] = useState<CustomerKitchenSubscription[]>([]);
  const [summary, setSummary] = useState<SubscriptionSummary | null>(null);
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploadingCover, setUploadingCover] = useState(false);
  const coverInputRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState("");
  const [planType, setPlanType] = useState<(typeof PLAN_TYPES)[number]["value"]>("thali");
  const [price, setPrice] = useState(2499);
  const [description, setDescription] = useState("");
  const [selectedDishIds, setSelectedDishIds] = useState<string[]>([]);
  const [weekdays, setWeekdays] = useState<number[]>([0, 1, 2, 3, 4]);
  const [mealsPerDay, setMealsPerDay] = useState(1);
  const [coverUrl, setCoverUrl] = useState<string | null>(null);
  const [editingPlanId, setEditingPlanId] = useState<string | null>(null);

  const load = () => {
    if (!kitchen) return;
    setLoading(true);
    Promise.all([
      fetchKitchenSubscriptionPlans(kitchen.id),
      fetchKitchenSubscriptions(kitchen.id, filter || undefined),
      fetchSubscriptionSummary(kitchen.id),
      fetchMenu(kitchen.id),
    ])
      .then(([p, s, sum, menu]) => {
        setPlans(p.plans);
        setSubs(s.subscriptions);
        setSummary(sum);
        setDishes(menu.dishes.filter((d) => d.is_active));
        setError("");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [kitchen, filter]);

  const toggleDish = (id: string) => {
    setSelectedDishIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (planType === "single_dish") return [id];
      return [...prev, id].slice(0, 40);
    });
  };

  const toggleWeekday = (day: number) => {
    setWeekdays((prev) => {
      if (prev.includes(day)) {
        const next = prev.filter((d) => d !== day);
        return next.length ? next : prev;
      }
      return [...prev, day].sort((a, b) => a - b);
    });
  };

  const onCoverUpload = async (file: File | null) => {
    if (!kitchen || !file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please choose a JPEG, PNG, or WebP image.");
      return;
    }
    setUploadingCover(true);
    setError("");
    try {
      const res = await uploadKitchenMedia(kitchen.id, file, {
        context: "general",
        filename: file.name,
      });
      setCoverUrl(res.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cover upload failed");
    } finally {
      setUploadingCover(false);
      if (coverInputRef.current) coverInputRef.current.value = "";
    }
  };

  const resetForm = () => {
    setName("");
    setDescription("");
    setSelectedDishIds([]);
    setWeekdays([0, 1, 2, 3, 4]);
    setMealsPerDay(1);
    setCoverUrl(null);
    setPlanType("thali");
    setPrice(2499);
    setEditingPlanId(null);
  };

  const startEditPlan = (plan: KitchenMealPlan) => {
    setEditingPlanId(plan.id);
    setName(plan.name);
    setDescription(plan.description ?? "");
    setPlanType((plan.plan_type as typeof planType) || "thali");
    setPrice(plan.price_monthly);
    setSelectedDishIds(plan.dishes_config?.dish_ids ?? []);
    setWeekdays(plan.dishes_config?.weekdays?.length ? plan.dishes_config.weekdays : [0, 1, 2, 3, 4]);
    setMealsPerDay(plan.dishes_config?.meals_per_day ?? 1);
    setCoverUrl(plan.dishes_config?.image_url ?? null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const onCreatePlan = async (e: FormEvent) => {
    e.preventDefault();
    if (!kitchen || !name.trim()) return;
    if (selectedDishIds.length === 0) {
      setError("Link at least one dish from your menu to this plan.");
      return;
    }
    if (planType === "single_dish" && selectedDishIds.length !== 1) {
      setError("Single dish pack needs exactly one linked dish.");
      return;
    }
    setBusy(true);
    setError("");
    const dishes_config = {
      dish_ids: selectedDishIds,
      weekdays,
      meals_per_day: mealsPerDay,
      image_url: coverUrl || undefined,
    };
    try {
      if (editingPlanId) {
        await updateSubscriptionPlan(kitchen.id, editingPlanId, {
          name: name.trim(),
          description: description.trim() || null,
          plan_type: planType,
          price_monthly: price,
          dishes_config,
        });
      } else {
        await createSubscriptionPlan(kitchen.id, {
          name: name.trim(),
          description: description.trim() || undefined,
          plan_type: planType,
          price_monthly: price,
          dishes_config,
        });
      }
      resetForm();
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save plan");
    } finally {
      setBusy(false);
    }
  };

  const onDecide = async (
    subId: string,
    action: "accept" | "deny" | "activate" | "deactivate",
  ) => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      await decideKitchenSubscription(kitchen.id, subId, action);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const togglePlan = async (plan: KitchenMealPlan) => {
    if (!kitchen) return;
    setBusy(true);
    try {
      await updateSubscriptionPlan(kitchen.id, plan.id, { is_active: !plan.is_active });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update plan");
    } finally {
      setBusy(false);
    }
  };

  const dishName = (id: string) => dishes.find((d) => d.id === id)?.name ?? "Dish";

  return (
    <OwnerPageShell
      eyebrow="Growth"
      title="Tiffin & monthly plans"
      description="Thali/tiffin subscriptions — customers request, you accept or deny. No food commission."
    >
      {error && <div className="auth-card__error">{error}</div>}

      {summary && (
        <div className="od-board__kpi-grid">
          <div className="owner-stat glass">
            <strong>{summary.pending}</strong>
            <span>Pending requests</span>
          </div>
          <div className="owner-stat glass">
            <strong>{summary.active}</strong>
            <span>Active subscribers</span>
          </div>
          <div className="owner-stat glass">
            <strong>{summary.paused}</strong>
            <span>Paused</span>
          </div>
          <div className="owner-stat glass">
            <strong>{inr(summary.mrr_estimate)}</strong>
            <span>MRR estimate</span>
          </div>
        </div>
      )}

      <OwnerPanel
        title={editingPlanId ? "Edit plan" : "Create plan"}
        description="Link menu dishes, add a cover photo, and describe the plan for customers."
      >
        <form className="owner-form owner-form--wide" onSubmit={onCreatePlan}>
          <div className="form-row">
            <label>
              Plan name
              <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Veg thali monthly" />
            </label>
            <label>
              Type
              <select
                value={planType}
                onChange={(e) => {
                  const next = e.target.value as typeof planType;
                  setPlanType(next);
                  if (next === "single_dish" && selectedDishIds.length > 1) {
                    setSelectedDishIds(selectedDishIds.slice(0, 1));
                  }
                }}
              >
                {PLAN_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </label>
            <label>
              Monthly price (₹)
              <input type="number" min={1} value={price} onChange={(e) => setPrice(Number(e.target.value))} required />
            </label>
            <label>
              Meals / day
              <select value={mealsPerDay} onChange={(e) => setMealsPerDay(Number(e.target.value))}>
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
              </select>
            </label>
          </div>

          <fieldset className="owner-form__fieldset">
            <legend>Delivery days</legend>
            <div className="owner-chip-row">
              {WEEKDAYS.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  className={`btn btn--sm ${weekdays.includes(d.value) ? "btn--primary" : "btn--ghost"}`}
                  onClick={() => toggleWeekday(d.value)}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </fieldset>

          <fieldset className="owner-form__fieldset">
            <legend>
              Linked dishes
              {selectedDishIds.length > 0 ? ` (${selectedDishIds.length})` : ""}
            </legend>
            <p className="owner-muted" style={{ marginTop: 0 }}>
              {planType === "single_dish"
                ? "Pick exactly one dish for this pack."
                : "Select the dishes included in this monthly plan."}
            </p>
            {dishes.length === 0 ? (
              <p className="owner-muted">No available dishes — add dishes in Menu first.</p>
            ) : (
              <div className="owner-chip-row">
                {dishes.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    className={`btn btn--sm ${selectedDishIds.includes(d.id) ? "btn--primary" : "btn--ghost"}`}
                    onClick={() => toggleDish(d.id)}
                  >
                    {d.name}
                  </button>
                ))}
              </div>
            )}
          </fieldset>

          <fieldset className="owner-form__fieldset">
            <legend>Cover image</legend>
            <input
              ref={coverInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              hidden
              onChange={(e) => onCoverUpload(e.target.files?.[0] ?? null)}
            />
            {coverUrl ? (
              <div className="plan-cover-preview">
                <img src={coverUrl} alt="Plan cover" />
                <div className="owner-actions">
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    disabled={uploadingCover || busy}
                    onClick={() => coverInputRef.current?.click()}
                  >
                    {uploadingCover ? "Uploading…" : "Replace"}
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    disabled={uploadingCover || busy}
                    onClick={() => setCoverUrl(null)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                className="btn btn--ghost"
                disabled={uploadingCover || busy || !kitchen}
                onClick={() => coverInputRef.current?.click()}
              >
                {uploadingCover ? "Uploading…" : "Upload cover photo"}
              </button>
            )}
          </fieldset>

          <label>
            Description
            {kitchen ? (
              <RichTextEditor
                value={description}
                onChange={setDescription}
                placeholder="What’s included, spice level, delivery window…"
                minHeight={140}
                kitchenId={kitchen.id}
                uploadContext="general"
                disabled={busy}
              />
            ) : (
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
            )}
          </label>

          <div className="owner-actions">
            <button type="submit" className="btn btn--primary" disabled={busy || uploadingCover}>
              {busy ? "Saving…" : editingPlanId ? "Save plan" : "Create plan"}
            </button>
            {editingPlanId && (
              <button type="button" className="btn btn--ghost" disabled={busy} onClick={resetForm}>
                Cancel edit
              </button>
            )}
          </div>
        </form>
      </OwnerPanel>

      <OwnerPanel title="Plans">
        {loading ? (
          <p className="owner-muted">Loading…</p>
        ) : plans.length === 0 ? (
          <OwnerEmpty message="No plans yet — create a thali or tiffin plan above." />
        ) : (
          <ul className="owner-detail-items plan-list">
            {plans.map((p) => {
              const linked = p.dishes_config?.dish_ids ?? [];
              const img = p.dishes_config?.image_url;
              const plain = p.description ? stripHtml(p.description) : "";
              return (
                <li key={p.id} className="plan-list__item">
                  {img ? (
                    <img className="plan-list__thumb" src={img} alt="" />
                  ) : (
                    <span className="plan-list__thumb plan-list__thumb--empty" aria-hidden />
                  )}
                  <span className="plan-list__body">
                    <strong>{p.name}</strong> · {p.plan_type} · {inr(p.price_monthly)}/mo
                    {" · "}
                    {p.active_subscriber_count} active · {p.pending_count} pending
                    {!p.is_active && " · inactive"}
                    {linked.length > 0 && (
                      <span className="owner-muted">
                        {" "}
                        · {linked.length} dish{linked.length === 1 ? "" : "es"}
                        {linked.slice(0, 3).map((id) => ` · ${dishName(id)}`).join("")}
                        {linked.length > 3 ? "…" : ""}
                      </span>
                    )}
                    {plain ? (
                      <RichHtml html={p.description || ""} className="plan-list__desc" />
                    ) : null}
                  </span>
                  <span className="owner-actions">
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      disabled={busy}
                      onClick={() => startEditPlan(p)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      disabled={busy}
                      onClick={() => togglePlan(p)}
                    >
                      {p.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </OwnerPanel>

      <OwnerPanel title="Subscription requests">
        <div className="form-row" style={{ marginBottom: "0.75rem" }}>
          <label>
            Filter
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="denied">Denied</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </label>
        </div>
        {subs.length === 0 ? (
          <OwnerEmpty message="No subscriptions in this filter." />
        ) : (
          <ul className="owner-detail-items">
            {subs.map((s) => (
              <li key={s.id}>
                <span>
                  <strong>{s.customer_name || s.customer_phone}</strong>
                  {" · "}
                  {s.plan_name || "Plan"} · {s.status}
                  {s.price_monthly != null && <> · {inr(s.price_monthly)}/mo</>}
                </span>
                <span className="owner-actions">
                  {s.status === "pending" && (
                    <>
                      <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => onDecide(s.id, "accept")}>
                        Accept
                      </button>
                      <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={() => onDecide(s.id, "deny")}>
                        Deny
                      </button>
                    </>
                  )}
                  {s.status === "active" && (
                    <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={() => onDecide(s.id, "deactivate")}>
                      Deactivate
                    </button>
                  )}
                  {s.status === "paused" && (
                    <button type="button" className="btn btn--primary btn--sm" disabled={busy} onClick={() => onDecide(s.id, "activate")}>
                      Activate
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </OwnerPanel>
    </OwnerPageShell>
  );
}
