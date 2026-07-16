import { Link } from "react-router-dom";
import { BrandNavMark } from "./BrandNavMark";
import { APP_NAME, KITCHEN_HOST } from "../shared/brand";
import { customerUrl } from "../shared/urls";

export function KitchenFooter() {
  return (
    <footer className="footer footer--kitchen">
      <div className="container footer__inner">
        <div className="footer__brand">
          <BrandNavMark height={36} />
          <p>Run your cloud kitchen — orders, menu, and customers.</p>
          <span className="footer__host">{KITCHEN_HOST}</span>
        </div>
        <div className="footer__links">
          <Link to="/">Home</Link>
          <Link to="/login">Owner sign in</Link>
          <a href={customerUrl("/")} target="_blank" rel="noopener noreferrer">Customer app</a>
        </div>
        <p className="footer__copy">
          © {new Date().getFullYear()} {APP_NAME} · Kitchen
        </p>
      </div>
    </footer>
  );
}
