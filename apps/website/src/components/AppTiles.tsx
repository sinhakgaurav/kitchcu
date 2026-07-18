import { images } from "../data/content";
import { CUSTOMER_HOST, KITCHEN_HOST } from "../shared/brand";
import { customerUrl, kitchenUrl } from "../shared/urls";

const tiles = [
  {
    id: "customer",
    host: CUSTOMER_HOST,
    title: "Order home-made food",
    description: "Nearby kitchens, live-capture menus, honest ETAs, and fair delivery fees.",
    href: () => customerUrl("/"),
    image: images.customers.src,
    accent: "teal" as const,
    cta: "Open customer app",
  },
  {
    id: "kitchen",
    host: KITCHEN_HOST,
    title: "Run your kitchen",
    description: "WhatsApp orders, menu, tiffin plans, reports — zero food commission.",
    href: () => kitchenUrl("/login"),
    image: images.owners.src,
    accent: "orange" as const,
    cta: "Owner sign in",
  },
];

export function AppTiles() {
  return (
    <div className="app-tiles app-tiles--duo">
      {tiles.map((tile) => (
        <a
          key={tile.id}
          className={`app-tile app-tile--${tile.accent}`}
          href={tile.href()}
          target="_blank"
          rel="noopener noreferrer"
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
