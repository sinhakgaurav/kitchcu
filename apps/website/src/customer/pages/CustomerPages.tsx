import { FormEvent, useState } from "react";
import type { CSSProperties, RefObject } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { images, sampleDishImages } from "../../data/content";
import { DEMO } from "../../shared/demo";
import { fetchKitchenByCode } from "../../shared/api";
import { CUSTOMER_HOST, KITCHEN_HOST } from "../../shared/brand";
import { CustomerSocialLogin } from "../../components/CustomerSocialLogin";
import { isCustomerSignedIn, useCustomerAuth } from "../../shared/customerAuth";
import { saveKitchenToSession } from "../../shared/customerSession";
import { kitchenUrl } from "../../shared/urls";
import { useInView } from "../../hooks/useParallax";
import { AnimatedMesh } from "../../components/AnimatedMesh";

export function CustomerLoginPage() {
  const { session, login, applyAuthResult } = useCustomerAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const nextPath = searchParams.get("next") || "/";
  const [name, setName] = useState(session?.name ?? "");
  const [phone, setPhone] = useState(session?.phone ?? "");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (isCustomerSignedIn(session)) {
    return <Navigate to="/" replace />;
  }

  const afterAuth = async (kitchenCode: string) => {
    if (kitchenCode.trim()) {
      const kitchen = await fetchKitchenByCode(kitchenCode);
      saveKitchenToSession(kitchen);
      navigate(`/kitchen/${kitchen.id}/menu`);
      return;
    }
    navigate(nextPath);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      login(name, phone);
      if (code.trim()) {
        const kitchen = await fetchKitchenByCode(code);
        saveKitchenToSession(kitchen);
        navigate(`/kitchen/${kitchen.id}/menu`);
        return;
      }
      navigate(nextPath);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
    } finally {
      setBusy(false);
    }
  };

  const fillDemo = () => {
    setName(DEMO.customerName);
    setPhone(DEMO.customerPhone);
    setCode(DEMO.kitchenCode);
  };

  return (
    <div className="auth-page auth-page--customer">
      <AnimatedMesh variant="customer" />
      <div className="auth-page__visual">
        <img src={images.customers.src} alt="" className="auth-page__img" />
        <div className="auth-page__overlay" />
        <div className="auth-page__visual-text">
          <Link to="/" className="nav__logo">kitchCU</Link>
          <h1>Customer sign in</h1>
          <p>Save your profile and favourite kitchens on {CUSTOMER_HOST}</p>
        </div>
      </div>

      <div className="auth-page__form-wrap">
        <div className="auth-card glass">
          <form onSubmit={handleSubmit}>
            <h2>Welcome back</h2>
            <p className="auth-card__hint">
              Your session stays on <strong>{CUSTOMER_HOST}</strong> — separate from kitchen owners.
            </p>
            {error && <div className="auth-card__error">{error}</div>}
            <label>
              Your name
              <input value={name} onChange={(e) => setName(e.target.value)} required placeholder={DEMO.customerName} />
            </label>
            <label>
              Phone
              <input value={phone} onChange={(e) => setPhone(e.target.value)} required placeholder="9123456789" />
            </label>
            <label>
              Kitchen code (optional)
              <input
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder={DEMO.kitchenCode}
              />
            </label>
            <button type="submit" className="btn btn--primary btn--lg" disabled={busy}>
              {busy ? "Signing in..." : "Continue"}
            </button>
            <button type="button" className="btn btn--ghost auth-card__resend" onClick={fillDemo}>
              Fill demo customer
            </button>
          </form>

          <CustomerSocialLogin
            onAuth={(result) => {
              applyAuthResult(result);
            }}
            onSuccess={() => afterAuth(code)}
            onError={setError}
          />
          <p className="auth-card__demo-note">
            Kitchen owner? <a href={kitchenUrl("/login")}>Sign in on {KITCHEN_HOST} →</a>
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
      const kitchen = await fetchKitchenByCode(kitchenCode);
      const next = saveKitchenToSession(kitchen);
      updateSession(next);
      navigate(`/kitchen/${kitchen.id}/menu`);
    } catch {
      setError("Kitchen not found. Check the code or run seed script.");
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
          {session
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
          <p>Follow your order from kitchen to delivery (coming to customer app).</p>
        </article>
      </div>
    </div>
  );
}