import { BrandAuthArt, BrandLogo } from "./BrandLogo";
import { APP_NAME, APP_POSITIONING_SHORT } from "../shared/brand";

type Props = {
  surface?: "portal" | "customer" | "kitchen" | "admin";
};

/**
 * Body-only brand block — image wordmark + creative art.
 * Tagline stays in top nav only (BrandNavMark); caption uses positioning claim.
 */
export function BrandHeroArt({ surface = "portal" }: Props) {
  return (
    <div className="hero__art brand-hero-art brand-body-art" aria-hidden={false}>
      <BrandLogo variant="wordmark" height={42} className="brand-body-art__wordmark" />
      <BrandAuthArt surface={surface} />
      <p className="brand-body-art__caption">
        <strong>{APP_NAME}</strong> · {APP_POSITIONING_SHORT}
      </p>
    </div>
  );
}
