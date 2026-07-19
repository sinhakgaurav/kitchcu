import { FormEvent, useState } from "react";
import type { CSSProperties, RefObject } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { images, sampleDishImages } from "../../data/content";
import { AuthLoginHighlights } from "../../components/AuthLoginHighlights";
import { BrandAuthArt, BrandLogo } from "../../components/BrandLogo";
import { DEMO, DEMO_CUSTOMERS, DEMO_OWNERS, type DemoCustomerAccount } from "../../shared/demo";
import { normalizePhone } from "../../shared/api";
import { fetchKitchenByCode } from "../../shared/publicApi";
import { CUSTOMER_HOST, KITCHEN_HOST } from "../../shared/brand";
import { CustomerSocialLogin } from "../../components/CustomerSocialLogin";
import { PolicyAgreement } from "../../components/PolicyAgreement";
import { isCustomerSignedIn, useCustomerAuth } from "../../shared/customerAuth";
import { saveKitchenToSession } from "../../shared/customerSession";
import { kitchenUrl } from "../../shared/urls";
import { useInView } from "../../hooks/useParallax";
import { AnimatedMesh } from "../../components/AnimatedMesh";
import {
  getCustomerToken,
  requestCustomerWhatsAppOtp,
  verifyCustomerWhatsAppOtp,
} from "../../shared/customerApi";

export function CustomerLoginPage() {
  const { session, applyAuthResult } = useCustomerAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const nextPath = searchParams.get("next") || "/";
  const [name, setName] = useState(session?.name ?? "");
  const [phone, setPhone] = useState(session?.phone ?? "");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyPhone, setBusyPhone] = useState<string | null>(null);
  const [policiesAgreed, setPoliciesAgreed] = useState(false);

  if (isCustomerSignedIn(session) && getCustomerToken()) {
    return <Navigate to={nextPath.startsWith("/") ? nextPath : "/"} replace />;
  }

  const requirePolicyAgreement = () => {
    if (policiesAgreed) return true;
    setError("Please agree to the Terms, Privacy, and Refund Policies to continue.");
    return false;
  };

  const afterAuth = async (kitchenCode: string) => {
    const safeNext = nextPath.startsWith("/") ? nextPath : "/";
    let kitchenMenu: string | null = null;
    if (kitchenCode.trim()) {
      try {
        const kitchen = await fetchKitchenByCode(kitchenCode);
        saveKitchenToSession(kitchen);
        kitchenMenu = `/kitchen/${kitchen.id}/menu`;
      } catch {
        // Optional kitchen pin — don't block return to checkout/dashboard.
      }
    }
    // Explicit return path (checkout, rate, dashboard) always wins over kitchen redirect.
    if (safeNext !== "/") {
      navigate(safeNext, { replace: true });
      return;
    }
    navigate(kitchenMenu ?? "/", { replace: true });
  };

  const handleRequestOtp = async (e: FormEvent) => {
    e.preventDefault();
    if (!requirePolicyAgreement()) return;
    setError("");
    setBusy(true);
    try {
      await requestCustomerWhatsAppOtp(normalizePhone(phone));
      setOtpSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send OTP");
    } finally {
      setBusy(false);
    }
  };

  const handleVerify = async (e: FormEvent) => {
    e.preventDefault();
    if (!requirePolicyAgreement()) return;
    setError("");
    setBusy(true);
    try {
      const result = await verifyCustomerWhatsAppOtp(normalizePhone(phone), otp.trim());
      applyAuthResult({
        ...result,
        customer: {
          ...result.customer,
          name: name.trim() || result.customer.name,
        },
      });
      await afterAuth(code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not verify OTP");
    } finally {
      setBusy(false);
    }
  };

  const fillDemo = (account: DemoCustomerAccount) => {
    setName(account.name);
    setPhone(account.phone);
    setCode(DEMO.kitchenCode);
    setOtp(DEMO.otp);
    setOtpSent(true);
  };

  const handleDemoWhatsApp = async (account: DemoCustomerAccount) => {
    setError("");
    setBusy(true);
    setBusyPhone(account.phone);
    fillDemo(account);
    try {
      const e164 = normalizePhone(account.phone);
      await requestCustomerWhatsAppOtp(e164);
      const result = await verifyCustomerWhatsAppOtp(e164, DEMO.otp);
      applyAuthResult(result);
      await afterAuth(DEMO.kitchenCode);
    } catch (err) {
      setError(
        err instanceof Error
          ? `${err.message} — ensure gateway is up`
          : "Demo customer login failed",
      );
    } finally {
      setBusy(false);
      setBusyPhone(null);
    }
  };

  return (
    <div className="auth-page auth-page--customer">
      <AnimatedMesh variant="customer" />
      <div className="auth-page__visual">
        <div className="auth-page__overlay" />
        <div className="auth-page__brand-stack">
          <BrandLogo variant="wordmark" className="brand-logo--lg" />
          <h1>Customer sign in</h1>
          <p>Save your profile and favourite kitchens on {CUSTOMER_HOST}</p>
          <AuthLoginHighlights surface="customer" />
          <BrandAuthArt surface="customer" />
        </div>
      </div>

      <div className="auth-page__form-wrap">
        <div className="auth-page__mobile-brand">
          <BrandLogo variant="wordmark" className="brand-logo--lg" />
          <p>Customer sign in · {CUSTOMER_HOST}</p>
        </div>
        <div className="auth-card glass">
          <div className="auth-card__demo">
            <strong>Demo customer accounts</strong>
            <p className="auth-card__demo-otp">WhatsApp OTP (dev): <code>{DEMO.otp}</code></p>
            <ul className="auth-card__demo-list">
              {DEMO_CUSTOMERS.map((account) => (
                <li key={account.phone}>
                  <div className="auth-card__demo-meta">
                    <span className="auth-card__demo-name">{account.name}</span>
                    <span>{account.phone} · {account.note}</span>
                  </div>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    disabled={busy}
                    onClick={() => handleDemoWhatsApp(account)}
                  >
                    {busyPhone === account.phone ? "Signing in…" : "WhatsApp login"}
                  </button>
                </li>
              ))}
            </ul>
            <p className="auth-card__demo-note">
              Opens demo kitchen <code>{DEMO.kitchenCode}</code>. Owners:{" "}
              {DEMO_OWNERS.map((o) => o.phone).join(", ")}
            </p>
          </div>

          <form onSubmit={otpSent ? handleVerify : handleRequestOtp}>
            <h2>Welcome back</h2>
            <p className="auth-card__hint">
              WhatsApp OTP on <strong>{CUSTOMER_HOST}</strong> — separate from kitchen owners.
              Dev OTP: <strong>{DEMO.otp}</strong>.
            </p>
            {error && <div className="auth-card__error">{error}</div>}
            <label>
              Your name
              <input value={name} onChange={(e) => setName(e.target.value)} required placeholder={DEMO.customerName} />
            </label>
            <label>
              Phone
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                placeholder="9123456789"
                disabled={otpSent}
              />
            </label>
            <label>
              Kitchen code (optional)
              <input
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder={DEMO.kitchenCode}
              />
            </label>
            {otpSent && (
              <label>
                OTP code
                <input
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                  required
                  placeholder={DEMO.otp}
                  maxLength={6}
                />
              </label>
            )}
            <PolicyAgreement
              audience="customer"
              checked={policiesAgreed}
              onChange={setPoliciesAgreed}
            />
            <button
              type="submit"
              className="btn btn--primary btn--lg"
              disabled={busy || !policiesAgreed}
            >
              {busy ? "Please wait…" : otpSent ? "Verify & sign in" : "Send WhatsApp OTP"}
            </button>
            {otpSent ? (
              <button type="button" className="btn btn--ghost auth-card__resend" onClick={() => setOtpSent(false)}>
                Change phone number
              </button>
            ) : (
              <button
                type="button"
                className="btn btn--ghost auth-card__resend"
                onClick={() => fillDemo(DEMO_CUSTOMERS[0])}
              >
                Fill demo profile
              </button>
            )}
          </form>

          <CustomerSocialLogin
            policiesAgreed={policiesAgreed}
            nextPath={nextPath}
            onAuth={(result) => {
              applyAuthResult(result);
            }}
            onSuccess={() => afterAuth(code)}
            onError={setError}
          />
          <p className="auth-card__demo-note">
            Kitchen owner? <a href={kitchenUrl("/login")} target="_blank" rel="noopener noreferrer">Sign in on {KITCHEN_HOST} →</a>
          </p>
          <Link to="/" className="auth-card__back">← Back to customer home</Link>
        </div>
      </div>
    </div>
  );
}

export function CustomerHomePage() {
  const navigate = useNavigate();
  const { session, updateSession } = useCustomerAuth();
  const { ref, visible } = useInView(0.08);
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const openKitchen = async (kitchenCode: string) => {
    setError("");
    setBusy(true);
    try {
      const kitchen = await fetchKitchenByCode(kitchenCode.trim().toUpperCase());
      const next = saveKitchenToSession(kitchen);
      updateSession(next);
      navigate(`/kitchen/${kitchen.id}/menu`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kitchen not found. Check the code or run seed script.");
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await openKitchen(code);
  };

  return (
    <div className="container customer-page__body" id="discover" ref={ref as RefObject<HTMLDivElement>}>
      <form className={`glass customer-search reveal ${visible ? "reveal--visible" : ""}`} onSubmit={handleSubmit}>
        <h2>Find a kitchen</h2>
        <p>
          {session?.name?.trim()
            ? `Welcome back, ${session.name}. Enter a kitchen code or pick a saved kitchen below.`
            : "Enter the kitchen code shared by your cloud kitchen owner."}
        </p>
        <label>
          Kitchen code
          <input
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder={DEMO.kitchenCode}
            required
          />
        </label>
        {error && <div className="auth-card__error">{error}</div>}
        <div className="customer-search__actions">
          <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
            {busy ? "Searching..." : "View menu"}
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--lg"
            disabled={busy}
            onClick={() => openKitchen(DEMO.kitchenCode)}
          >
            Open demo ({DEMO.kitchenCode})
          </button>
        </div>
      </form>

      {session && session.savedKitchens.length > 0 && (
        <section className="customer-saved">
          <h2>Your kitchens</h2>
          <div className="customer-saved__grid">
            {session.savedKitchens.map((k) => (
              <button
                key={k.id}
                type="button"
                className="glass customer-saved__card"
                onClick={() => navigate(`/kitchen/${k.id}/menu`)}
              >
                <strong>{k.name}</strong>
                <span>{k.code}{k.city ? ` · ${k.city}` : ""}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      <div className={`customer-benefits reveal-stagger ${visible ? "reveal--visible" : ""}`} id="how">
        <article className="glass customer-benefit-card" style={{ "--i": 0 } as CSSProperties}>
          <img src={sampleDishImages.biryani} alt="" loading="lazy" />
          <h3>Live-capture photos</h3>
          <p>See what your food actually looks like — not stock images.</p>
        </article>
        <article className="glass customer-benefit-card" style={{ "--i": 1 } as CSSProperties}>
          <img src={images.customers.src} alt="" loading="lazy" />
          <h3>Home-taste quality</h3>
          <p>Cloud kitchens focused on authentic home cooking, not aggregator races.</p>
        </article>
        <article className="glass customer-benefit-card" style={{ "--i": 2 } as CSSProperties}>
          <img src={sampleDishImages.thali} alt="" loading="lazy" />
          <h3>Order tracking</h3>
          <p>Follow your order from kitchen to door with live tracking links.</p>
        </article>
      </div>
    </div>
  );
}