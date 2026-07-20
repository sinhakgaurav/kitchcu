import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import { useKitchen } from "../../shared/kitchenContext";
import { getToken } from "../../shared/api";
import {
  bulkOwnerCustomerReferrals,
  fetchOwnerReferrals,
  ownerReferralTemplateUrl,
  submitOwnerCustomerReferral,
  uploadOwnerReferralCsv,
  type ReferralDashboard,
} from "../../shared/referralApi";

const inr = (n: number) => `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;

type Row = { contact_name: string; contact_phone: string; contact_email: string; city: string; notes: string };

const emptyRow = (): Row => ({
  contact_name: "",
  contact_phone: "",
  contact_email: "",
  city: "",
  notes: "",
});

export function ReferralsPage() {
  const { t } = useTranslation();
  const { kitchen } = useKitchen();
  const [dash, setDash] = useState<ReferralDashboard | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [rows, setRows] = useState<Row[]>([emptyRow(), emptyRow()]);

  const reload = () =>
    fetchOwnerReferrals()
      .then(setDash)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));

  useEffect(() => {
    reload();
  }, []);

  const submitRows = async () => {
    if (!kitchen) return;
    setBusy(true);
    setError("");
    try {
      const payload = rows
        .filter((r) => r.contact_phone.trim())
        .map((r) => ({
          contact_name: r.contact_name || undefined,
          contact_phone: r.contact_phone.trim(),
          contact_email: r.contact_email || undefined,
          city: r.city || undefined,
          notes: r.notes || undefined,
        }));
      if (payload.length === 1) {
        await submitOwnerCustomerReferral({ kitchen_id: kitchen.id, ...payload[0] });
      } else {
        const result = await bulkOwnerCustomerReferrals(kitchen.id, payload);
        if (result.rejected) {
          setError(`${result.accepted} accepted, ${result.rejected} rejected. ${result.errors[0] || ""}`);
        }
      }
      setRows([emptyRow(), emptyRow()]);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submit failed");
    } finally {
      setBusy(false);
    }
  };

  const onUpload = async (file: File | null) => {
    if (!file || !kitchen) return;
    setBusy(true);
    setError("");
    try {
      const result = await uploadOwnerReferralCsv(kitchen.id, file);
      if (result.rejected) {
        setError(`${result.accepted} accepted, ${result.rejected} rejected`);
      }
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  const downloadTemplate = async () => {
    const token = getToken();
    const res = await fetch(ownerReferralTemplateUrl(), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "kitchcu-refer-customers-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <OwnerPageShell
      eyebrow={t("owner.nav.growth")}
      title={t("owner.pages.referrals")}
      description={t("owner.referrals.title")}
    >
      {error && <div className="auth-card__error">{error}</div>}

      {dash && (
        <OwnerPanel title="Subscription credit">
          <div className="owner-stat-grid">
            <div>
              <strong>{inr(dash.credit.balance_inr)}</strong>
              <span>Available off next SaaS bill</span>
            </div>
            <div>
              <strong>{inr(dash.credit.lifetime_earned_inr)}</strong>
              <span>Lifetime earned</span>
            </div>
            <div>
              <strong>{inr(dash.credit.lifetime_applied_inr)}</strong>
              <span>Applied to subscriptions</span>
            </div>
            <div>
              <strong>{inr(dash.credit.reward_per_conversion_inr)}</strong>
              <span>Per successful referral</span>
            </div>
          </div>
          <p className="muted">{dash.credit.subscription_credit_note}</p>
          <p>
            Pending leads: {dash.pending_count} · Converted: {dash.converted_count} · Estimated savings:{" "}
            {inr(dash.estimated_subscription_savings_inr)}
          </p>
        </OwnerPanel>
      )}

      <OwnerPanel title="Add referrals">
        <div className="owner-form-actions" style={{ marginBottom: "1rem" }}>
          <button type="button" className="btn btn--ghost btn--sm" onClick={downloadTemplate}>
            Download Excel template (CSV)
          </button>
          <label className="btn btn--ghost btn--sm">
            Upload CSV
            <input
              type="file"
              accept=".csv,text/csv"
              hidden
              onChange={(e) => onUpload(e.target.files?.[0] || null)}
            />
          </label>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setRows((r) => [...r, emptyRow()])}
          >
            Add row
          </button>
        </div>

        <div className="owner-table-wrap">
          <table className="owner-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>Email</th>
                <th>City</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {(["contact_name", "contact_phone", "contact_email", "city", "notes"] as const).map(
                    (key) => (
                      <td key={key}>
                        <input
                          className="owner-input"
                          value={row[key]}
                          onChange={(e) =>
                            setRows((prev) =>
                              prev.map((r, idx) => (idx === i ? { ...r, [key]: e.target.value } : r)),
                            )
                          }
                          placeholder={key === "contact_phone" ? "9876543210" : ""}
                        />
                      </td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button type="button" className="btn btn--primary" disabled={busy || !kitchen} onClick={submitRows}>
          {busy ? "Saving…" : "Submit referrals"}
        </button>
      </OwnerPanel>

      {dash && dash.leads.length > 0 && (
        <OwnerPanel title="Your referral leads">
          <div className="owner-table-wrap">
            <table className="owner-table">
              <thead>
                <tr>
                  <th>Contact</th>
                  <th>Phone</th>
                  <th>Status</th>
                  <th>Reward</th>
                </tr>
              </thead>
              <tbody>
                {dash.leads.map((L) => (
                  <tr key={L.id}>
                    <td>{L.contact_name || "—"}</td>
                    <td>{L.contact_phone}</td>
                    <td>{L.status}</td>
                    <td>{L.reward_inr != null ? inr(L.reward_inr) : "—"}</td>
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
