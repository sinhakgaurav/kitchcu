import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { OwnerPageShell, OwnerPanel } from "../../components/owner/OwnerPageShell";
import { updateKitchenBrandedPage, uploadKitchenBrandedMedia } from "../../lib/api";
import { useKitchen } from "../../lib/kitchen";
import { CUSTOMER_HOST } from "../../shared/brand";
import { customerUrl } from "../../shared/urls";

export function BrandPage() {
  const { t } = useTranslation();
  const { kitchen, reloadKitchens } = useKitchen();
  const [tagline, setTagline] = useState("");
  const [accent, setAccent] = useState("#0F766E");
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [backgroundUrl, setBackgroundUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState<"logo" | "background" | null>(null);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const logoInputRef = useRef<HTMLInputElement>(null);
  const bgInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!kitchen) return;
    setTagline(kitchen.branded_page?.tagline ?? "");
    setAccent(kitchen.branded_page?.accent_color ?? "#0F766E");
    setLogoUrl(kitchen.branded_page?.logo_url ?? null);
    setBackgroundUrl(kitchen.branded_page?.background_url ?? null);
  }, [
    kitchen?.id,
    kitchen?.branded_page?.tagline,
    kitchen?.branded_page?.accent_color,
    kitchen?.branded_page?.logo_url,
    kitchen?.branded_page?.background_url,
  ]);

  if (!kitchen) return null;

  const enabled = kitchen.branded_page?.enabled ?? false;
  const brandedLink = customerUrl(`/k/${kitchen.code}`);
  const discoverLink = customerUrl(`/kitchen/${kitchen.id}/menu`);
  const templateHint =
    `Hi {{customer_name}} — order from {{kitchen_name}} (${kitchen.code}): {{storefront_url}}. {{tagline}}`;

  const copyLink = async () => {
    await navigator.clipboard.writeText(brandedLink);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  const save = async (patch: {
    enabled?: boolean;
    tagline?: string | null;
    accent_color?: string | null;
    logo_url?: string | null;
    background_url?: string | null;
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

  const onUpload = async (slot: "logo" | "background", file: File | null) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Please choose a JPEG, PNG, or WebP image.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("Image must be 10MB or smaller.");
      return;
    }
    setUploading(slot);
    setError("");
    setMsg("");
    try {
      const next = await uploadKitchenBrandedMedia(
        kitchen.id,
        file,
        slot,
        file.name || `${slot}.jpg`,
      );
      setLogoUrl(next.branded_page?.logo_url ?? null);
      setBackgroundUrl(next.branded_page?.background_url ?? null);
      await reloadKitchens();
      setMsg(slot === "logo" ? "Logo uploaded." : "Background image uploaded.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(null);
    }
  };

  const clearMedia = async (slot: "logo" | "background") => {
    const patch = slot === "logo" ? { logo_url: "" } : { background_url: "" };
    await save(patch);
    if (slot === "logo") setLogoUrl(null);
    else setBackgroundUrl(null);
  };

  return (
    <OwnerPageShell
      eyebrow={t("owner.nav.growth")}
      title={t("owner.pages.brand")}
      description={`Your kitchen-first storefront on ${CUSTOMER_HOST} — logo, hero, menu, cart, checkout. Powered by kitchCU at the foot.`}
      meta={
        <div className="od-board__pills">
          <span className={`od-pill ${enabled ? "od-pill--live" : "od-pill--sub"}`}>
            {enabled ? t("owner.home.published") : t("owner.home.notPublished")}
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
            onClick={() =>
              save({
                enabled: !enabled,
                tagline: tagline.trim() || null,
                accent_color: accent,
                logo_url: logoUrl,
                background_url: backgroundUrl,
              })
            }
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
      {error && <p className="auth-card__error">{error}</p>}
      {msg && <p className="auth-card__success">{msg}</p>}

      <OwnerPanel
        title="Brand visuals"
        description="Upload your kitchen logo and a hero background. Shown on the customer storefront at /k/{code}. JPEG, PNG, or WebP · max 10MB."
      >
        <div className="od-brand-media">
          <div className="od-brand-media__slot">
            <span className="kc-field__label">Logo</span>
            <button
              type="button"
              className="od-brand-media__drop"
              disabled={!!uploading || busy}
              onClick={() => logoInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                void onUpload("logo", e.dataTransfer.files?.[0] ?? null);
              }}
            >
              {logoUrl ? (
                <img src={logoUrl} alt="" className="od-brand-media__preview od-brand-media__preview--logo" />
              ) : (
                <span className="od-brand-media__empty-copy">
                  {uploading === "logo" ? "Uploading…" : "Drop logo here or click to upload"}
                </span>
              )}
            </button>
            <input
              ref={logoInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="visually-hidden"
              disabled={!!uploading || busy}
              onChange={(e) => {
                void onUpload("logo", e.target.files?.[0] ?? null);
                e.target.value = "";
              }}
            />
            <div className="od-brand-media__actions">
              <button
                type="button"
                className="btn btn--primary btn--sm"
                disabled={!!uploading || busy}
                onClick={() => logoInputRef.current?.click()}
              >
                {uploading === "logo" ? "Uploading…" : "Upload logo"}
              </button>
              {logoUrl && (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={busy}
                  onClick={() => void clearMedia("logo")}
                >
                  Remove
                </button>
              )}
            </div>
          </div>

          <div className="od-brand-media__slot">
            <span className="kc-field__label">Background / hero</span>
            <button
              type="button"
              className="od-brand-media__drop od-brand-media__drop--bg"
              disabled={!!uploading || busy}
              onClick={() => bgInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                void onUpload("background", e.dataTransfer.files?.[0] ?? null);
              }}
            >
              {backgroundUrl ? (
                <img
                  src={backgroundUrl}
                  alt=""
                  className="od-brand-media__preview od-brand-media__preview--bg"
                />
              ) : (
                <span className="od-brand-media__empty-copy">
                  {uploading === "background"
                    ? "Uploading…"
                    : "Drop background here or click to upload"}
                </span>
              )}
            </button>
            <input
              ref={bgInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="visually-hidden"
              disabled={!!uploading || busy}
              onChange={(e) => {
                void onUpload("background", e.target.files?.[0] ?? null);
                e.target.value = "";
              }}
            />
            <div className="od-brand-media__actions">
              <button
                type="button"
                className="btn btn--primary btn--sm"
                disabled={!!uploading || busy}
                onClick={() => bgInputRef.current?.click()}
              >
                {uploading === "background" ? "Uploading…" : "Upload background"}
              </button>
              {backgroundUrl && (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={busy}
                  onClick={() => void clearMedia("background")}
                >
                  Remove
                </button>
              )}
            </div>
          </div>
        </div>
      </OwnerPanel>

      <OwnerPanel
        title="Share link"
        description="WhatsApp Status, Instagram bio, flyer QR — also injected as {{storefront_url}} in message templates."
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
          Discover fallback: <code>{discoverLink}</code>
        </p>
      </OwnerPanel>

      <OwnerPanel title="Page content" description="Tagline and accent colour on the storefront header.">
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

      <OwnerPanel
        title="Message templates"
        description="WhatsApp / email blasts can include {{storefront_url}} and {{tagline}} so customers land on this brand page."
      >
        <p className="owner-muted">Suggested body:</p>
        <code className="od-brand-template-hint">{templateHint}</code>
        <div style={{ marginTop: "0.75rem" }}>
          <Link to="/dashboard/templates" className="btn btn--ghost btn--sm">
            Open message templates →
          </Link>
        </div>
      </OwnerPanel>

      <OwnerPanel title="What customers see">
        <ul className="od-share__tips">
          <li>Your logo, hero background, name &amp; tagline — not the kitchCU discover home</li>
          <li>Your live-capture menu → cart → checkout → PDF bill</li>
          <li>
            Kitchen code <strong className="od-board__code">{kitchen.code}</strong> for repeat orders
          </li>
        </ul>
      </OwnerPanel>
    </OwnerPageShell>
  );
}
