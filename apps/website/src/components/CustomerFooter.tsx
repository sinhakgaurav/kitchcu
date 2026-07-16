import { Link } from "react-router-dom";
import { BrandNavMark } from "./BrandNavMark";
import { APP_NAME, CUSTOMER_HOST } from "../shared/brand";
import { kitchenUrl } from "../shared/urls";

export function CustomerFooter() {
  return (
    <footer className="footer footer--customer">
      <div className="container footer__inner">
        <div className="footer__brand">
          <BrandNavMark height={36} />
          <p>Discover trusted cloud kitchens with live-capture menus.</p>
          <span className="footer__host">{CUSTOMER_HOST}</span>
        </div>
        <div className="footer__links">
          <Link to="/">Home</Link>
          <Link to="/login">Customer sign in</Link>
          <a href={kitchenUrl("/login")} target="_blank" rel="noopener noreferrer">Kitchen owner login</a>
        </div>
        <p className="footer__copy">
          © {new Date().getFullYear()} {APP_NAME} · Customer
        </p>
      </div>
    </footer>
  );
}
