import { Link, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { useKitchen } from "../../lib/kitchen";
import { useKitchenAuth } from "../../shared/kitchenAuth";
import { fetchDrafts, fetchMenu, fetchOrders } from "../../lib/api";
import { CUSTOMER_HOST } from "../../shared/brand";
import { customerUrl } from "../../shared/urls";

export function OwnerHomePage() {
  const { kitchen, kitchens, loading } = useKitchen();
  const { owner } = useKitchenAuth();
  const [stats, setStats] = useState({ active: 0, drafts: 0, dishes: 0 });

  useEffect(() => {
    if (!kitchen) return;
    Promise.all([
      fetchOrders(kitchen.id),
      fetchDrafts(kitchen.id),
      fetchMenu(kitchen.id),
    ]).then(([orders, drafts, menu]) => {
      setStats({
        active: orders.orders.filter((o: { status: string }) => !["delivered", "cancelled"].includes(o.status)).length,
        drafts: drafts.total,
        dishes: menu.dishes.length,
      });
    }).catch(() => {});
  }, [kitchen]);

  if (!loading && kitchens.length === 0) {
    return <Navigate to="/dashboard/setup" replace />;
  }

  if (!kitchen) return null;

  const menuLink = customerUrl(`/kitchen/${kitchen.id}/menu`);

  return (
    <div className="owner-page">
      <header className="owner-page__head">
        <div>
          <h1>{kitchen.name}</h1>
          <p className="owner-page__code">
            {kitchen.code} · {kitchen.city}, {kitchen.state}
            {owner && (
              <> · <Link to="/dashboard/subscription">{owner.subscription_tier} ({owner.subscription_status})</Link></>
            )}
          </p>
        </div>
        <Link to="/dashboard/orders/new" className="btn btn--primary">New Order</Link>
      </header>

      <div className="owner-stats">
        <Link to="/dashboard/orders" className="owner-stat glass">
          <strong>{stats.active}</strong>
          <span>Active orders</span>
        </Link>
        <Link to="/dashboard/orders?tab=drafts" className="owner-stat glass">
          <strong>{stats.drafts}</strong>
          <span>Order drafts</span>
        </Link>
        <Link to="/dashboard/menu" className="owner-stat glass">
          <strong>{stats.dishes}</strong>
          <span>Menu dishes</span>
        </Link>
      </div>

      <section className="glass owner-share">
        <h2>Customer menu link</h2>
        <p>Share this with your customers so they can browse your live-capture menu.</p>
        <div className="owner-share__row">
          <code>{menuLink}</code>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => navigator.clipboard.writeText(menuLink)}
          >
            Copy
          </button>
        </div>
        <p className="owner-share__hint">
          Customers open <strong>{CUSTOMER_HOST}</strong> and enter code: <strong>{kitchen.code}</strong>
        </p>
      </section>
    </div>
  );
}
