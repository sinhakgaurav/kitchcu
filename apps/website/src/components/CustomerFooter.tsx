import { Link } from "react-router-dom";
import { CUSTOMER_HOST } from "../shared/brand";
import { kitchenUrl } from "../shared/urls";

export function CustomerFooter() {
  return (
    <footer className="footer footer--customer">
      <div className="container footer__inner">
        <div className="footer__brand">
          <span className="nav__logo">kitchCU</span>
          <p>Discover trusted cloud kitchens with live-capture menus.</p>
          <span className="footer__host">{CUSTOMER_HOST}</span>
        </div>
        <div className="footer__links">
          <Link to="/">Home</Link>
          <Link to="/login">Customer sign in</Link>
          <a href={kitchenUrl("/login")}>Kitchen owner login</a>
        </div>
        <p className="footer__copy">© {new Date().getFullYear()} kitchCU Customer</p>
      </div>
    </footer>
  );
}
