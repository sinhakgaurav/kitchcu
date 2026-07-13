import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { AnimatedMesh } from "../components/AnimatedMesh";
import { images } from "../data/content";
import { DEMO } from "../shared/demo";
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

  const handleDemoLogin = async () => {
    setError("");
    setBusy(true);
    setMode("login");
    setPhone(DEMO.phone);
    setOtp(DEMO.otp);
    try {
      await requestOtp(DEMO.phone);
      setOtpSent(true);
      const { access_token } = await verifyOtp(DEMO.phone, DEMO.otp);
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
    }
  };

  return (
    <div className="auth-page auth-page--kitchen">
      <AnimatedMesh variant="kitchen" />
      <div className="auth-page__visual">
        <img src={images.login.src} alt={images.login.alt} className="auth-page__img" />
        <div className="auth-page__overlay" />
        <div className="auth-page__visual-text">
          <Link to="/" className="nav__logo">kitchCU</Link>
          <h1>Kitchen owner portal</h1>
          <p>Sign in on {KITCHEN_HOST} to manage orders, menu, and customer links.</p>
        </div>
      </div>

      <div className="auth-page__form-wrap">
        <div className="auth-card glass">
          <div className="auth-card__demo">
            <strong>Demo owner account</strong>
            <dl>
              <div><dt>Phone</dt><dd>{DEMO.phone}</dd></div>
              <div><dt>OTP</dt><dd>{DEMO.otp}</dd></div>
              <div><dt>Kitchen</dt><dd>{DEMO.kitchenCode}</dd></div>
            </dl>
            <button
              type="button"
              className="btn btn--primary btn--lg auth-card__demo-btn"
              disabled={busy}
              onClick={handleDemoLogin}
            >
              {busy ? "Signing in..." : "Sign in as demo owner"}
            </button>
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
