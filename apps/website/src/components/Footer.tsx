import { Link } from "react-router-dom";
import { APP_NAME } from "../shared/brand";

export function Footer() {
  return (
    <footer className="footer">
      <div className="container footer__inner">
        <div className="footer__brand">
          <span className="nav__logo">{APP_NAME}</span>
          <p>Cloud kitchen platform for owners and customers.</p>
        </div>
        <div className="footer__links">
          <a href="/#for-owners">Owners</a>
          <Link to="/customers">Customers</Link>
          <Link to="/login">Owner Login</Link>
          <a href="/#contact">Contact</a>
        </div>
        <p className="footer__copy">
          © {new Date().getFullYear()} {APP_NAME}. Zero food commission.
        </p>
      </div>
    </footer>
  );
}
