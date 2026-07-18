import { Link, Navigate, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useBrandedStorefront } from "../../customer/BrandedStorefront";
import { useGeolocation } from "../../hooks/useGeolocation";
import { getCustomerToken } from "../../shared/customerApi";
import { useCustomerAuth } from "../../shared/customerAuth";
import {
  captureCustomerPayment,
  createCustomerOrder,
  createCustomerPayment,
  createCustomerUpiIntent,
  captureMasterPayment,
  createMasterOrder,
  createMasterPayment,
} from "../../shared/customerCheckoutApi";
import {
  cartSubtotal,
  clearCart,
  getCart,
  kitchenCartSubtotal,
  projectKitchenReadyMin,
  updateLineQuantity,
  type CustomerCart,
  type KitchenCartGroup,
} from "../../shared/customerCart";
import { APP_STORAGE_PREFIX } from "../../shared/brand";
import { denyDeliveryFee, fetchDeliveryQuote, type DeliveryQuote } from "../../shared/api";

type DeliveryType = "pickup" | "delivery";
type PaymentMethod = "cod" | "online" | "upi";

const PUNE_FALLBACK = { latitude: 18.5362, longitude: 73.8958 };

function checkoutKey(cart: CustomerCart): string {
  const storageKey = `${APP_STORAGE_PREFIX}_checkout_key:${cart.updatedAt}`;
  const existing = sessionStorage.getItem(storageKey);
  if (existing) return existing;
  const value = crypto.randomUUID();
  sessionStorage.setItem(storageKey, value);
  return value;
}

function selectedModeFee(quote: DeliveryQuote | undefined, mode: string): number {
  const opt = quote?.modes?.find((m) => m.mode === mode);
  if (opt) return opt.customer_fee;
  return quote?.fee ?? 0;
}

function buildGroupPayload(
  kitchen: KitchenCartGroup,
  deliveryType: DeliveryType,
  quote: DeliveryQuote | undefined,
  feeAccepted: boolean,
  coords: { latitude: number; longitude: number },
  deliveryMode: string,
) {
  const isDelivery = deliveryType === "delivery";
  const fee = isDelivery ? selectedModeFee(quote, deliveryMode) : 0;
  return {
    kitchen_id: kitchen.kitchenId,
    items: kitchen.lines.map((line) => ({
      dish_id: line.dishId,
      quantity: line.quantity,
    })),
    delivery_type: deliveryType,
    delivery_mode: isDelivery ? deliveryMode : undefined,
    delivery_fee: fee,
    distance_km: isDelivery ? quote?.distance_km : undefined,
    delivery_fee_accepted: isDelivery && fee > 0 ? feeAccepted : isDelivery ? true : undefined,
    customer_latitude: isDelivery ? coords.latitude : undefined,
    customer_longitude: isDelivery ? coords.longitude : undefined,
  };
}

export function CheckoutPage() {
  const { loading } = useCustomerAuth();
  const navigate = useNavigate();
  const token = getCustomerToken();
  const { coords, status: geoStatus, error: geoError, refresh: refreshGeo } = useGeolocation(PUNE_FALLBACK);
  const [cart, setCart] = useState<CustomerCart | null>(null);
  const [deliveryByKitchen, setDeliveryByKitchen] = useState<Record<string, DeliveryType>>({});
  const [quotes, setQuotes] = useState<Record<string, DeliveryQuote>>({});
  const [feeAccepted, setFeeAccepted] = useState<Record<string, boolean>>({});
  const [modeByKitchen, setModeByKitchen] = useState<Record<string, string>>({});
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("cod");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [deniedFeeKitchens, setDeniedFeeKitchens] = useState<Record<string, boolean>>({});

  const denyFee = async (kitchenId: string) => {
    const quote = quotes[kitchenId];
    if (!quote?.quote_id) return;
    try {
      await denyDeliveryFee(quote.quote_id, {
        subtotal: kitchenCartSubtotal(cart!.kitchens.find((k) => k.kitchenId === kitchenId)!),
      });
      setDeniedFeeKitchens((current) => ({ ...current, [kitchenId]: true }));
    } catch {
      // Fire-and-forget UX — even if the alert fails to send, don't block checkout flow.
      setDeniedFeeKitchens((current) => ({ ...current, [kitchenId]: true }));
    }
  };

  useEffect(() => {
    setCart(getCart());
  }, []);

  useEffect(() => {
    if (!cart) return;
    let cancelled = false;
    const loadQuotes = async () => {
      setQuoteLoading(true);
      const next: Record<string, DeliveryQuote> = {};
      try {
        for (const kitchen of cart.kitchens) {
          if ((deliveryByKitchen[kitchen.kitchenId] ?? "pickup") !== "delivery") continue;
          const quote = await fetchDeliveryQuote({
            kitchen_id: kitchen.kitchenId,
            latitude: coords.latitude,
            longitude: coords.longitude,
            subtotal: kitchenCartSubtotal(kitchen),
          });
          if (quote.status === "out_of_range") {
            throw new Error(`${kitchen.kitchenName} does not deliver to your location`);
          }
          // status "ok" (in range) or "extended" (beyond max — customer pays) are allowed
          next[kitchen.kitchenId] = quote;
        }
        if (!cancelled) {
          setQuotes(next);
          setModeByKitchen((prev) => {
            const merged = { ...prev };
            for (const [kid, q] of Object.entries(next)) {
              if (!merged[kid]) merged[kid] = q.modes?.[0]?.mode || "self";
            }
            return merged;
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not quote delivery fee");
        }
      } finally {
        if (!cancelled) setQuoteLoading(false);
      }
    };
    loadQuotes();
    return () => {
      cancelled = true;
    };
  }, [cart, deliveryByKitchen, coords.latitude, coords.longitude]);

  const isMultiKitchen = (cart?.kitchens.length ?? 0) > 1;

  const deliveryFee = useMemo(
    () => cart?.kitchens.reduce((sum, kitchen) => {
      if ((deliveryByKitchen[kitchen.kitchenId] ?? "pickup") !== "delivery") return sum;
      const mode = modeByKitchen[kitchen.kitchenId] || "self";
      return sum + selectedModeFee(quotes[kitchen.kitchenId], mode);
    }, 0) ?? 0,
    [cart, deliveryByKitchen, quotes, modeByKitchen],
  );

  const branded = useBrandedStorefront();
  const loginNext = branded ? `${branded.basePath}/checkout` : "/checkout";
  const menuBack = branded ? `${branded.basePath}/menu` : "/#nearby";

  if (!loading && !token) {
    return <Navigate to={`/login?next=${encodeURIComponent(loginNext)}`} replace />;
  }

  if (!cart) {
    return (
      <div className="container customer-checkout">
        <p className="owner-empty">Your cart is empty.</p>
        <Link to={menuBack} className="btn btn--primary">
          {branded ? "Back to menu" : "Discover kitchens"}
        </Link>
      </div>
    );
  }

  const subtotal = cartSubtotal(cart);
  const total = subtotal + deliveryFee;

  const placeOrder = async () => {
    setError("");
    for (const kitchen of cart.kitchens) {
      const dtype = deliveryByKitchen[kitchen.kitchenId] ?? "pickup";
      const quote = quotes[kitchen.kitchenId];
      if (dtype === "delivery" && !quote) {
        setError("Waiting for delivery fee quote — try again in a moment");
        return;
      }
      const mode = modeByKitchen[kitchen.kitchenId] || "self";
      const fee = selectedModeFee(quote, mode);
      if (dtype === "delivery" && fee > 0 && !feeAccepted[kitchen.kitchenId]) {
        setError(`Accept the delivery fee for ${kitchen.kitchenName} to continue`);
        return;
      }
    }

    setBusy(true);
    try {
      if (cart.kitchens.length > 1) {
        const master = await createMasterOrder(
          {
            payment_method: paymentMethod,
            groups: cart.kitchens.map((kitchen) => buildGroupPayload(
              kitchen,
              deliveryByKitchen[kitchen.kitchenId] ?? "pickup",
              quotes[kitchen.kitchenId],
              feeAccepted[kitchen.kitchenId] ?? false,
              coords,
              modeByKitchen[kitchen.kitchenId] || "self",
            )),
          },
          checkoutKey(cart),
        );

        let settlements;
        if (paymentMethod === "online" || paymentMethod === "upi") {
          const payment = await createMasterPayment(master.id, paymentMethod);
          const captured = await captureMasterPayment(payment.id);
          settlements = captured.settlements;
        }

        clearCart();
        navigate(
          branded
            ? `${branded.basePath}/master-orders/${master.id}/confirm`
            : `/master-orders/${master.id}/confirm`,
          { state: { master, paymentMethod, settlements } },
        );
        return;
      }

      const kitchen = cart.kitchens[0];
      const order = await createCustomerOrder(
        kitchen.kitchenId,
        {
          ...buildGroupPayload(
            kitchen,
            deliveryByKitchen[kitchen.kitchenId] ?? "pickup",
            quotes[kitchen.kitchenId],
            feeAccepted[kitchen.kitchenId] ?? false,
            coords,
            modeByKitchen[kitchen.kitchenId] || "self",
          ),
          payment_method: paymentMethod,
        },
        checkoutKey(cart),
      );

      if (paymentMethod === "online") {
        const payment = await createCustomerPayment(order.id, "online");
        await captureCustomerPayment(payment.id);
      } else if (paymentMethod === "upi") {
        await createCustomerUpiIntent(order.id);
      }

      clearCart();
      navigate(
        branded
          ? `${branded.basePath}/orders/${order.id}/confirm`
          : `/orders/${order.id}/confirm`,
        { state: { order, paymentMethod } },
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container customer-checkout">
      <Link to={menuBack} className="owner-back">
        {branded ? "← Back to menu" : "← Add from another kitchen"}
      </Link>
      <header className="owner-page__head">
        <div>
          <h1>{isMultiKitchen ? "Multi-kitchen checkout" : "Checkout"}</h1>
          <p>
            {cart.kitchens.length} kitchen{cart.kitchens.length === 1 ? "" : "s"} ·{" "}
            {isMultiKitchen ? "separate tracking for every kitchen" : cart.kitchens[0].kitchenCode}
          </p>
        </div>
      </header>

      {geoError && (
        <p className="nearby-kitchens__geo-hint">
          {geoError}{" "}
          <button type="button" className="btn btn--ghost" onClick={refreshGeo}>Retry GPS</button>
        </p>
      )}
      {geoStatus === "granted" && (
        <p className="nearby-kitchens__geo-hint">Using your location for distance-based delivery fees.</p>
      )}

      {error && <div className="auth-card__error">{error}</div>}

      {cart.kitchens.map((kitchen) => {
        const dtype = deliveryByKitchen[kitchen.kitchenId] ?? "pickup";
        const quote = quotes[kitchen.kitchenId];
        return (
          <section key={kitchen.kitchenId} className="glass customer-checkout__cart">
            <h2>{kitchen.kitchenName} · {kitchen.kitchenCode}</h2>
            <p className="customer-checkout__eta">
              Projected ready within ~{projectKitchenReadyMin(kitchen, dtype === "delivery")} min
              {" "}(longest dish max time — quality-first, not a speed race)
            </p>
            <ul className="owner-detail-items">
              {kitchen.lines.map((line) => (
                <li key={line.dishId}>
                  <span>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={line.quantity}
                      className="customer-qty-input"
                      onChange={(event) => {
                        const next = updateLineQuantity(line.dishId, Number(event.target.value));
                        setCart(next);
                      }}
                    />
                    {" "}× {line.dishName}
                    <em className="customer-line-eta">
                      {" "}· ready ≤{line.maxTimeMin || line.prepTimeMin}m
                    </em>
                  </span>
                  <span>₹{(line.unitPrice * line.quantity).toFixed(0)}</span>
                </li>
              ))}
            </ul>
            <label>
              Fulfillment
              <select
                value={dtype}
                onChange={(event) => {
                  const nextType = event.target.value as DeliveryType;
                  setDeliveryByKitchen((current) => ({
                    ...current,
                    [kitchen.kitchenId]: nextType,
                  }));
                  if (nextType === "pickup") {
                    setFeeAccepted((current) => ({ ...current, [kitchen.kitchenId]: false }));
                  }
                }}
              >
                <option value="pickup">Pickup (free)</option>
                <option value="delivery">Delivery</option>
              </select>
            </label>
            {dtype === "delivery" && (
              <div className="report-hint">
                {quoteLoading && !quote && <span>Calculating distance & fee…</span>}
                {quote && (
                  <>
                    <span>
                      {quote.distance_km.toFixed(1)} km ·{" "}
                      {quote.in_range !== false && quote.status !== "extended"
                        ? "In kitchen range — kitchen covers full delivery cost (₹0 to you)"
                        : "Beyond kitchen range — choose how delivery is fulfilled below"}
                    </span>
                    {quote.modes && quote.modes.length > 0 && (
                      <label style={{ display: "block", marginTop: "0.65rem" }}>
                        Delivery option
                        <select
                          value={modeByKitchen[kitchen.kitchenId] || quote.modes[0].mode}
                          onChange={(e) => {
                            setModeByKitchen((c) => ({ ...c, [kitchen.kitchenId]: e.target.value }));
                            setFeeAccepted((c) => ({ ...c, [kitchen.kitchenId]: false }));
                          }}
                        >
                          {quote.modes.map((m) => (
                            <option key={m.mode} value={m.mode}>
                              {m.label} — you pay ₹{Math.round(m.customer_fee)}
                              {m.owner_fee > 0 ? ` (kitchen ₹${Math.round(m.owner_fee)})` : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    {(() => {
                      const mode = modeByKitchen[kitchen.kitchenId] || quote.modes?.[0]?.mode || "self";
                      const opt = quote.modes?.find((m) => m.mode === mode);
                      const fee = opt?.customer_fee ?? quote.fee;
                      return (
                        <>
                          {opt && <p style={{ marginTop: "0.35rem" }}>{opt.description}</p>}
                          {fee > 0 && (
                      <>
                        <label style={{ display: "block", marginTop: "0.5rem" }}>
                          <input
                            type="checkbox"
                            checked={feeAccepted[kitchen.kitchenId] ?? false}
                            onChange={(event) => setFeeAccepted((current) => ({
                              ...current,
                              [kitchen.kitchenId]: event.target.checked,
                            }))}
                          />
                          {" "}I accept the ₹{Math.round(fee)} delivery fee
                        </label>
                        {!feeAccepted[kitchen.kitchenId] && (
                          deniedFeeKitchens[kitchen.kitchenId] ? (
                            <p style={{ marginTop: "0.35rem", color: "var(--teal-dark, #0f766e)" }}>
                              Kitchen notified — they may call you to offer free delivery or pickup.
                            </p>
                          ) : (
                            <button
                              type="button"
                              onClick={() => denyFee(kitchen.kitchenId)}
                              style={{
                                marginTop: "0.35rem",
                                background: "none",
                                border: "none",
                                padding: 0,
                                color: "var(--orange, #d9622b)",
                                textDecoration: "underline",
                                cursor: "pointer",
                                font: "inherit",
                              }}
                            >
                              Can&apos;t pay this fee? Notify the kitchen instead
                            </button>
                          )
                        )}
                      </>
                          )}
                        </>
                      );
                    })()}
                  </>
                )}
              </div>
            )}
            <div className="owner-detail-total">
              <span>Kitchen subtotal</span>
              <strong>₹{kitchenCartSubtotal(kitchen).toFixed(0)}</strong>
            </div>
          </section>
        );
      })}

      <section className="glass owner-form customer-checkout__form">
        <label>
          Payment
          <select
            value={paymentMethod}
            onChange={(event) => setPaymentMethod(event.target.value as PaymentMethod)}
          >
            <option value="cod">Cash on delivery / pickup</option>
            <option value="upi">UPI{isMultiKitchen ? " (split to kitchens)" : ""}</option>
            <option value="online">Card / wallet{isMultiKitchen ? " (split to kitchens)" : ""}</option>
          </select>
        </label>
        {isMultiKitchen && paymentMethod !== "cod" && (
          <p className="nearby-kitchens__geo-hint">
            One payment is captured at checkout and split to each kitchen via Razorpay Route.
          </p>
        )}
        <div className="owner-detail-total">
          <span>Delivery fees</span>
          <strong>₹{deliveryFee.toFixed(0)}</strong>
        </div>
        <div className="owner-detail-total">
          <span>Total</span>
          <strong>₹{total.toFixed(0)}</strong>
        </div>
        <button type="button" className="btn btn--primary" disabled={busy || quoteLoading} onClick={placeOrder}>
          {busy ? "Placing order…" : `Place ${cart.kitchens.length} order${cart.kitchens.length === 1 ? "" : "s"} · ₹${total.toFixed(0)}`}
        </button>
      </section>
    </div>
  );
}
