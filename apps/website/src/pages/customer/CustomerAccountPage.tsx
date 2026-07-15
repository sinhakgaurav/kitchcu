import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  fetchCustomerProfile,
  getCustomerToken,
  updateCustomerPayout,
  uploadCustomerPayoutQr,
  type CustomerProfile,
} from "../../shared/customerApi";

export function CustomerAccountPage() {
  const token = getCustomerToken();
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [upi, setUpi] = useState("");
  const [bankAccount, setBankAccount] = useState("");
  const [bankIfsc, setBankIfsc] = useState("");
  const [bankName, setBankName] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    fetchCustomerProfile()
      .then((p) => {
        setProfile(p);
        setUpi(p.upi_vpa ?? "");
        setBankIfsc(p.bank_ifsc ?? "");
        setBankName(p.bank_account_name ?? "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load profile"));
  }, [token]);

  if (!token) {
    return <Navigate to="/login?next=/account" replace />;
  }

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setOk("");
    setBusy(true);
    try {
      const next = await updateCustomerPayout({
        upi_vpa: upi.trim() || null,
        bank_account_number: bankAccount.trim() || null,
        bank_ifsc: bankIfsc.trim() || null,
        bank_account_name: bankName.trim() || null,
      });
      setProfile(next);
      setBankAccount("");
      setOk("Payout details saved — kitchens can refund to this UPI or bank account.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const onQr = async (file: File | null) => {
    if (!file) return;
    setError("");
    setOk("");
    setBusy(true);
    try {
      const next = await uploadCustomerPayoutQr(file);
      setProfile(next);
      setOk("UPI QR image uploaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container customer-page__body" style={{ maxWidth: 560, padding: "2rem 1rem 3rem" }}>
      <p style={{ marginBottom: "0.5rem" }}>
        <Link to="/orders">← My orders</Link>
      </p>
      <h1>Refund payout details</h1>
      <p>
        Save your UPI ID, QR scanner image, and bank account so kitchen owners can send full or
        partial refunds directly (remark = order id).
      </p>

      {error && <div className="auth-card__error">{error}</div>}
      {ok && <p className="auth-card__hint">{ok}</p>}

      <form className="glass customer-search" onSubmit={save}>
        <label>
          UPI ID
          <input value={upi} onChange={(e) => setUpi(e.target.value)} placeholder="priya@okaxis" />
        </label>
        <label>
          Bank account number
          <input
            value={bankAccount}
            onChange={(e) => setBankAccount(e.target.value)}
            placeholder={
              profile?.bank_account_number_masked
                ? `Saved: ${profile.bank_account_number_masked}`
                : "Enter account number"
            }
          />
        </label>
        <label>
          IFSC
          <input value={bankIfsc} onChange={(e) => setBankIfsc(e.target.value)} placeholder="HDFC0001234" />
        </label>
        <label>
          Account holder name
          <input value={bankName} onChange={(e) => setBankName(e.target.value)} placeholder="Priya Customer" />
        </label>
        <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
          {busy ? "Saving…" : "Save payout details"}
        </button>
      </form>

      <section className="glass customer-search" style={{ marginTop: "1.25rem" }}>
        <h2>UPI QR / scanner image</h2>
        <p>Optional — owners can use this when sending a direct UPI refund.</p>
        {profile?.upi_qr_url && (
          <img
            src={profile.upi_qr_url}
            alt="Your UPI QR"
            style={{ maxWidth: 220, width: "100%", borderRadius: 8, marginBottom: "0.75rem" }}
          />
        )}
        <label>
          Upload image
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => onQr(e.target.files?.[0] ?? null)}
            disabled={busy}
          />
        </label>
      </section>
    </div>
  );
}
