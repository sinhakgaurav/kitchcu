import { useEffect, useState } from "react";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import { updateKitchenBrandedPage } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";
import { CUSTOMER_HOST } from "../../shared/brand";
import { customerUrl } from "../../shared/urls";

export function BrandPage() {
  const { kitchen, reloadKitchens } = useKitchen();
  const [tagline, setTagline] = useState("");
  const [accent, setAccent] = useState("#0F766E");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!kitchen) return;
    setTagline(kitchen.branded_page?.tagline ?? "");
    setAccent(kitchen.branded_page?.accent_color ?? "#0F766E");
  }, [kitchen?.id, kitchen?.branded_page?.tagline, kitchen?.branded_page?.accent_color]);

  if (!kitchen) return null;

  const enabled = kitchen.branded_page?.enabled ?? false;
  const brandedLink = customerUrl(`/k/${kitchen.code}`);
  const discoverLink = customerUrl(`/kitchen/${kitchen.id}/menu`);

  const copyLink = async () => {
    await navigator.clipboard.writeText(brandedLink);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  const save = async (patch: {
    enabled?: boolean;
    tagline?: string | null;
    accent_color?: string | null;
  }) => {
    setBusy(true);
    setError("");
    setMsg("");
    try {
      await updateKitchenBrandedPage(kitchen.id, patch);
      await reloadKitchens();
      if (patch.enabled === true) setMsg("Branded page published — share the link with customers.");
      else if (patch.enabled === false) setMsg("Branded page unpublished.");
      else setMsg("Brand page saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update brand page");
    } finally {
      setBusy(false);
    }
  };

  return (
    <OwnerPageShell
      eyebrow="Growth · share"
      title="Brand page"
      description={`Your kitchen-first storefront on ${CUSTOMER_HOST} — menu, cart, checkout, bill. Powered by kitchCU at the foot.`}
      meta={
        <div className="od-board__pills">
          <span className={`od-pill ${enabled ? "od-pill--live" : "od-pill--sub"}`}>
            {enabled ? "Published" : "Not published"}
          </span>
          <span className="od-board__code">{kitchen.code}</span>
        </div>
      }
      actions={
        <>
          <button
            type="button"
            className="btn btn--primary"
            disabled={busy}
            onClick={() => save({ enabled: !enabled, tagline: tagline.trim() || null, accent_color: accent })}
          >
            {enabled ? "Unpublish" : "Publish page"}
          </button>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => window.open(brandedLink, "_blank", "noopener,noreferrer")}
          >
            Open preview
          </button>
        </>
      }
    >
      <OwnerPanel
        title="Share link"
        description="This is what you put on WhatsApp Status, Instagram bio, and flyer QR codes."
      >
        <div className="kc-copy-field owner-share__row">
          <code>{brandedLink}</code>
          <button type="button" className="btn btn--primary btn--sm" onClick={copyLink}>
            {copied ? "Copied!" : "Copy link"}
          </button>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => window.open(brandedLink, "_blank", "noopener,noreferrer")}
          >
            Open
          </button>
        </div>
        <p className="owner-muted" style={{ marginTop: "0.75rem" }}>
          Discover fallback (marketplace tab): <code>{discoverLink}</code>
        </p>
      </OwnerPanel>

      <OwnerPanel title="Page content" description="Shown above the menu on /k/{code}.">
        <label className="kc-field">
          <span className="kc-field__label">Tagline</span>
          <input
            className="kc-input"
            type="text"
            maxLength={160}
            value={tagline}
            onChange={(e) => setTagline(e.target.value)}
            placeholder="Home-style thalis · live-capture menu"
          />
        </label>
        <label className="kc-field" style={{ marginTop: "1rem" }}>
          <span className="kc-field__label">Accent colour</span>
          <div className="od-branded__tagline-row">
            <input
              type="color"
              value={accent}
              onChange={(e) => setAccent(e.target.value.toUpperCase())}
              aria-label="Accent colour"
            />
            <input
              className="kc-input"
              type="text"
              maxLength={7}
              value={accent}
              onChange={(e) => setAccent(e.target.value.toUpperCase())}
              placeholder="#0F766E"
              style={{ maxWidth: "8rem" }}
            />
          </div>
        </label>
        <div style={{ marginTop: "1rem" }}>
          <button
            type="button"
            className="btn btn--primary btn--sm"
            disabled={busy}
            onClick={() =>
              save({
                tagline: tagline.trim() || null,
                accent_color: accent.trim() || null,
              })
            }
          >
            Save content
          </button>
        </div>
      </OwnerPanel>

      <OwnerPanel title="What customers see">
        <ul className="od-share__tips">
          <li>Your kitchen name &amp; tagline — not the kitchCU discover home</li>
          <li>Your live-capture menu → cart → checkout → PDF bill</li>
          <li>
            Kitchen code <strong className="od-board__code">{kitchen.code}</strong> for repeat orders
          </li>
        </ul>
      </OwnerPanel>

      {error && <p className="auth-card__error">{error}</p>}
      {msg && <p className="auth-card__success">{msg}</p>}
    </OwnerPageShell>
  );
}
