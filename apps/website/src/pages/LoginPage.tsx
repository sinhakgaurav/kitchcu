import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AnimatedMesh } from "../components/AnimatedMesh";
import { AuthLoginHighlights } from "../components/AuthLoginHighlights";
import { BrandAuthArt, BrandLogo } from "../components/BrandLogo";
import { PhoneField } from "../components/PhoneField";
import { PolicyAgreement } from "../components/PolicyAgreement";
import { DEMO, DEMO_OWNERS, type DemoOwnerAccount } from "../shared/demo";
import { showDemoCredentials } from "../shared/env";
import { otpDeliveryNotice, registerOwner, requestOtp, verifyOtp } from "../shared/api";
import {
  firstError,
  otpInputValue,
  phoneInputValue,
  toE164,
  validateEmail,
  validateNationalPhone,
  validateOtp,
  validatePersonName,
} from "../shared/validation";
import { KITCHEN_HOST, CUSTOMER_HOST } from "../shared/brand";
import { useKitchenAuth } from "../shared/kitchenAuth";
import { customerUrl } from "../shared/urls";
import { SuperAdminCredentials } from "../components/SuperAdminAccess";

type Mode = "login" | "register";

export function LoginPage() {
  const { t } = useTranslation();
  const { token, login } = useKitchenAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionExpired = searchParams.get("session") === "expired";
  const nextPath = searchParams.get("next") || "/dashboard";
  const [mode, setMode] = useState<Mode>("login");
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [otpNotice, setOtpNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyPhone, setBusyPhone] = useState<string | null>(null);
  const demoVisible = showDemoCredentials();
  const [policiesAgreed, setPoliciesAgreed] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{
    name?: string;
    phone?: string;
    email?: string;
    otp?: string;
  }>({});

  if (token) return <Navigate to={nextPath.startsWith("/") ? nextPath : "/dashboard"} replace />;

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    if (!policiesAgreed) {
      setError(t("owner.auth.agreePolicies"));
      return;
    }
    setError("");
    const nextErrors: typeof fieldErrors = {
      name: validatePersonName(name) ?? undefined,
      phone: validateNationalPhone(phone) ?? undefined,
      email: validateEmail(email, { required: false }) ?? undefined,
    };
    setFieldErrors(nextErrors);
    const firstMessage = firstError(nextErrors);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
    setBusy(true);
    try {
      const e164 = toE164(phone);
      await registerOwner({ phone: e164, name, email: email || undefined });
      await requestOtp(e164);
      setOtpSent(true);
      setMode("login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  };

  const handleRequestOtp = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const phoneMessage = validateNationalPhone(phone);
    setFieldErrors(phoneMessage ? { phone: phoneMessage } : {});
    if (phoneMessage) {
      setError(phoneMessage);
      return;
    }
    setBusy(true);
    try {
      const result = await requestOtp(toE164(phone));
      setOtpNotice(otpDeliveryNotice(result));
      setOtpSent(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not send OTP";
      setError(
        /unavailable|503|WhatsApp|Configure/i.test(msg)
          ? `${msg} — Demo accounts still work with OTP ${DEMO.otp} when WhatsApp delivery is not configured.`
          : msg,
      );
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const nextErrors: typeof fieldErrors = {
      phone: validateNationalPhone(phone) ?? undefined,
      otp: validateOtp(otp) ?? undefined,
    };
    setFieldErrors(nextErrors);
    const firstMessage = firstError(nextErrors);
    if (firstMessage) {
      setError(firstMessage);
      return;
    }
    setBusy(true);
    try {
      const { access_token } = await verifyOtp(toE164(phone), otp);
      await login(access_token);
      navigate(nextPath.startsWith("/") ? nextPath : "/dashboard/orders");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid OTP");
    } finally {
      setBusy(false);
    }
  };

  const handleDemoLogin = async (account: DemoOwnerAccount) => {
    setError("");
    setBusy(true);
    setBusyPhone(account.phone);
    setMode("login");
    setPhone(phoneInputValue(account.phone));
    setOtp(DEMO.otp);
    setFieldErrors({});
    try {
      await requestOtp(account.phone);
      setOtpSent(true);
      const { access_token } = await verifyOtp(account.phone, DEMO.otp);
      await login(access_token);
      navigate(nextPath.startsWith("/") ? nextPath : "/dashboard/orders");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Demo login failed";
      const backendDown =
        /unavailable|timed out|Docker|Gateway not ready|Failed to fetch|NetworkError/i.test(msg);
      setError(
        backendDown
          ? `${msg} — on GCP: restart identity (+ stack) on the VM (see docs/DEPLOYMENT-GCP.md §11.7–11.8). Seed only after /health/ready shows identity:true.`
          : `${msg} — seed demo data: python scripts/seed-bulk-data.py (GCP) or python scripts/seed-dev-data.py (local)`,
      );
      setOtpSent(true);
    } finally {
      setBusy(false);
      setBusyPhone(null);
    }
  };

  return (
    <div className="auth-page auth-page--kitchen">
      <AnimatedMesh variant="kitchen" />
      <div className="auth-page__visual">
        <div className="auth-page__overlay" />
        <div className="auth-page__brand-stack">
          <BrandLogo variant="wordmark" className="brand-logo--lg" />
          <h1>Kitchen owner portal</h1>
          <p>Sign in on {KITCHEN_HOST} to manage orders, menu, and customer links.</p>
          <AuthLoginHighlights surface="kitchen" />
          <BrandAuthArt surface="kitchen" />
        </div>
      </div>

      <div className="auth-page__form-wrap">
        <div className="auth-page__mobile-brand">
          <BrandLogo variant="wordmark" className="brand-logo--lg" />
          <p>Kitchen owner portal · {KITCHEN_HOST}</p>
        </div>
        <div className="auth-card glass">
          <div className="auth-card__tabs">
            <button
              type="button"
              className={mode === "login" ? "active" : ""}
              onClick={() => { setMode("login"); setError(""); }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={mode === "register" ? "active" : ""}
              onClick={() => { setMode("register"); setError(""); }}
            >
              Register
            </button>
          </div>

          {sessionExpired && (
            <div className="auth-card__hint auth-card__error">
              {t("owner.auth.sessionExpired")}
            </div>
          )}

          {error && <div className="auth-card__error">{error}</div>}

          {mode === "register" ? (
            <form onSubmit={handleRegister}>
              <h2>{t("owner.auth.titleRegister")}</h2>
              <p className="auth-card__hint">Owner accounts are only for {KITCHEN_HOST} — not customer sign-in.</p>
              <label>
                {t("owner.auth.name")}
                <input
                  value={name}
                  onChange={(e) => {
                    const next = e.target.value;
                    setName(next);
                    setFieldErrors((f) => ({
                      ...f,
                      name: next.trim() ? validatePersonName(next) ?? undefined : undefined,
                    }));
                  }}
                  onBlur={() =>
                    setFieldErrors((f) => ({ ...f, name: validatePersonName(name) ?? undefined }))
                  }
                  required
                  placeholder="Raj Sharma"
                  className={fieldErrors.name ? "input-invalid" : undefined}
                  aria-invalid={Boolean(fieldErrors.name)}
                />
                {fieldErrors.name ? <span className="field-error">{fieldErrors.name}</span> : null}
              </label>
              <PhoneField
                label={t("owner.auth.phone")}
                value={phone}
                onChange={(national) => {
                  setPhone(national);
                  setFieldErrors((f) => ({
                    ...f,
                    phone: national ? validateNationalPhone(national) ?? undefined : undefined,
                  }));
                }}
                onBlur={() =>
                  setFieldErrors((f) => ({
                    ...f,
                    phone: validateNationalPhone(phone) ?? undefined,
                  }))
                }
                error={fieldErrors.phone}
                required
                placeholder={DEMO.phone}
              />
              <label>
                {t("owner.auth.email")}
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    const next = e.target.value;
                    setEmail(next);
                    setFieldErrors((f) => ({
                      ...f,
                      email: next.trim()
                        ? validateEmail(next, { required: false }) ?? undefined
                        : undefined,
                    }));
                  }}
                  onBlur={() =>
                    setFieldErrors((f) => ({
                      ...f,
                      email: validateEmail(email, { required: false }) ?? undefined,
                    }))
                  }
                  placeholder={DEMO.email}
                  className={fieldErrors.email ? "input-invalid" : undefined}
                  aria-invalid={Boolean(fieldErrors.email)}
                />
                {fieldErrors.email ? <span className="field-error">{fieldErrors.email}</span> : null}
              </label>
              <PolicyAgreement
                audience="owner"
                checked={policiesAgreed}
                onChange={setPoliciesAgreed}
              />
              <button
                type="submit"
                className="btn btn--primary btn--lg"
                disabled={busy || !policiesAgreed}
              >
                {busy ? t("common.loading") : t("owner.auth.register")}
              </button>
            </form>
          ) : (
            <form onSubmit={otpSent ? handleVerify : handleRequestOtp}>
              <h2>{t("owner.auth.titleLogin")}</h2>
              {demoVisible ? (
                <p className="auth-card__hint">
                  {t("owner.auth.demoHint", { otp: DEMO.otp })}
                </p>
              ) : null}
              <PhoneField
                label={t("owner.auth.phone")}
                value={phone}
                onChange={(national) => {
                  setPhone(national);
                  setFieldErrors((f) => ({
                    ...f,
                    phone: national ? validateNationalPhone(national) ?? undefined : undefined,
                  }));
                }}
                onBlur={() =>
                  setFieldErrors((f) => ({
                    ...f,
                    phone: validateNationalPhone(phone) ?? undefined,
                  }))
                }
                error={fieldErrors.phone}
                required
                placeholder={DEMO.phone}
              />
              {otpSent && otpNotice && <p className="auth-card__notice">{otpNotice}</p>}
              {otpSent && (
                <label>
                  {t("owner.auth.otp")}
                  <input
                    value={otp}
                    onChange={(e) => {
                      setOtp(otpInputValue(e.target.value));
                      setFieldErrors((f) => ({ ...f, otp: undefined }));
                    }}
                    required
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder={DEMO.otp}
                    maxLength={6}
                    className={fieldErrors.otp ? "input-invalid" : undefined}
                    aria-invalid={Boolean(fieldErrors.otp)}
                  />
                  {fieldErrors.otp ? <span className="field-error">{fieldErrors.otp}</span> : null}
                </label>
              )}
              <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
                {busy ? t("common.loading") : otpSent ? t("owner.auth.verify") : t("owner.auth.sendOtp")}
              </button>
              {otpSent && (
                <button type="button" className="btn btn--ghost auth-card__resend" onClick={() => setOtpSent(false)}>
                  Use a different phone
                </button>
              )}
            </form>
          )}

          {demoVisible ? (
          <details className="auth-card__demo" open>
            <summary>Demo owner accounts · OTP <code>{DEMO.otp}</code></summary>
            <p className="auth-card__demo-otp">
              Phone <code>{DEMO.phone}</code> · OTP <code>{DEMO.otp}</code>
            </p>
            <ul className="auth-card__demo-list">
              {DEMO_OWNERS.map((account) => (
                <li key={account.phone}>
                  <div className="auth-card__demo-meta">
                    <span className="auth-card__demo-name">
                      {account.name}
                      {account.primary ? " · primary" : ""}
                    </span>
                    <span>{account.phone} · {account.kitchenLabel}</span>
                    {account.kitchenCode && <span className="auth-card__demo-code">{account.kitchenCode}</span>}
                  </div>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    disabled={busy}
                    onClick={() => handleDemoLogin(account)}
                  >
                    {busyPhone === account.phone ? "Signing in…" : "Sign in"}
                  </button>
                </li>
              ))}
            </ul>
            <p className="auth-card__demo-note">
              Requires healthy API (<code>identity:true</code>). Seed only after that.
            </p>
          </details>
          ) : null}

          <SuperAdminCredentials />

          <p className="auth-card__demo-note">
            Looking for menus? <a href={customerUrl("/")} target="_blank" rel="noopener noreferrer">Go to {CUSTOMER_HOST} →</a>
          </p>
          <Link to="/" className="auth-card__back">← Back to kitchen home</Link>
        </div>
      </div>
    </div>
  );
}
