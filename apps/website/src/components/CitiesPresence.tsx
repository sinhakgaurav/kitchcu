import type { CSSProperties, RefObject } from "react";
import { useTranslation } from "react-i18next";
import { CITIES_PRESENCE } from "../data/citiesPresence";
import { useInView } from "../hooks/useParallax";

type Props = {
  /** Lighter layout for customer discovery (no full section chrome). */
  variant?: "section" | "inline";
  id?: string;
};

export function CitiesPresence({ variant = "section", id = "cities" }: Props) {
  const { t } = useTranslation();
  const { ref, visible } = useInView();
  const cities = [...CITIES_PRESENCE].sort((a, b) => a.sortOrder - b.sortOrder);
  const liveCount = cities.filter((c) => c.status === "live").length;

  const body = (
    <>
      <div className={`section__header reveal reveal--blur ${visible ? "reveal--visible" : ""}`}>
        <span className="section__eyebrow">{t("cities.eyebrow")}</span>
        <h2>{t("cities.title")}</h2>
        <p>{t("cities.body", { count: liveCount })}</p>
      </div>
      <ul
        className={`cities-presence__grid reveal-stagger ${visible ? "reveal--visible" : ""}`}
        aria-label={t("cities.title")}
      >
        {cities.map((city, i) => (
          <li
            key={city.slug}
            className={`cities-presence__chip cities-presence__chip--${city.status}`}
            style={{ "--i": i } as CSSProperties}
          >
            <strong>{city.name}</strong>
            <span>{city.state}</span>
            <em>
              {city.status === "live" ? t("cities.statusLive") : t("cities.statusSoon")}
            </em>
          </li>
        ))}
      </ul>
    </>
  );

  if (variant === "inline") {
    return (
      <section
        className="cities-presence cities-presence--inline"
        id={id}
        ref={ref as RefObject<HTMLElement>}
      >
        {body}
      </section>
    );
  }

  return (
    <section
      className="section cities-presence"
      id={id}
      ref={ref as RefObject<HTMLElement>}
    >
      <div className="container">{body}</div>
    </section>
  );
}
