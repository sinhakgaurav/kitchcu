import { useTranslation } from "react-i18next";
import { KitchenNavbar } from "../../components/KitchenNavbar";
import { Hero } from "../../components/Hero";
import { CitiesPresence } from "../../components/CitiesPresence";
import { Features } from "../../components/Features";
import { HowItWorks } from "../../components/HowItWorks";
import { ParallaxDivider } from "../../components/ParallaxDivider";
import { Contact } from "../../components/Contact";
import { KitchenFooter } from "../../components/KitchenFooter";

export function KitchenLandingPage() {
  const { t } = useTranslation();
  return (
    <div className="kitchen-landing">
      <KitchenNavbar />
      <main>
        <Hero variant="kitchen" />
        <ParallaxDivider />
        <Features />
        <CitiesPresence />
        <ParallaxDivider reverse />
        <HowItWorks ctaHref="/login" ctaLabel={t("common.ownerLogin")} />
        <Contact />
      </main>
      <KitchenFooter />
    </div>
  );
}