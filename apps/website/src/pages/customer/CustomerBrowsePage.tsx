import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BrandTextLogo } from "../../components/BrandLogo";
import { images, sampleDishImages } from "../../data/content";
import { DEMO } from "../../data/demo";
import { fetchKitchenByCode } from "../../lib/api";

export function CustomerBrowsePage() {
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const kitchen = await fetchKitchenByCode(code);
      navigate(`/kitchen/${kitchen.id}/menu`);
    } catch {
      setError("Kitchen not found. Check the code from your kitchen (e.g. CKPNQ001).");
    } finally {
      setBusy(false);
    }
  };

  const openDemoKitchen = async () => {
    setCode(DEMO.kitchenCode);
    setError("");
    setBusy(true);
    try {
      const kitchen = await fetchKitchenByCode(DEMO.kitchenCode);
      navigate(`/kitchen/${kitchen.id}/menu`);
    } catch {
      setError(`Demo kitchen not found. Run: python scripts/seed-dev-data.py`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="customer-page">
      <header className="customer-page__nav container">
        <Link to="/" className="nav__brand nav__brand--row">
          <BrandTextLogo subtitle="For Customers" />
        </Link>
        <Link to="/login" className="btn btn--ghost btn--sm">Owner Login</Link>
      </header>

      <div className="customer-page__hero">
        <img src={images.heroSecondary.src} alt="" className="customer-page__hero-img" />
        <div className="customer-page__hero-overlay" />
        <div className="container customer-page__hero-content">
          <h1>Discover trusted home kitchens</h1>
          <p>Browse live-capture menus, see real dishes, and order from cloud kitchens near you.</p>
        </div>
      </div>

      <div className="container customer-page__body">
        <form className="glass customer-search" onSubmit={handleSubmit}>
          <h2>Find a kitchen</h2>
          <p>Enter the kitchen code shared by your cloud kitchen owner.</p>
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
              onClick={openDemoKitchen}
            >
              Open demo kitchen ({DEMO.kitchenCode})
            </button>
          </div>
          <p className="customer-search__demo-hint">
            Demo menu includes {DEMO.kitchenName} with live-capture dish photos.
          </p>
        </form>

        <div className="customer-benefits">
          <article className="glass customer-benefit-card">
            <img src={sampleDishImages.biryani} alt="" loading="lazy" />
            <h3>Live-capture photos</h3>
            <p>See what your food actually looks like — not stock images.</p>
          </article>
          <article className="glass customer-benefit-card">
            <img src={images.owners.src} alt="" loading="lazy" />
            <h3>Home-taste quality</h3>
            <p>Cloud kitchens focused on authentic home cooking, not aggregator races.</p>
          </article>
          <article className="glass customer-benefit-card">
            <img src={sampleDishImages.thali} alt="" loading="lazy" />
            <h3>Order tracking</h3>
            <p>Follow your order from kitchen to delivery (coming to customer app).</p>
          </article>
        </div>      </div>
    </div>
  );
}
