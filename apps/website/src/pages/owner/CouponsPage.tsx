import { useEffect, useState } from "react";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  createCoupon,
  createPromotion,
  deactivateCoupon,
  fetchCoupons,
  fetchMenu,
  fetchPromotions,
  type Coupon,
  type Dish,
  type Promotion,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const SEGMENTS = [
  { value: "all", label: "Everyone" },
  { value: "top_spenders", label: "Top spenders" },
  { value: "repeat", label: "Repeat customers" },
  { value: "vip", label: "VIP (5+ orders)" },
  { value: "churn_risk", label: "Churn risk" },
] as const;

export function CouponsPage() {
  const { kitchen } = useKitchen();
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [code, setCode] = useState("");
  const [discountType, setDiscountType] = useState<"percent" | "fixed">("percent");
  const [discountValue, setDiscountValue] = useState(10);
  const [minOrder, setMinOrder] = useState("");

  const [promoName, setPromoName] = useState("");
  const [promoDishId, setPromoDishId] = useState("");
  const [promoPrice, setPromoPrice] = useState(149);
  const [promoSegment, setPromoSegment] = useState<(typeof SEGMENTS)[number]["value"]>("all");
  const [promoLimit, setPromoLimit] = useState("20");
  const [promoDays, setPromoDays] = useState(7);

  const load = () => {
    if (!kitchen) return;
    setLoading(true);
    Promise.all([
      fetchCoupons(kitchen.id),
      fetchPromotions(kitchen.id),
      fetchMenu(kitchen.id),
    ])
      .then(([c, p, menu]) => {
        setCoupons(c.coupons);
        setPromotions(p.promotions);
        setDishes(menu.dishes.filter((d) => d.is_active));
        if (menu.dishes[0]) setPromoDishId(menu.dishes[0].id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [kitchen]);

  const addCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kitchen || !code.trim()) return;
    setBusy(true);
    setError("");
    try {
      await createCoupon(kitchen.id, {
        code: code.trim(),
        discount_type: discountType,
        discount_value: discountValue,
        min_order_amount: minOrder ? Number(minOrder) : undefined,
      });
      setCode("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create coupon");
    } finally {
      setBusy(false);
    }
  };

  const addPromotion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!kitchen || !promoDishId) return;
    setBusy(true);
    setError("");
    const now = new Date();
    const ends = new Date(now.getTime() + promoDays * 86400000);
    try {
      await createPromotion(kitchen.id, {
        name: promoName.trim() || "Special offer",
        dish_id: promoDishId,
        special_price: promoPrice,
        segment: promoSegment,
        segment_limit: promoSegment === "top_spenders" ? Number(promoLimit) : undefined,
        starts_at: now.toISOString(),
        ends_at: ends.toISOString(),
      });
      setPromoName("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create promotion");
    } finally {
      setBusy(false);
    }
  };

  const disableCoupon = async (couponId: string) => {
    if (!kitchen) return;
    await deactivateCoupon(kitchen.id, couponId);
    load();
  };

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Marketing"
      title="Coupons & promotions"
      description="Share codes on WhatsApp or run targeted dish pricing"
    >
      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <div className="app-loading">Loading…</div>
      ) : (
        <>
          <OwnerPanel title="New coupon" description="Create a code customers can apply at checkout">
            <form className="owner-form owner-form--inline" onSubmit={addCoupon}>
              <input
                className="owner-input"
                placeholder="Code e.g. SAVE10"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                required
              />
              <select
                className="owner-input"
                value={discountType}
                onChange={(e) => setDiscountType(e.target.value as "percent" | "fixed")}
              >
                <option value="percent">Percent off</option>
                <option value="fixed">Fixed ₹ off</option>
              </select>
              <input
                className="owner-input"
                type="number"
                min={1}
                value={discountValue}
                onChange={(e) => setDiscountValue(Number(e.target.value))}
              />
              <input
                className="owner-input"
                type="number"
                placeholder="Min order ₹"
                value={minOrder}
                onChange={(e) => setMinOrder(e.target.value)}
              />
              <button type="submit" className="btn btn--primary" disabled={busy}>
                Create
              </button>
            </form>
          </OwnerPanel>

          <OwnerPanel title="Active coupons">
            {coupons.length === 0 ? (
              <OwnerEmpty message="No coupons yet — create one above to share on WhatsApp." />
            ) : (
              <ul className="owner-list">
                {coupons.map((c) => (
                  <li key={c.id}>
                    <strong>{c.code}</strong> —{" "}
                    {c.discount_type === "percent"
                      ? `${c.discount_value}% off`
                      : `₹${c.discount_value} off`}
                    {c.min_order_amount != null && ` · min ₹${c.min_order_amount}`}
                    {c.used_count > 0 && ` · used ${c.used_count}`}
                    {!c.is_active && " · inactive"}
                    {c.is_active && (
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => disableCoupon(c.id)}
                      >
                        Deactivate
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </OwnerPanel>

          <OwnerPanel
            title="Targeted promotion"
            description="Special pricing for a customer segment (F38)"
          >
            <form className="owner-form" onSubmit={addPromotion}>
              <input
                className="owner-input"
                placeholder="Campaign name"
                value={promoName}
                onChange={(e) => setPromoName(e.target.value)}
              />
              <select
                className="owner-input"
                value={promoDishId}
                onChange={(e) => setPromoDishId(e.target.value)}
              >
                {dishes.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} (₹{d.price})
                  </option>
                ))}
              </select>
              <input
                className="owner-input"
                type="number"
                min={1}
                placeholder="Special price ₹"
                value={promoPrice}
                onChange={(e) => setPromoPrice(Number(e.target.value))}
              />
              <select
                className="owner-input"
                value={promoSegment}
                onChange={(e) =>
                  setPromoSegment(e.target.value as (typeof SEGMENTS)[number]["value"])
                }
              >
                {SEGMENTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
              {promoSegment === "top_spenders" && (
                <input
                  className="owner-input"
                  type="number"
                  min={1}
                  value={promoLimit}
                  onChange={(e) => setPromoLimit(e.target.value)}
                  placeholder="Top N customers"
                />
              )}
              <input
                className="owner-input"
                type="number"
                min={1}
                max={30}
                value={promoDays}
                onChange={(e) => setPromoDays(Number(e.target.value))}
                placeholder="Days"
              />
              <button
                type="submit"
                className="btn btn--primary"
                disabled={busy || dishes.length === 0}
              >
                Launch promotion
              </button>
            </form>

            {promotions.length > 0 && (
              <ul className="owner-list owner-list--spaced">
                {promotions.map((p) => (
                  <li key={p.id}>
                    <strong>{p.name}</strong> — {p.dish_name} at ₹{p.special_price} for{" "}
                    {p.segment.replace("_", " ")}
                    {!p.is_active && " · inactive"}
                  </li>
                ))}
              </ul>
            )}
          </OwnerPanel>
        </>
      )}
    </OwnerPageShell>
  );
}
