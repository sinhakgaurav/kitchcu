import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import { PhoneField } from "../../components/PhoneField";
import { useKitchen } from "../../shared/kitchenContext";
import { getToken } from "../../shared/api";
import {
  firstError,
  toE164,
  validateEmail,
  validateNationalPhone,
  validatePersonName,
  validateText,
} from "../../shared/validation";
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
type RowErrors = Partial<Record<keyof Row, string>>;

const ROW_FIELDS = ["contact_name", "contact_phone", "contact_email", "city", "notes"] as const;

const emptyRow = (): Row => ({
  contact_name: "",
  contact_phone: "",
  contact_email: "",
  city: "",
  notes: "",
});

const isBlankRow = (row: Row) => ROW_FIELDS.every((key) => !row[key].trim());

const validateRow = (row: Row): RowErrors => ({
  contact_name: validatePersonName(row.contact_name, { required: false }) ?? undefined,
  contact_phone: validateNationalPhone(row.contact_phone) ?? undefined,
  contact_email: validateEmail(row.contact_email, { required: false }) ?? undefined,
  city: validateText(row.city, "a city", { required: false, max: 80 }) ?? undefined,
  notes: validateText(row.notes, "a note", { required: false, max: 500 }) ?? undefined,
});

export function ReferralsPage() {
  const { t } = useTranslation();
  const { kitchen } = useKitchen();
  const [dash, setDash] = useState<ReferralDashboard | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [rows, setRows] = useState<Row[]>([emptyRow(), emptyRow()]);
  const [rowErrors, setRowErrors] = useState<RowErrors[]>([]);

  const updateRow = (index: number, key: keyof Row, value: string) => {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, [key]: value } : r)));
    setRowErrors((prev) => prev.map((e, i) => (i === index ? { ...e, [key]: undefined } : e)));
  };

  const reload = () =>
    fetchOwnerReferrals()
      .then(setDash)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));

  useEffect(() => {
    reload();
  }, []);

  const submitRows = async () => {
    if (!kitchen) return;
    const filled = rows.filter((r) => !isBlankRow(r));
    if (filled.length === 0) {
      setError("Add at least one referral with a mobile number");
      return;
    }
    const nextRowErrors = rows.map((r) => (isBlankRow(r) ? {} : validateRow(r)));
    setRowErrors(nextRowErrors);
    const firstMessage = nextRowErrors.map(firstError).find(Boolean);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const payload = filled.map((r) => ({
        contact_name: r.contact_name.trim() || undefined,
        contact_phone: toE164(r.contact_phone),
        contact_email: r.contact_email.trim() || undefined,
        city: r.city.trim() || undefined,
        notes: r.notes.trim() || undefined,
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
      setRowErrors([]);
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
        <OwnerPanel title={t("owner.panels.subCredit")}>
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

      <OwnerPanel title={t("owner.panels.addReferrals")}>
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
                  {ROW_FIELDS.map((key) => (
                    <td key={key}>
                      {key === "contact_phone" ? (
                        <PhoneField
                          className="phone-field--bare"
                          label="Phone"
                          value={row.contact_phone}
                          onChange={(national) => updateRow(i, key, national)}
                          error={rowErrors[i]?.contact_phone}
                        />
                      ) : (
                        <>
                          <input
                            className={
                              rowErrors[i]?.[key] ? "owner-input input-invalid" : "owner-input"
                            }
                            value={row[key]}
                            onChange={(e) => updateRow(i, key, e.target.value)}
                            aria-invalid={Boolean(rowErrors[i]?.[key])}
                          />
                          {rowErrors[i]?.[key] ? (
                            <span className="field-error">{rowErrors[i][key]}</span>
                          ) : null}
                        </>
                      )}
                    </td>
                  ))}
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
        <OwnerPanel title={t("owner.panels.referralLeads")}>
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
