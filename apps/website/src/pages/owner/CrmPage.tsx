import { useEffect, useState } from "react";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  fetchCrmCustomers,
  updateCrmCustomerTags,
  type CrmCustomer,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

export function CrmPage() {
  const { kitchen } = useKitchen();
  const [customers, setCustomers] = useState<CrmCustomer[]>([]);
  const [syncedAt, setSyncedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tagDraft, setTagDraft] = useState<Record<string, string>>({});

  const load = (refresh = true) => {
    if (!kitchen) return;
    setLoading(true);
    setError("");
    fetchCrmCustomers(kitchen.id, refresh)
      .then((res) => {
        setCustomers(res.customers);
        setSyncedAt(res.synced_at);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load CRM"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(true);
  }, [kitchen]);

  const saveTags = async (customer: CrmCustomer) => {
    if (!kitchen) return;
    const raw = tagDraft[customer.id] ?? customer.tags.join(", ");
    const tags = raw
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);
    try {
      const updated = await updateCrmCustomerTags(kitchen.id, customer.id, tags);
      setCustomers((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save tags");
    }
  };

  if (!kitchen) return null;

  return (
    <OwnerPageShell
      eyebrow="Growth"
      title="Customer CRM"
      description="Spend, favorites & order patterns — synced from your orders"
      meta={
        syncedAt ? (
          <p className="owner-page__meta">
            Last synced {new Date(syncedAt).toLocaleString("en-IN")}
          </p>
        ) : undefined
      }
      actions={
        <button
          type="button"
          className="btn btn--secondary"
          onClick={() => load(true)}
          disabled={loading}
        >
          Refresh from orders
        </button>
      }
    >
      {error && <p className="form-error">{error}</p>}
      {loading ? (
        <div className="app-loading">Loading customers…</div>
      ) : customers.length === 0 ? (
        <OwnerEmpty message="No customers yet — orders with phone numbers appear here." />
      ) : (
        <OwnerPanel
          title="Your customers"
          description={`${customers.length} contact${customers.length !== 1 ? "s" : ""} with order history`}
        >
          <div className="owner-table-wrap dash-card">
            <table className="owner-table">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Orders</th>
                  <th>Total spend</th>
                  <th>This month</th>
                  <th>Favorites</th>
                  <th>Patterns</th>
                  <th>Tags</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <strong>{c.customer_name ?? "Guest"}</strong>
                      <br />
                      <span className="owner-muted">{c.customer_phone}</span>
                    </td>
                    <td>{c.order_count}</td>
                    <td>{inr(c.total_spend)}</td>
                    <td>{inr(c.monthly_spend)}</td>
                    <td>
                      {c.favorite_dishes.slice(0, 2).map((d) => (
                        <span key={d.dish_id} className="owner-chip">
                          {d.dish_name} ×{d.quantity}
                        </span>
                      ))}
                    </td>
                    <td>
                      {c.order_patterns.peak_hours.length > 0 && (
                        <span className="owner-muted">
                          Peak {c.order_patterns.peak_hours.join(", ")}h
                        </span>
                      )}
                    </td>
                    <td>
                      <input
                        className="owner-input owner-input--compact"
                        value={tagDraft[c.id] ?? c.tags.join(", ")}
                        onChange={(e) =>
                          setTagDraft((prev) => ({ ...prev, [c.id]: e.target.value }))
                        }
                        placeholder="vip, weekend"
                      />
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => saveTags(c)}
                      >
                        Save
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </OwnerPanel>
      )}
    </OwnerPageShell>
  );
}
