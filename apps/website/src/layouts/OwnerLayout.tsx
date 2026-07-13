import { Navigate, Outlet, Link, useLocation } from "react-router-dom";
import { APP_NAME, KITCHEN_HOST } from "../shared/brand";
import { useKitchenAuth } from "../shared/kitchenAuth";
import { useKitchen } from "../shared/kitchenContext";
import { customerUrl } from "../shared/urls";

const NAV = [
  { to: "/dashboard", label: "Overview", end: true },
  { to: "/dashboard/orders", label: "Orders" },
  { to: "/dashboard/menu", label: "Menu" },
  { to: "/dashboard/reports", label: "Reports" },
  { to: "/dashboard/growth", label: "Growth" },
  { to: "/dashboard/ingredients", label: "Ingredients" },
  { to: "/dashboard/learning", label: "Learning" },
  { to: "/dashboard/community", label: "Community" },
  { to: "/dashboard/crm", label: "CRM" },
  { to: "/dashboard/coupons", label: "Coupons" },
  { to: "/dashboard/subscription", label: "Subscription" },
  { to: "/dashboard/setup", label: "Kitchen" },
];

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token, loading } = useKitchenAuth();
  if (loading) return <div className="app-loading">Loading...</div>;
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function OwnerLayout() {
  const { owner, logout } = useKitchenAuth();
  const { kitchen, kitchens, setKitchenId, loading } = useKitchen();
  const location = useLocation();

  return (
    <div className="owner-app">
      <aside className="owner-app__sidebar">
        <Link to="/" className="nav__brand owner-app__brand">
          <span className="nav__logo">{APP_NAME}</span>
          <span className="nav__tagline">{KITCHEN_HOST}</span>
        </Link>

        {kitchens.length > 1 && (
          <select
            className="owner-app__kitchen-select"
            value={kitchen?.id ?? ""}
            onChange={(e) => setKitchenId(e.target.value)}
          >
            {kitchens.map((k) => (
              <option key={k.id} value={k.id}>{k.name}</option>
            ))}
          </select>
        )}

        <nav className="owner-app__nav">
          {NAV.map((item) => {
            const active = item.end
              ? location.pathname === item.to
              : location.pathname.startsWith(item.to);
            return (
              <Link key={item.to} to={item.to} className={active ? "active" : ""}>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="owner-app__sidebar-foot">
          <span>{owner?.name}</span>
          <a href={customerUrl("/")} className="owner-app__customer-link">Customer app</a>
          <button type="button" onClick={logout}>Sign out</button>
        </div>
      </aside>

      <div className="owner-app__main">
        {loading ? (
          <div className="app-loading">Loading kitchen...</div>
        ) : (
          <Outlet context={{ kitchen }} />
        )}
      </div>
    </div>
  );
}
