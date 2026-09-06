import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  CART_CHANGED_EVENT,
  cartItemCount,
  cartSubtotal,
  getCart,
  kitchenCartSubtotal,
  updateLineQuantity,
  type CustomerCart,
} from "../shared/customerCart";
export function CustomerCartDrawer() {
  const location = useLocation();
  const [cart, setCart] = useState<CustomerCart | null>(null);
  const [open, setOpen] = useState(false);

  const refresh = useCallback(() => setCart(getCart()), []);

  useEffect(() => {
    refresh();
    window.addEventListener(CART_CHANGED_EVENT, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(CART_CHANGED_EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, [refresh]);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  const count = cartItemCount(cart);
  if (!count || !cart) return null;

  const checkoutHref = "/checkout";

  return (
    <>
      <button
        type="button"
        className="customer-cart-fab btn btn--primary"
        aria-expanded={open}
        aria-controls="customer-cart-drawer"
        onClick={() => setOpen((v) => !v)}
      >
        Cart · {count}
      </button>

      {open && (
        <div className="customer-cart-drawer-scrim" onClick={() => setOpen(false)} />
      )}

      <aside
        id="customer-cart-drawer"
        className={`customer-cart-drawer glass${open ? " customer-cart-drawer--open" : ""}`}
        aria-hidden={!open}
      >
        <header className="customer-cart-drawer__head">
          <div>
            <h2>Your cart</h2>
            <p>
              {cart.kitchens.length} kitchen{cart.kitchens.length === 1 ? "" : "s"} · ₹
              {cartSubtotal(cart).toFixed(0)}
            </p>
          </div>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setOpen(false)}>
            Close
          </button>
        </header>

        <div className="customer-cart-drawer__body">
          {cart.kitchens.map((kitchen) => (
            <section key={kitchen.kitchenId} className="customer-checkout__card">
              <h2>
                {kitchen.kitchenName} · {kitchen.kitchenCode}
              </h2>
              <ul className="customer-checkout__lines">
                {kitchen.lines.map((line) => (
                  <li key={line.dishId}>
                    <span>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm customer-cart-drawer__qty"
                        aria-label={`Decrease ${line.dishName}`}
                        onClick={() => setCart(updateLineQuantity(line.dishId, line.quantity - 1))}
                      >
                        −
                      </button>
                      <span className="customer-cart-drawer__count">{line.quantity}</span>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm customer-cart-drawer__qty"
                        aria-label={`Increase ${line.dishName}`}
                        onClick={() =>
                          setCart(updateLineQuantity(line.dishId, Math.min(20, line.quantity + 1)))
                        }
                      >
                        +
                      </button>
                      {" "}
                      {line.dishName}
                    </span>
                    <span>₹{(line.unitPrice * line.quantity).toFixed(0)}</span>
                  </li>
                ))}
              </ul>
              <div className="customer-checkout__row">
                <span>Kitchen subtotal</span>
                <strong>₹{kitchenCartSubtotal(kitchen).toFixed(0)}</strong>
              </div>
            </section>
          ))}
        </div>

        <footer className="customer-cart-drawer__foot">
          <Link to={checkoutHref} className="btn btn--primary" onClick={() => setOpen(false)}>
            Checkout · ₹{cartSubtotal(cart).toFixed(0)}
          </Link>
        </footer>
      </aside>
    </>
  );
}
