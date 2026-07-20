import { useTranslation } from "react-i18next";
import { AppTiles } from "../components/AppTiles";
import { Contact } from "../components/Contact";
import { Features } from "../components/Features";
import { HowItWorks } from "../components/HowItWorks";
import { ParallaxScrollProgress } from "../components/ParallaxScrollProgress";
import { PortalFooter } from "../components/PortalFooter";
import { PortalHero } from "../components/PortalHero";
import { PortalNavbar } from "../components/PortalNavbar";
import { Pricing } from "../components/Pricing";
import { SupportChat } from "../components/SupportChat";
import { SupportSection } from "../components/SupportSection";
import { kitchenUrl } from "../shared/urls";

/**
 * Portal landing — one composition per section.
 * Dropped admin tile + repeated gallery/story/mosaic/showcase stacks.
 */
export function PortalHomePage() {
  const { t } = useTranslation();

  return (
    <div className="portal-site">
      <ParallaxScrollProgress />
      <PortalNavbar />
      <main>
        <PortalHero />

        <section className="section portal-apps portal-apps--duo" id="apps">
          <div className="container portal-apps__inner">
            <div className="section__header">
              <span className="section__eyebrow">{t("portal.appsEyebrow")}</span>
              <h2>{t("portal.appsTitle")}</h2>
              <p>{t("portal.appsBody")}</p>
            </div>
            <AppTiles />
          </div>
        </section>

        <Features />
        <HowItWorks ctaHref={kitchenUrl("/login")} />
        <Pricing />
        <SupportSection />
        <Contact />
      </main>
      <PortalFooter />
      <SupportChat />
    </div>
  );
}
