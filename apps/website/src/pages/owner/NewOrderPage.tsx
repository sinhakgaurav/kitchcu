import { Link, useNavigate } from "react-router-dom";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ListingToolbar } from "../../components/ListingToolbar";
import { PhoneField } from "../../components/PhoneField";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import { createManualOrder, fetchMenu, type Dish } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";
import {
  filterAndSortDishes,
  type DishHighlight,
  type DishSort,
} from "../../shared/listingControls";
import {
  firstError,
  toE164,
  validateNationalPhone,
  validatePersonName,
} from "../../shared/validation";

type Line = { dish_id: string; quantity: number };

export function NewOrderPage() {
  const { kitchen } = useKitchen();
  const navigate = useNavigate();
  const [dishes, setDishes] = useState<Dish[]>([]);
  const [lines, setLines] = useState<Line[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<DishSort>("name_asc");
  const [highlights, setHighlights] = useState<DishHighlight[]>([]);
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{ name?: string; phone?: string }>({});

  useEffect(() => {
    if (!kitchen) return;
    fetchMenu(kitchen.id).then((m) => setDishes(m.dishes)).catch(() => {});
  }, [kitchen]);

  const visibleDishes = useMemo(
    () => filterAndSortDishes(dishes, { q: search, sort, highlights }),
    [dishes, search, sort, highlights],
  );

  if (!kitchen) return null;

  const addLine = (dishId: string) => {
    setLines((prev) => {
      const existing = prev.find((l) => l.dish_id === dishId);
      if (existing) {
        return prev.map((l) => l.dish_id === dishId ? { ...l, quantity: l.quantity + 1 } : l);
      }
      return [...prev, { dish_id: dishId, quantity: 1 }];
    });
  };

  const total = lines.reduce((sum, l) => {
    const d = dishes.find((x) => x.id === l.dish_id);
    return sum + (d ? d.price * l.quantity : 0);
  }, 0);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (lines.length === 0) {
      setError("Add at least one dish");
      return;
    }
    const fd = new FormData(e.currentTarget);
    const nextErrors = {
      name: validatePersonName(customerName, { required: false }) ?? undefined,
      phone: validateNationalPhone(customerPhone, undefined, { required: false }) ?? undefined,
    };
    setFieldErrors(nextErrors);
    const firstMessage = firstError(nextErrors);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
    setError("");
    setBusy(true);
    try {
      const order = await createManualOrder(kitchen.id, {
        items: lines,
        delivery_type: fd.get("delivery_type") as "pickup" | "delivery",
        payment_method: fd.get("payment_method") as "cod" | "online" | "upi",
        customer_name: customerName.trim() || undefined,
        customer_phone: customerPhone ? toE164(customerPhone) : undefined,
        delivery_fee: Number(fd.get("delivery_fee") || 0),
      });
      navigate(`/dashboard/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create order");
    } finally {
      setBusy(false);
    }
  };

  return (
    <OwnerPageShell
      eyebrow="Order operations"
      title="New manual order"
      description="Walk-in, phone, or counter orders — add dishes and place instantly"
      backTo="/dashboard/orders"
      backLabel="← Back to orders"
    >
      <div className="owner-new-order">
        <OwnerPanel title="Menu" description="Tap dishes to add to the order">
          {dishes.length === 0 ? (
            <p className="owner-muted">No dishes yet. <Link to="/dashboard/menu/new">Add dishes</Link> first.</p>
          ) : (
            <>
              <ListingToolbar
                search={search}
                onSearchChange={setSearch}
                searchPlaceholder="Search dishes…"
                sort={sort}
                onSortChange={(v) => setSort(v as DishSort)}
                highlights={highlights}
                onHighlightsChange={setHighlights}
                resultCount={visibleDishes.length}
              />
              <div className="owner-dish-pick">
                {visibleDishes.map((d) => (
                  <button key={d.id} type="button" onClick={() => addLine(d.id)}>
                    <span>{d.name}</span>
                    <span>₹{d.price}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </OwnerPanel>

        <form className="dash-card owner-form" onSubmit={handleSubmit}>
          <h2>Order details</h2>
          {lines.length > 0 && (
            <ul className="owner-cart">
              {lines.map((l) => {
                const d = dishes.find((x) => x.id === l.dish_id);
                return (
                  <li key={l.dish_id}>
                    {l.quantity}× {d?.name} — ₹{((d?.price ?? 0) * l.quantity).toFixed(0)}
                    <button type="button" onClick={() => setLines((p) => p.filter((x) => x.dish_id !== l.dish_id))}>×</button>
                  </li>
                );
              })}
              <li className="owner-cart__total"><strong>Subtotal ₹{total.toFixed(0)}</strong></li>
            </ul>
          )}
          {error && <div className="auth-card__error">{error}</div>}
          <label>
            Customer name
            <input
              value={customerName}
              onChange={(e) => {
                setCustomerName(e.target.value);
                setFieldErrors((f) => ({ ...f, name: undefined }));
              }}
              placeholder="Optional"
              className={fieldErrors.name ? "input-invalid" : undefined}
              aria-invalid={Boolean(fieldErrors.name)}
            />
            {fieldErrors.name ? <span className="field-error">{fieldErrors.name}</span> : null}
          </label>
          <PhoneField
            label="Customer phone"
            value={customerPhone}
            onChange={(national) => {
              setCustomerPhone(national);
              setFieldErrors((f) => ({ ...f, phone: undefined }));
            }}
            error={fieldErrors.phone}
            hint="Optional — used for order updates"
          />
          <div className="form-row">
            <label>Delivery
              <select name="delivery_type" defaultValue="pickup">
                <option value="pickup">Pickup</option>
                <option value="delivery">Delivery</option>
              </select>
            </label>
            <label>Payment
              <select name="payment_method" defaultValue="cod">
                <option value="cod">COD</option>
                <option value="upi">UPI</option>
                <option value="online">Online</option>
              </select>
            </label>
          </div>
          <label>Delivery fee<input name="delivery_fee" type="number" min="0" step="1" defaultValue="0" /></label>
          <button type="submit" className="btn btn--primary btn--lg" disabled={busy || lines.length === 0}>
            {busy ? "Placing..." : "Place order"}
          </button>
        </form>
      </div>
    </OwnerPageShell>
  );
}
