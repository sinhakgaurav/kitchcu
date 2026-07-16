import { BrandAuthArt } from "./BrandLogo";
import { APP_NAME, APP_POSITIONING_SHORT } from "../shared/brand";

type Props = {
  surface?: "portal" | "customer" | "kitchen" | "admin";
};

/**
 * Body brand art only — no wordmark (logo + tagline live in top BrandNavMark).
 */
export function BrandHeroArt({ surface = "portal" }: Props) {
  return (
    <div className="hero__art brand-hero-art brand-body-art" aria-hidden={false}>
      <BrandAuthArt surface={surface} />
      <p className="brand-body-art__caption">
        <strong>{APP_NAME}</strong> · {APP_POSITIONING_SHORT}
      </p>
    </div>
  );
}
