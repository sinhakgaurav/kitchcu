import { Navbar } from "../components/Navbar";
import { Hero } from "../components/Hero";
import { Features } from "../components/Features";
import { HowItWorks } from "../components/HowItWorks";
import { ForCustomers, ForOwners } from "../components/AudienceSections";
import { ParallaxDivider } from "../components/ParallaxDivider";
import { Contact } from "../components/Contact";
import { Footer } from "../components/Footer";

export function LandingPage() {
  return (
    <>
      <Navbar />
      <main>
        <Hero variant="kitchen" />
        <ParallaxDivider />
        <ForOwners />
        <ParallaxDivider />
        <ForCustomers />
        <Features />
        <HowItWorks />
        <Contact />
      </main>
      <Footer />
    </>
  );
}
