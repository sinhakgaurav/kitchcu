import { images } from "../data/content";
import { ADMIN_HOST, CUSTOMER_HOST, KITCHEN_HOST } from "../shared/brand";
import { customerUrl, kitchenUrl, adminUrl } from "../shared/urls";

const tiles = [
  {
    id: "customer",
    host: CUSTOMER_HOST,
    title: "Browse & order",
    description: "Discover nearby cloud kitchens, live-capture menus, and customer sign-in.",
    href: () => customerUrl("/"),
    image: images.customers.src,
    accent: "teal" as const,
    cta: "Open customer app",
  },
  {
    id: "kitchen",
    host: KITCHEN_HOST,
    title: "Owner portal",
    description: "WhatsApp orders, menu management, dashboard, and kitchen operations.",
    href: () => kitchenUrl("/"),
    image: images.owners.src,
    accent: "orange" as const,
    cta: "Open kitchen app",
  },
  {
    id: "admin",
    host: ADMIN_HOST,
    title: "Platform admin",
    description: "Manage all owners, kitchens, orders, and platform status.",
    href: () => adminUrl("/"),
    image: images.analytics.src,
    accent: "orange" as const,
    cta: "Open admin panel",
  },
];

export function AppTiles() {
  return (
    <div className="app-tiles">
      {tiles.map((tile) => (
        <a
          key={tile.id}
          className={`app-tile app-tile--${tile.accent}`}
          href={tile.href()}
          rel="noopener"
        >
          <div className="app-tile__media">
            <img src={tile.image} alt="" loading="lazy" />
            <div className="app-tile__overlay" />
          </div>
          <div className="app-tile__body">
            <span className="app-tile__host">{tile.host}</span>
            <h2>{tile.title}</h2>
            <p>{tile.description}</p>
            <span className="app-tile__cta">{tile.cta} →</span>
          </div>
        </a>
      ))}
    </div>
  );
}
