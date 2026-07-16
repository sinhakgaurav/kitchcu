import { BrandNavMark } from "./BrandNavMark";
import { APP_NAME, SUPPORT_EMAIL } from "../shared/brand";
import { customerUrl, kitchenUrl } from "../shared/urls";

export function PortalFooter() {
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <div className="footer__brand">
          <BrandNavMark height={40} />
          <p>
            Cloud Kitchen Analytics &amp; Control — India's first (and the world's third)
            Growth OS for home food businesses, tiffin services, and delivery-only kitchens.
            Zero food commission.
          </p>
        </div>
        <div className="footer__links">
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href="#support">Support</a>
          <a href="#contact">Contact</a>
          <a href="/openapi">API / OpenAPI</a>
          <a href={customerUrl("/")} target="_blank" rel="noopener noreferrer">Customer app</a>
          <a href={kitchenUrl("/")} target="_blank" rel="noopener noreferrer">Kitchen app</a>
        </div>
        <p className="footer__copy">
          © {new Date().getFullYear()} {APP_NAME} · {SUPPORT_EMAIL} · Pune, India
        </p>
      </div>
    </footer>
  );
}
