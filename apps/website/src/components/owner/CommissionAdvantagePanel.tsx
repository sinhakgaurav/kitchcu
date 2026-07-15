/** Zero-commission vs aggregator apps — profit retention + price/sale impact. */

const AGGREGATOR_RATES = [
  { id: "swiggy", label: "Typical food apps", rate: 0.25, color: "#e57373" },
  { id: "high", label: "High-commission apps", rate: 0.3, color: "#ef9a9a" },
] as const;

const KITCHCU_RATE = 0;

export function CommissionAdvantagePanel({
  grossRevenue,
  avgOrderValue,
  completedOrders,
}: {
  grossRevenue: number;
  avgOrderValue: number;
  completedOrders: number;
}) {
  const inr = (n: number) => `₹${Math.round(n).toLocaleString("en-IN")}`;
  const base = Math.max(grossRevenue, avgOrderValue * Math.max(completedOrders, 1), 10000);
  const kitchcuKeep = base * (1 - KITCHCU_RATE);
  const rows = AGGREGATOR_RATES.map((a) => {
    const commission = base * a.rate;
    const keep = base - commission;
    return { ...a, commission, keep, lost: commission };
  });
  const maxBar = Math.max(kitchcuKeep, ...rows.map((r) => r.keep));

  // Price inflation needed to protect same net margin when apps take commission.
  const dishBase = Math.max(avgOrderValue || 220, 150);
  const inflate25 = dishBase / (1 - 0.25);
  const inflate30 = dishBase / (1 - 0.3);
  // Rough demand elasticity: ~1% volume drop per 1% price rise (illustrative).
  const priceRise25 = (inflate25 - dishBase) / dishBase;
  const volumeFactor25 = Math.max(0.55, 1 - priceRise25);
  const saleRev25 = inflate25 * volumeFactor25;
  const netAfterComm25 = saleRev25 * (1 - 0.25);

  return (
    <section className="dash-card od-panel commission-panel">
      <header className="od-panel__head">
        <div>
          <h2>Zero commission advantage</h2>
          <p>
            Last 7 days food sales · how much you keep on kitchCU (0% order commission) vs apps
            that take ~25–30% per order
          </p>
        </div>
      </header>

      <div className="commission-panel__compare">
        <div className="commission-bar-row">
          <span className="commission-bar-row__label">kitchCU · 0%</span>
          <div className="commission-bar-row__track">
            <div
              className="commission-bar-row__fill commission-bar-row__fill--kitchcu"
              style={{ width: `${(kitchcuKeep / maxBar) * 100}%` }}
            />
          </div>
          <strong>{inr(kitchcuKeep)}</strong>
        </div>
        {rows.map((r) => (
          <div key={r.id} className="commission-bar-row">
            <span className="commission-bar-row__label">
              {r.label} · {(r.rate * 100).toFixed(0)}%
            </span>
            <div className="commission-bar-row__track">
              <div
                className="commission-bar-row__fill commission-bar-row__fill--agg"
                style={{ width: `${(r.keep / maxBar) * 100}%`, background: r.color }}
              />
            </div>
            <strong>
              {inr(r.keep)}
              <em> −{inr(r.lost)}</em>
            </strong>
          </div>
        ))}
      </div>

      <p className="commission-panel__insight">
        On {inr(base)} of orders you keep <strong>{inr(kitchcuKeep)}</strong> here — vs about{" "}
        <strong>{inr(rows[0].keep)}</strong> after a 25% commission (you lose{" "}
        <strong>{inr(rows[0].lost)}</strong> to the platform).
      </p>

      <div className="commission-panel__impact">
        <h3>How commission raises dish price & cuts sales</h3>
        <p>
          To keep the same kitchen margin after 25% commission, a {inr(dishBase)} dish must list near{" "}
          <strong>{inr(inflate25)}</strong> (+{(priceRise25 * 100).toFixed(0)}%). Higher menu
          prices suppress orders — modeled sale revenue falls roughly to{" "}
          <strong>{inr(saleRev25)}</strong> per order, and after commission the kitchen nets only{" "}
          <strong>{inr(netAfterComm25)}</strong>.
        </p>
        <table className="commission-panel__table">
          <thead>
            <tr>
              <th>System</th>
              <th>Customer pays</th>
              <th>Kitchen nets</th>
              <th>Difference</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>kitchCU (0% order fee)</td>
              <td>{inr(dishBase)}</td>
              <td>{inr(dishBase)}</td>
              <td className="commission-panel__pos">Baseline</td>
            </tr>
            <tr>
              <td>App @ 25% + price inflate</td>
              <td>{inr(inflate25)}</td>
              <td>{inr(netAfterComm25)}</td>
              <td className="commission-panel__neg">
                −{inr(dishBase - netAfterComm25)} vs kitchCU
              </td>
            </tr>
            <tr>
              <td>App @ 30% + price inflate</td>
              <td>{inr(inflate30)}</td>
              <td>{inr(inflate30 * Math.max(0.5, 1 - (inflate30 - dishBase) / dishBase) * 0.7)}</td>
              <td className="commission-panel__neg">Worse for kitchen & customer</td>
            </tr>
          </tbody>
        </table>
        <p className="commission-panel__footnote">
          kitchCU bills a flat kitchen subscription — never a per-order food commission — so you
          can keep honest prices and retain demand.
        </p>
      </div>
    </section>
  );
}
