import { customerUrl, kitchenUrl } from "../shared/urls";

export function PortalFooter() {
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <div className="footer__brand">
          <span className="nav__logo">kitchCU</span>
          <p>
            Cloud Kitchen Analytics &amp; Control — built for home food businesses,
            tiffin services, and delivery-only kitchens. Zero food commission.
          </p>
        </div>
        <div className="footer__links">
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <a href="#support">Support</a>
          <a href="#contact">Contact</a>
          <a href={customerUrl("/")}>Customer app</a>
          <a href={kitchenUrl("/")}>Kitchen app</a>
        </div>
        <p className="footer__copy">
          © {new Date().getFullYear()} kitchCU · hello@kitchCU.in · Pune, India
        </p>
      </div>
    </footer>
  );
}
