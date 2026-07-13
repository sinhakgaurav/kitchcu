import { Link, useLocation, useParams } from "react-router-dom";
import type { Order } from "../../shared/api";

type ConfirmState = {
  order: Order;
  paymentMethod: string;
};

export function OrderConfirmPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const location = useLocation();
  const state = location.state as ConfirmState | null;

  if (!state?.order || state.order.id !== orderId) {
    return (
      <div className="container customer-checkout">
        <h1>Order placed</h1>
        <p>Thank you! Your kitchen will confirm shortly.</p>
        <Link to="/" className="btn btn--primary">Back to home</Link>
      </div>
    );
  }

  const { order, paymentMethod } = state;

  return (
    <div className="container customer-checkout">
      <header className="owner-page__head">
        <div>
          <h1>Order confirmed</h1>
          <p>{order.order_code}</p>
        </div>
        <span className="status-badge status-badge--received status-badge--lg">Received</span>
      </header>

      <section className="glass">
        <p>Total <strong>₹{order.total.toFixed(0)}</strong> · {paymentMethod.toUpperCase()}</p>
        <p>The kitchen will update your order status. No per-order commission — subscription SaaS only.</p>
        <ul className="owner-detail-items">
          {order.items.map((item) => (
            <li key={item.id}>
              <span>{item.quantity}× {item.dish_name}</span>
              <span>₹{(item.unit_price * item.quantity).toFixed(0)}</span>
            </li>
          ))}
        </ul>
      </section>

      <Link to="/orders" className="btn btn--primary">View my orders</Link>
      <Link to="/" className="btn btn--ghost">Discover more kitchens</Link>
    </div>
  );
}
