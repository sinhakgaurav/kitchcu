import { Link, Navigate, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
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
  updateLineQuantity,
  type CustomerCart,
  type KitchenCartGroup,
} from "../../shared/customerCart";
import { APP_STORAGE_PREFIX } from "../../shared/brand";
import { fetchDeliveryQuote, type DeliveryQuote } from "../../shared/api";

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

function buildGroupPayload(
  kitchen: KitchenCartGroup,
  deliveryType: DeliveryType,
  quote: DeliveryQuote | undefined,
  feeAccepted: boolean,
  coords: { latitude: number; longitude: number },
) {
  const isDelivery = deliveryType === "delivery";
  return {
    kitchen_id: kitchen.kitchenId,
    items: kitchen.lines.map((line) => ({
      dish_id: line.dishId,
      quantity: line.quantity,
    })),
    delivery_type: deliveryType,
    delivery_fee: isDelivery ? (quote?.fee ?? 0) : 0,
    distance_km: isDelivery ? quote?.distance_km : undefined,
    delivery_fee_accepted: isDelivery && (quote?.fee ?? 0) > 0 ? feeAccepted : isDelivery ? true : undefined,
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
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("cod");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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
          next[kitchen.kitchenId] = quote;
        }
        if (!cancelled) setQuotes(next);
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
      return sum + (quotes[kitchen.kitchenId]?.fee ?? 0);
    }, 0) ?? 0,
    [cart, deliveryByKitchen, quotes],
  );

  if (!loading && !token) {
    return <Navigate to="/login?next=/checkout" replace />;
  }

  if (!cart) {
    return (
      <div className="container customer-checkout">
        <p className="owner-empty">Your cart is empty.</p>
        <Link to="/#nearby" className="btn btn--primary">Discover kitchens</Link>
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
      if (dtype === "delivery" && quote && quote.fee > 0 && !feeAccepted[kitchen.kitchenId]) {
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
        navigate(`/master-orders/${master.id}/confirm`, {
          state: { master, paymentMethod, settlements },
        });
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
          ),
          payment_method: paymentMethod,
        },
      );

      if (paymentMethod === "online") {
        const payment = await createCustomerPayment(order.id, "online");
        await captureCustomerPayment(payment.id);
      } else if (paymentMethod === "upi") {
        await createCustomerUpiIntent(order.id);
      }

      clearCart();
      navigate(`/orders/${order.id}/confirm`, { state: { order, paymentMethod } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container customer-checkout">
      <Link to="/#nearby" className="owner-back">← Add from another kitchen</Link>
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
                      {quote.distance_km.toFixed(1)} km away · delivery fee ₹{Math.round(quote.fee)}
                      {quote.within_free_radius ? " (within free radius)" : ""}
                    </span>
                    {quote.fee > 0 && (
                      <label style={{ display: "block", marginTop: "0.5rem" }}>
                        <input
                          type="checkbox"
                          checked={feeAccepted[kitchen.kitchenId] ?? false}
                          onChange={(event) => setFeeAccepted((current) => ({
                            ...current,
                            [kitchen.kitchenId]: event.target.checked,
                          }))}
                        />
                        {" "}I accept the ₹{Math.round(quote.fee)} delivery fee
                      </label>
                    )}
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
