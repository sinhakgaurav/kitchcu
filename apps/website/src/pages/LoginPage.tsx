import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { AnimatedMesh } from "../components/AnimatedMesh";
import { BrandAuthArt, BrandLogo } from "../components/BrandLogo";
import { DEMO, DEMO_OWNERS, type DemoOwnerAccount } from "../shared/demo";
import { registerOwner, requestOtp, verifyOtp } from "../shared/api";
import { KITCHEN_HOST, CUSTOMER_HOST } from "../shared/brand";
import { useKitchenAuth } from "../shared/kitchenAuth";
import { customerUrl } from "../shared/urls";

type Mode = "login" | "register";

export function LoginPage() {
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
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyPhone, setBusyPhone] = useState<string | null>(null);

  if (token) return <Navigate to={nextPath.startsWith("/") ? nextPath : "/dashboard"} replace />;

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await registerOwner({ phone, name, email: email || undefined });
      await requestOtp(phone);
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
    setBusy(true);
    try {
      await requestOtp(phone);
      setOtpSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send OTP");
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { access_token } = await verifyOtp(phone, otp);
      await login(access_token);
      navigate(nextPath.startsWith("/") ? nextPath : "/dashboard");
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
    setPhone(account.phone);
    setOtp(DEMO.otp);
    try {
      await requestOtp(account.phone);
      setOtpSent(true);
      const { access_token } = await verifyOtp(account.phone, DEMO.otp);
      await login(access_token);
      navigate(nextPath.startsWith("/") ? nextPath : "/dashboard");
    } catch (err) {
      setError(
        err instanceof Error
          ? `${err.message} — run: python scripts/seed-dev-data.py`
          : "Demo login failed — seed demo data first",
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
          <BrandAuthArt surface="kitchen" />
          <h1>Kitchen owner portal</h1>
          <p>Sign in on {KITCHEN_HOST} to manage orders, menu, and customer links.</p>
        </div>
      </div>

      <div className="auth-page__form-wrap">
        <div className="auth-card glass">
          <div className="auth-card__demo">
            <strong>Demo owner accounts</strong>
            <p className="auth-card__demo-otp">Dev OTP for all: <code>{DEMO.otp}</code></p>
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
              Requires backend + <code>python scripts/seed-dev-data.py</code>
            </p>
          </div>

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
              Your session expired. Sign in again to view reports and dashboard data.
            </div>
          )}

          {error && <div className="auth-card__error">{error}</div>}

          {mode === "register" ? (
            <form onSubmit={handleRegister}>
              <h2>Create owner account</h2>
              <p className="auth-card__hint">Owner accounts are only for {KITCHEN_HOST} — not customer sign-in.</p>
              <label>
                Full name
                <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Raj Sharma" />
              </label>
              <label>
                Phone
                <input value={phone} onChange={(e) => setPhone(e.target.value)} required placeholder={DEMO.phone} />
              </label>
              <label>
                Email (optional)
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={DEMO.email} />
              </label>
              <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
                {busy ? "Creating..." : "Register & Send OTP"}
              </button>
            </form>
          ) : (
            <form onSubmit={otpSent ? handleVerify : handleRequestOtp}>
              <h2>Owner sign in (OTP)</h2>
              <p className="auth-card__hint">
                Dev OTP: <strong>{DEMO.otp}</strong>. Backend on port 18000.
              </p>
              <label>
                Phone
                <input value={phone} onChange={(e) => setPhone(e.target.value)} required placeholder={DEMO.phone} />
              </label>
              {otpSent && (
                <label>
                  OTP code
                  <input value={otp} onChange={(e) => setOtp(e.target.value)} required placeholder={DEMO.otp} maxLength={6} />
                </label>
              )}
              <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
                {busy ? "Please wait..." : otpSent ? "Sign In" : "Send OTP"}
              </button>
              {otpSent && (
                <button type="button" className="btn btn--ghost auth-card__resend" onClick={() => setOtpSent(false)}>
                  Change phone number
                </button>
              )}
            </form>
          )}

          <p className="auth-card__demo-note">
            Looking for menus? <a href={customerUrl("/")}>Go to {CUSTOMER_HOST} →</a>
          </p>
          <Link to="/" className="auth-card__back">← Back to kitchen home</Link>
        </div>
      </div>
    </div>
  );
}
