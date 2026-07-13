import { useEffect, useMemo, useState } from "react";
import { OwnerPageShell, OwnerPanel, OwnerEmpty } from "../../components/owner/OwnerPageShell";
import { useKitchen } from "../../lib/kitchen";
import {
  closeGstAudit,
  fetchGstAudit,
  fetchGstBalanceSheet,
  fetchGstMonthlyReport,
  fetchGstProfile,
  syncGstInvoices,
  upsertGstProfile,
  type GstAudit,
  type GstBalanceSheet,
  type GstMonthlyReport,
  type GstProfile,
} from "../../lib/api";

const inr = (n: number) => `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function BalanceSheetView({ sheet }: { sheet: GstBalanceSheet }) {
  return (
    <div className="gst-balance-grid">
      <div className="gst-balance-col">
        <h3>Assets</h3>
        <ul>
          {sheet.assets.map((line) => (
            <li key={line.label}>
              <span>{line.label}</span>
              <strong>{inr(line.amount)}</strong>
            </li>
          ))}
        </ul>
        <p className="gst-balance-total">Total assets: {inr(sheet.total_assets)}</p>
      </div>
      <div className="gst-balance-col">
        <h3>Liabilities</h3>
        <ul>
          {sheet.liabilities.map((line) => (
            <li key={line.label}>
              <span>{line.label}</span>
              <strong>{inr(line.amount)}</strong>
            </li>
          ))}
        </ul>
        <p className="gst-balance-total">Total liabilities: {inr(sheet.total_liabilities)}</p>
      </div>
      <div className="gst-balance-col">
        <h3>Equity</h3>
        <ul>
          {sheet.equity.map((line) => (
            <li key={line.label}>
              <span>{line.label}</span>
              <strong>{inr(line.amount)}</strong>
            </li>
          ))}
        </ul>
        <p className="gst-balance-total">Total equity: {inr(sheet.total_equity)}</p>
      </div>
    </div>
  );
}

export function GstFinancePage() {
  const { kitchen } = useKitchen();
  const now = useMemo(() => new Date(), []);
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [profile, setProfile] = useState<GstProfile | null>(null);
  const [report, setReport] = useState<GstMonthlyReport | null>(null);
  const [audit, setAudit] = useState<GstAudit | null>(null);
  const [balanceSheet, setBalanceSheet] = useState<GstBalanceSheet | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showSetup, setShowSetup] = useState(false);
  const [form, setForm] = useState({
    gstin: "",
    legal_name: "",
    trade_name: "",
    registered_address: "",
    default_tax_rate: "5",
    is_active: true,
  });

  const loadData = async (kitchenId: string, y: number, m: number) => {
    setError("");
    setLoading(true);
    try {
      const prof = await fetchGstProfile(kitchenId);
      setProfile(prof);
      if (prof) {
        setForm({
          gstin: prof.gstin,
          legal_name: prof.legal_name,
          trade_name: prof.trade_name ?? "",
          registered_address: prof.registered_address,
          default_tax_rate: String(prof.default_tax_rate),
          is_active: prof.is_active,
        });
        const [rep, aud, sheet] = await Promise.all([
          fetchGstMonthlyReport(kitchenId, y, m),
          fetchGstAudit(kitchenId, y, m),
          fetchGstBalanceSheet(kitchenId, y, m),
        ]);
        setReport(rep);
        setAudit(aud);
        setBalanceSheet(sheet);
      } else {
        setReport(null);
        setAudit(null);
        setBalanceSheet(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load GST data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!kitchen) return;
    void loadData(kitchen.id, year, month);
  }, [kitchen, year, month]);

  const saveProfile = async () => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      const saved = await upsertGstProfile(kitchen.id, {
        gstin: form.gstin.trim().toUpperCase(),
        legal_name: form.legal_name.trim(),
        trade_name: form.trade_name.trim() || null,
        registered_address: form.registered_address.trim(),
        default_tax_rate: Number(form.default_tax_rate) || 5,
        is_active: form.is_active,
      });
      setProfile(saved);
      setShowSetup(false);
      await loadData(kitchen.id, year, month);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save GST profile");
    } finally {
      setBusy(false);
    }
  };

  const runSync = async () => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      await syncGstInvoices(kitchen.id, year, month);
      await loadData(kitchen.id, year, month);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  };

  const closeMonth = async () => {
    if (!kitchen || !audit || audit.status === "closed") return;
    if (!window.confirm(`Close GST audit for ${MONTHS[month - 1]} ${year}? This locks the period.`)) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      const closed = await closeGstAudit(kitchen.id, year, month);
      setAudit(closed);
      if (closed.balance_sheet) setBalanceSheet(closed.balance_sheet);
      await loadData(kitchen.id, year, month);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not close audit");
    } finally {
      setBusy(false);
    }
  };

  if (!kitchen) return <div className="owner-screen app-loading">Loading kitchen…</div>;
  if (loading) return <div className="owner-screen app-loading">Loading GST & finance…</div>;

  return (
    <OwnerPageShell
      eyebrow="Finance"
      title="GST & monthly audit"
      description="Register your GSTIN, sync tax invoices from delivered orders, and close monthly audits with balance sheet snapshots."
      actions={
        profile ? (
          <>
            <button type="button" className="btn btn--ghost" onClick={() => setShowSetup((v) => !v)} disabled={busy}>
              {showSetup ? "Hide setup" : "Edit GST profile"}
            </button>
            <button type="button" className="btn btn--primary" onClick={runSync} disabled={busy || audit?.status === "closed"}>
              Sync invoices
            </button>
          </>
        ) : null
      }
    >
      {error && <p className="owner-alert owner-alert--error">{error}</p>}

      <OwnerPanel title="Period">
        <div className="gst-period-row">
          <label className="kc-field">
            <span className="kc-field__label">Year</span>
            <select className="kc-select" value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {[year - 1, year, year + 1].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </label>
          <label className="kc-field">
            <span className="kc-field__label">Month</span>
            <select className="kc-select" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
              {MONTHS.map((label, idx) => (
                <option key={label} value={idx + 1}>{label}</option>
              ))}
            </select>
          </label>
          {audit && (
            <span className={`gst-audit-badge gst-audit-badge--${audit.status}`}>
              Audit {audit.status}
            </span>
          )}
        </div>
      </OwnerPanel>

      {(!profile || showSetup) && (
        <OwnerPanel title={profile ? "Update GST registration" : "Enable GST registration"}>
          <div className="gst-setup-grid">
            <label className="kc-field">
              <span className="kc-field__label">GSTIN (15 characters)</span>
              <input
                className="kc-input"
                value={form.gstin}
                onChange={(e) => setForm((f) => ({ ...f, gstin: e.target.value.toUpperCase() }))}
                maxLength={15}
                placeholder="27AABCU9603R1ZM"
              />
            </label>
            <label className="kc-field">
              <span className="kc-field__label">Legal name</span>
              <input
                className="kc-input"
                value={form.legal_name}
                onChange={(e) => setForm((f) => ({ ...f, legal_name: e.target.value }))}
              />
            </label>
            <label className="kc-field">
              <span className="kc-field__label">Trade name (optional)</span>
              <input
                className="kc-input"
                value={form.trade_name}
                onChange={(e) => setForm((f) => ({ ...f, trade_name: e.target.value }))}
              />
            </label>
            <label className="kc-field gst-setup-grid__full">
              <span className="kc-field__label">Registered address</span>
              <textarea
                className="kc-input"
                rows={3}
                value={form.registered_address}
                onChange={(e) => setForm((f) => ({ ...f, registered_address: e.target.value }))}
              />
            </label>
            <label className="kc-field">
              <span className="kc-field__label">Default food GST %</span>
              <input
                className="kc-input"
                type="number"
                min={0}
                max={28}
                step={0.1}
                value={form.default_tax_rate}
                onChange={(e) => setForm((f) => ({ ...f, default_tax_rate: e.target.value }))}
              />
            </label>
            <label className="kc-field kc-field--checkbox">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
              />
              <span>GST billing active</span>
            </label>
          </div>
          <button type="button" className="btn btn--primary" onClick={saveProfile} disabled={busy}>
            {profile ? "Save changes" : "Register GST"}
          </button>
        </OwnerPanel>
      )}

      {profile && report && (
        <>
          <div className="od-board__kpi-grid">
            <div className="dash-card od-kpi">
              <span className="od-kpi__label">Taxable value</span>
              <strong>{inr(report.total_taxable)}</strong>
            </div>
            <div className="dash-card od-kpi">
              <span className="od-kpi__label">Output tax (CGST + SGST)</span>
              <strong>{inr(report.total_cgst + report.total_sgst + report.total_igst)}</strong>
            </div>
            <div className="dash-card od-kpi">
              <span className="od-kpi__label">Gross sales</span>
              <strong>{inr(report.total_gross_sales)}</strong>
            </div>
            <div className="dash-card od-kpi">
              <span className="od-kpi__label">Tax invoices</span>
              <strong>{report.invoice_count}</strong>
            </div>
          </div>

          <OwnerPanel
            title={`GST report — ${MONTHS[month - 1]} ${year}`}
            action={
              <div className="gst-panel-head">
                <span className="gst-meta">{report.gstin} · {report.legal_name}</span>
                {audit?.status === "open" ? (
                  <button type="button" className="btn btn--ghost btn--sm" onClick={closeMonth} disabled={busy}>
                    Close monthly audit
                  </button>
                ) : null}
              </div>
            }
          >
            <div className="owner-table-wrap">
              <table className="owner-table">
                <thead>
                  <tr>
                    <th>Invoice</th>
                    <th>Order</th>
                    <th>Date</th>
                    <th>Taxable</th>
                    <th>CGST</th>
                    <th>SGST</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {report.invoices.length === 0 ? (
                    <tr>
                      <td colSpan={7}>
                        <OwnerEmpty message="No tax invoices this month — deliver orders and run Sync invoices." />
                      </td>
                    </tr>
                  ) : (
                    report.invoices.map((inv) => (
                      <tr key={inv.id}>
                        <td>{inv.invoice_number}</td>
                        <td>{inv.order_code}</td>
                        <td>{new Date(inv.invoice_date).toLocaleDateString("en-IN")}</td>
                        <td>{inr(inv.taxable_value)}</td>
                        <td>{inr(inv.cgst_amount)}</td>
                        <td>{inr(inv.sgst_amount)}</td>
                        <td>{inr(inv.gross_total)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </OwnerPanel>

          {balanceSheet && (
            <OwnerPanel title="Balance sheet (month-end snapshot)">
              <BalanceSheetView sheet={balanceSheet} />
            </OwnerPanel>
          )}
        </>
      )}

      {!profile && !showSetup && (
        <OwnerEmpty
          message="GST not registered — add your GSTIN to generate tax invoices, monthly reports, and audit-ready balance sheets."
          action={
            <button type="button" className="btn btn--primary" onClick={() => setShowSetup(true)}>
              Register GST
            </button>
          }
        />
      )}
    </OwnerPageShell>
  );
}
