import { useEffect, useMemo, useState } from "react";
import { ListingToolbar } from "../../components/ListingToolbar";
import { OwnerEmpty, OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import {
  fetchCrmCustomers,
  updateCrmCustomerTags,
  type CrmCustomer,
} from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";

const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;

type CrmSort = "spend_desc" | "spend_asc" | "orders_desc" | "name_asc" | "name_desc";

export function CrmPage() {
  const { kitchen } = useKitchen();
  const [customers, setCustomers] = useState<CrmCustomer[]>([]);
  const [syncedAt, setSyncedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tagDraft, setTagDraft] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<CrmSort>("spend_desc");
  const [segment, setSegment] = useState("");

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

  const shown = useMemo(() => {
    let list = [...customers];
    if (search.trim()) {
      const n = search.trim().toLowerCase();
      list = list.filter(
        (c) =>
          (c.customer_name || "").toLowerCase().includes(n) ||
          (c.customer_phone || "").includes(n) ||
          c.tags.some((t) => t.includes(n)) ||
          c.favorite_dishes.some((d) => d.dish_name.toLowerCase().includes(n)),
      );
    }
    if (segment === "vip") list = list.filter((c) => c.order_count >= 5);
    if (segment === "repeat") list = list.filter((c) => c.order_count >= 2);
    if (segment === "tagged") list = list.filter((c) => c.tags.length > 0);
    list.sort((a, b) => {
      switch (sort) {
        case "spend_asc":
          return a.total_spend - b.total_spend;
        case "orders_desc":
          return b.order_count - a.order_count;
        case "name_asc":
          return (a.customer_name || a.customer_phone || "").localeCompare(
            b.customer_name || b.customer_phone || "",
          );
        case "name_desc":
          return (b.customer_name || b.customer_phone || "").localeCompare(
            a.customer_name || a.customer_phone || "",
          );
        default:
          return b.total_spend - a.total_spend;
      }
    });
    return list;
  }, [customers, search, sort, segment]);

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
          <ListingToolbar
            search={search}
            onSearchChange={setSearch}
            searchPlaceholder="Search name, phone, tags, dishes…"
            sort={sort}
            onSortChange={(v) => setSort(v as CrmSort)}
            sortOptions={[
              { value: "spend_desc", label: "Spend ↓" },
              { value: "spend_asc", label: "Spend ↑" },
              { value: "orders_desc", label: "Orders ↓" },
              { value: "name_asc", label: "Name A–Z" },
              { value: "name_desc", label: "Name Z–A" },
            ]}
            filterChips={[
              { id: "vip", label: "VIP (5+)" },
              { id: "repeat", label: "Repeat" },
              { id: "tagged", label: "Tagged" },
            ]}
            activeFilter={segment}
            onFilterChange={setSegment}
            resultCount={shown.length}
          />
          {shown.length === 0 ? (
            <OwnerEmpty message="No customers match this search or filter." />
          ) : (
            <div className="owner-table-wrap">
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
                  {shown.map((c) => (
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
          )}
        </OwnerPanel>
      )}
    </OwnerPageShell>
  );
}
