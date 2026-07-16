import { Link } from "react-router-dom";
import { BrandLogo } from "./BrandLogo";

type Props = {
  /** Link target for the brand mark */
  to?: string;
  /** External href (portal uses anchors) */
  href?: string;
  /** Host / product line under the wordmark */
  subtitle?: string;
  /** Wordmark height in px */
  height?: number;
  className?: string;
  /** Prefer dark lockup on dark chrome backgrounds */
  dark?: boolean;
};

/**
 * Chrome brand mark — image wordmark from logos/ (public/brand).
 * Use in navbars, sidebars, and footers only.
 */
export function BrandNavMark({
  to,
  href,
  subtitle,
  height = 48,
  className = "",
  dark = false,
}: Props) {
  const mark = (
    <span className={`brand-nav-mark ${className}`.trim()}>
      <BrandLogo
        variant={dark ? "lockup" : "wordmark"}
        height={height}
        className="brand-nav-mark__logo"
      />
      {subtitle ? <span className="brand-nav-mark__sub">{subtitle}</span> : null}
    </span>
  );

  if (to) {
    return (
      <Link to={to} className="nav__brand nav__brand--row">
        {mark}
      </Link>
    );
  }
  if (href) {
    return (
      <a href={href} className="nav__brand nav__brand--row">
        {mark}
      </a>
    );
  }
  return mark;
}
