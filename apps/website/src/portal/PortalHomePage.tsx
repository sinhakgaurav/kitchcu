import { AppTiles } from "../components/AppTiles";
import { Contact } from "../components/Contact";
import { CustomerShowcase } from "../components/CustomerShowcase";
import { Features } from "../components/Features";
import { FloatingGallery } from "../components/FloatingGallery";
import { HowItWorks } from "../components/HowItWorks";
import { ParallaxDivider } from "../components/ParallaxDivider";
import { ParallaxMosaic } from "../components/ParallaxMosaic";
import { ParallaxScene } from "../components/ParallaxScene";
import { ParallaxScrollProgress } from "../components/ParallaxScrollProgress";
import { ParallaxStickyStory } from "../components/ParallaxStickyStory";
import { PortalFooter } from "../components/PortalFooter";
import { PortalHero } from "../components/PortalHero";
import { PortalNavbar } from "../components/PortalNavbar";
import { Pricing } from "../components/Pricing";
import { SupportChat } from "../components/SupportChat";
import { SupportSection } from "../components/SupportSection";
import { ADMIN_HOST, CUSTOMER_HOST, KITCHEN_HOST } from "../shared/brand";
import { kitchenUrl } from "../shared/urls";

export function PortalHomePage() {
  return (
    <div className="portal-site">
      <ParallaxScrollProgress />
      <PortalNavbar />
      <main>
        <PortalHero />
        <section className="section portal-apps portal-apps--parallax" id="apps">
          <ParallaxScene variant="section" />
          <div className="container portal-apps__inner">
            <div className="section__header">
              <span className="section__eyebrow">Apps</span>
              <h2>One platform, three experiences</h2>
              <p>
                Customers browse on <strong>{CUSTOMER_HOST}</strong>. Owners run kitchens on{" "}
                <strong>{KITCHEN_HOST}</strong>. Platform team uses <strong>{ADMIN_HOST}</strong>.
              </p>
            </div>
            <AppTiles />
          </div>
        </section>
        <FloatingGallery />
        <ParallaxDivider />
        <Features />
        <ParallaxStickyStory />
        <ParallaxDivider reverse />
        <CustomerShowcase />
        <ParallaxMosaic />
        <HowItWorks ctaHref={kitchenUrl("/login")} ctaLabel="Start as kitchen owner" />
        <Pricing />
        <SupportSection />
        <Contact />
      </main>
      <PortalFooter />
      <SupportChat />
    </div>
  );
}
