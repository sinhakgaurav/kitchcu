import { APP_NAME, BRAND_ASSETS } from "../shared/brand";

type BrandLogoVariant = "wordmark" | "icon" | "badge" | "mark" | "lockup" | "mascot";

const SRC: Record<BrandLogoVariant, string> = {
  wordmark: BRAND_ASSETS.wordmark,
  icon: BRAND_ASSETS.appicon,
  badge: BRAND_ASSETS.badge,
  mark: BRAND_ASSETS.markCircle,
  lockup: BRAND_ASSETS.lockupDark,
  mascot: BRAND_ASSETS.mascot,
};

type BrandLogoProps = {
  variant?: BrandLogoVariant;
  className?: string;
  alt?: string;
  /** Height hint for CSS; width auto */
  height?: number;
};

/** Image wordmark / icons — use in page body heroes, auth visuals, marketing sections. */
export function BrandLogo({
  variant = "wordmark",
  className = "",
  alt = APP_NAME,
  height,
}: BrandLogoProps) {
  return (
    <img
      src={SRC[variant]}
      alt={alt}
      className={`brand-logo brand-logo--${variant} ${className}`.trim()}
      style={height ? { height, width: "auto" } : undefined}
      decoding="async"
    />
  );
}

type BrandTextLogoProps = {
  className?: string;
  /** Optional muted trailing label (host / product line) */
  subtitle?: string;
  size?: "sm" | "md" | "lg";
};

/**
 * Simple typographic logo for headers, sidebars, and chrome.
 * Keeps nav clean; put illustration assets in body sections only.
 */
export function BrandTextLogo({ className = "", subtitle, size = "md" }: BrandTextLogoProps) {
  return (
    <span className={`brand-text-logo brand-text-logo--${size} ${className}`.trim()}>
      <span className="brand-text-logo__mark" aria-label={APP_NAME}>
        <span className="brand-text-logo__kitch">kitch</span>
        <span className="brand-text-logo__cu">CU</span>
      </span>
      {subtitle ? <span className="brand-text-logo__sub">{subtitle}</span> : null}
    </span>
  );
}

type BrandAuthArtProps = {
  surface?: "kitchen" | "customer" | "admin" | "portal";
  className?: string;
};

/**
 * Auth hero mark — the plain kitchCU app icon (pot mascot, no wordmark)
 * at a large size. One consistent icon across kitchen/customer/admin/portal
 * auth screens keeps the brand mark from repeating alongside the wordmark
 * already shown above it in the same brand stack.
 */
export function BrandAuthArt({ surface = "kitchen", className = "" }: BrandAuthArtProps) {
  return (
    <img
      src={BRAND_ASSETS.appicon}
      alt=""
      width={340}
      height={340}
      className={`brand-auth-art brand-auth-art--${surface} ${className}`.trim()}
      decoding="async"
      fetchPriority="high"
    />
  );
}
