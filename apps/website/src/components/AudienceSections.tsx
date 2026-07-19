import { Link } from "react-router-dom";
import { useInView } from "../hooks/useParallax";
import { images } from "../data/content";
import { customerUrl } from "../shared/urls";
import { ParallaxImage } from "./ParallaxImage";
import type { RefObject } from "react";
export function ForCustomers() {
  const { ref, visible } = useInView();

  return (
    <section className="section for-customers" id="customers" ref={ref as RefObject<HTMLElement>}>
      <div className="container for-customers__grid">
        <div className={`for-customers__visual reveal ${visible ? "reveal--visible" : ""}`}>
          <ParallaxImage src={images.customers.src} alt={images.customers.alt} />
        </div>        <div className={`for-customers__text reveal ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">For Customers</span>
          <h2>Trust what you order</h2>
          <p>
            Browse cloud kitchen menus with live-captured dish photos. No stock images,
            no aggregator markup — just honest food from local kitchens.
          </p>
          <ul>
            <li>Find kitchens by code</li>
            <li>See real dish photos with live-capture badge</li>
            <li>Order tracking coming to customer app</li>
          </ul>
          <a
            href={customerUrl("/browse")}
            className="btn btn--primary btn--lg"
            target="_blank"
            rel="noopener noreferrer"
          >
            Browse kitchens
          </a>
        </div>
      </div>
    </section>
  );
}

export function ForOwners() {
  const { ref, visible } = useInView();

  return (
    <section className="section for-owners" id="for-owners" ref={ref as RefObject<HTMLElement>}>
      <div className="container for-customers__grid for-customers__grid--reverse">
        <div className={`for-customers__text reveal ${visible ? "reveal--visible" : ""}`}>
          <span className="section__eyebrow">For Cloud Kitchen Owners</span>
          <h2>Run orders, menu &amp; customers in one place</h2>
          <p>
            WhatsApp intake, order lifecycle, live-capture menu, and owner dashboard —
            built for cloud kitchens who want control without paying food commission.
          </p>
          <Link to="/login" className="btn btn--primary btn--lg">
            Owner Login
          </Link>
        </div>
        <div className={`for-customers__visual reveal ${visible ? "reveal--visible" : ""}`}>
          <ParallaxImage src={images.owners.src} alt={images.owners.alt} />
        </div>      </div>
    </section>
  );
}
