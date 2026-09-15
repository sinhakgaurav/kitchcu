import { FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CustomerAvatar } from "../../components/CustomerAvatar";
import { CustomerProfilePhotos } from "../../components/CustomerProfilePhotos";
import {
  fetchCustomerProfile,
  getCustomerToken,
  updateCustomerPayout,
  uploadCustomerPayoutQr,
  type CustomerProfile,
} from "../../shared/customerApi";
import { useCustomerAuth } from "../../shared/customerAuth";
import { maskCustomerPhone } from "../../shared/customerUi";

export function CustomerAccountPage() {
  const { t } = useTranslation();
  const token = getCustomerToken();
  const { logout, loading: authLoading } = useCustomerAuth();
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

  if (authLoading) {
    return <p className="app-loading">{t("common.loading")}</p>;
  }
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

  const payoutReady = Boolean(profile?.upi_vpa || profile?.bank_account_number_masked);

  return (
    <div className="container customer-dash customer-account">
      <header className="customer-space__hero">
        <div className="customer-space__identity">
          <CustomerAvatar
            name={profile?.name}
            src={profile?.avatar_url}
            size="lg"
            live={Boolean(profile?.has_live_photo)}
          />
          <div>
            <p className="customer-dash__eyebrow">{t("customer.account.title")}</p>
            <h1>{t("customer.account.pageTitle")}</h1>
            <p className="customer-space__meta">
              {profile?.phone ? maskCustomerPhone(profile.phone) : t("customer.dashboard.phoneUnlinked")}
              {profile?.email ? ` · ${profile.email}` : ""}
            </p>
            <p className="customer-space__meta">{t("customer.account.intro")}</p>
          </div>
        </div>
        <div className="customer-dash__hero-actions">
          <Link to="/dashboard?tab=account" className="btn btn--ghost btn--sm">
            {t("customer.account.backToSpace")}
          </Link>
          <Link to="/orders" className="btn btn--ghost btn--sm">
            {t("customer.account.myOrders")}
          </Link>
        </div>
      </header>

      {error && <div className="auth-card__error">{error}</div>}
      {ok && <p className="customer-dash__ok" role="status">{ok}</p>}

      {profile ? <CustomerProfilePhotos profile={profile} onUpdated={setProfile} /> : null}

      {payoutReady ? (
        <p className="customer-dash__ok" role="status">
          {t("customer.account.payoutStatusReady")}
        </p>
      ) : null}

      <form className="glass customer-dash__card" onSubmit={save}>
        <h2>{t("customer.account.payout")}</h2>
        <label>
          {t("customer.account.upiId")}
          <input value={upi} onChange={(e) => setUpi(e.target.value)} placeholder="priya@okaxis" autoComplete="off" />
        </label>
        <label>
          {t("customer.account.bankAccount")}
          <input
            value={bankAccount}
            onChange={(e) => setBankAccount(e.target.value)}
            placeholder={
              profile?.bank_account_number_masked
                ? t("customer.account.savedMasked", { masked: profile.bank_account_number_masked })
                : t("customer.account.enterAccount")
            }
            autoComplete="off"
          />
        </label>
        <label>
          {t("customer.account.ifsc")}
          <input value={bankIfsc} onChange={(e) => setBankIfsc(e.target.value)} placeholder="HDFC0001234" autoComplete="off" />
        </label>
        <label>
          {t("customer.account.accountHolder")}
          <input value={bankName} onChange={(e) => setBankName(e.target.value)} placeholder="Priya Customer" />
        </label>
        <button type="submit" className="btn btn--primary" disabled={busy}>
          {busy ? t("customer.account.saving") : t("customer.account.savePayout")}
        </button>
      </form>

      <section className="glass customer-dash__card">
        <h2>{t("customer.account.upiQrTitle")}</h2>
        <p className="auth-card__hint">{t("customer.account.upiQrHint")}</p>
        {profile?.upi_qr_url ? (
          <img className="customer-account__qr" src={profile.upi_qr_url} alt={t("customer.account.upiQrTitle")} />
        ) : null}
        <label className="customer-qr-drop">
          <span>{profile?.upi_qr_url ? t("customer.account.qrChange") : t("customer.account.uploadImage")}</span>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => onQr(e.target.files?.[0] ?? null)}
            disabled={busy}
          />
        </label>
      </section>

      <div className="customer-dash__signout">
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => {
            logout();
            navigate("/login", { replace: true });
          }}
        >
          {t("customer.account.logOut")}
        </button>
      </div>
    </div>
  );
}
