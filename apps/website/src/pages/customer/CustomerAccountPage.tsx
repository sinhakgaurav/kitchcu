import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  fetchCustomerProfile,
  getCustomerToken,
  updateCustomerPayout,
  uploadCustomerPayoutQr,
  type CustomerProfile,
} from "../../shared/customerApi";
import { useCustomerAuth } from "../../shared/customerAuth";

export function CustomerAccountPage() {
  const { t } = useTranslation();
  const token = getCustomerToken();
  const { logout } = useCustomerAuth();
  const navigate = useNavigate();
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
      .catch((err) => setError(err instanceof Error ? err.message : t("common.error")));
  }, [token, t]);

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
      setOk(t("customer.account.payoutSaved"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
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
      setOk(t("customer.account.qrUploaded"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container customer-page__body customer-account" style={{ maxWidth: 560, padding: "2rem 1rem 3rem" }}>
      <p style={{ marginBottom: "0.5rem" }}>
        <Link to="/orders">← {t("customer.account.myOrders")}</Link>
      </p>
      <h1>{t("customer.account.pageTitle")}</h1>
      <p className="customer-account__intro">{t("customer.account.intro")}</p>
      <nav className="customer-account-nav" aria-label={t("customer.account.pageTitle")}>
        <Link to="/dashboard" className="btn btn--ghost btn--sm">
          {t("customer.account.mySpace")}
        </Link>
        <Link to="/orders" className="btn btn--ghost btn--sm">
          {t("customer.account.myOrders")}
        </Link>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => {
            logout();
            navigate("/login", { replace: true });
          }}
        >
          {t("customer.account.logOut")}
        </button>
      </nav>
      <h2 className="customer-account__section-title">{t("customer.account.title")}</h2>
      <p>{t("customer.account.intro")}</p>

      {error && <div className="auth-card__error">{error}</div>}
      {ok && <p className="auth-card__hint">{ok}</p>}

      <form className="glass customer-search" onSubmit={save}>
        <label>
          {t("customer.account.upiId")}
          <input value={upi} onChange={(e) => setUpi(e.target.value)} placeholder="priya@okaxis" />
        </label>
        <label>
          {t("customer.account.bankAccount")}
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
          {t("customer.account.ifsc")}
          <input value={bankIfsc} onChange={(e) => setBankIfsc(e.target.value)} placeholder="HDFC0001234" />
        </label>
        <label>
          {t("customer.account.accountHolder")}
          <input value={bankName} onChange={(e) => setBankName(e.target.value)} placeholder="Priya Customer" />
        </label>
        <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
          {busy ? t("customer.account.saving") : t("customer.account.savePayout")}
        </button>
      </form>

      <section className="glass customer-search" style={{ marginTop: "1.25rem" }}>
        <h2>{t("customer.account.upiQrTitle")}</h2>
        <p>{t("customer.account.upiQrHint")}</p>
        {profile?.upi_qr_url && (
          <img
            src={profile.upi_qr_url}
            alt={t("customer.account.upiQrTitle")}
            style={{ maxWidth: 220, width: "100%", borderRadius: 8, marginBottom: "0.75rem" }}
          />
        )}
        <label>
          {t("customer.account.uploadImage")}
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
