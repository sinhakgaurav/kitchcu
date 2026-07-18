import { Link } from "react-router-dom";
import { PortalFooter } from "../components/PortalFooter";
import { PortalNavbar } from "../components/PortalNavbar";
import { APP_NAME, SUPPORT_EMAIL } from "../shared/brand";
import {
  KITCHEN_REFUND_SECTIONS,
  LEGAL_UPDATED,
  PLATFORM_REFUND_SECTIONS,
  PRIVACY_SECTIONS,
  TERMS_SECTIONS,
  type LegalSection,
} from "../shared/legalContent";

type LegalKind = "terms" | "privacy" | "refund" | "platform-refund";

const META: Record<
  LegalKind,
  { title: string; eyebrow: string; intro: string; sections: LegalSection[]; related?: { to: string; label: string }[] }
> = {
  terms: {
    title: "Terms & Conditions",
    eyebrow: "Legal",
    intro: `${APP_NAME} software and marketplaces for cloud kitchens — zero food commission.`,
    sections: TERMS_SECTIONS,
    related: [
      { to: "/privacy", label: "Privacy Policy" },
      { to: "/refund-policy", label: "Kitchen Refund Policy" },
    ],
  },
  privacy: {
    title: "Privacy Policy",
    eyebrow: "Legal",
    intro: "How we collect, use, and protect personal data on kitchCU.",
    sections: PRIVACY_SECTIONS,
    related: [
      { to: "/terms", label: "Terms" },
      { to: "/refund-policy", label: "Kitchen Refund Policy" },
    ],
  },
  refund: {
    title: "Kitchen Refund Policy",
    eyebrow: "Refunds",
    intro:
      "Customer refunds are decided and fulfilled by the kitchen. This is the primary refund policy for every kitchen on kitchCU.",
    sections: KITCHEN_REFUND_SECTIONS,
    related: [
      { to: "/platform-refund-policy", label: "Platform Refund Policy (enforcement)" },
      { to: "/terms", label: "Terms" },
    ],
  },
  "platform-refund": {
    title: "Platform Refund Policy",
    eyebrow: "Refunds",
    intro:
      "Driven by the Kitchen Refund Policy — kitchCU enforces kitchen refunds through product rails; it does not replace them with aggregator-style platform refunds.",
    sections: PLATFORM_REFUND_SECTIONS,
    related: [
      { to: "/refund-policy", label: "Kitchen Refund Policy (source)" },
      { to: "/terms", label: "Terms" },
    ],
  },
};

export function LegalPage({ kind }: { kind: LegalKind }) {
  const meta = META[kind];

  return (
    <div className="portal-site portal-legal">
      <PortalNavbar />
      <main className="legal-page">
        <div className="container legal-page__inner">
          <p className="section__eyebrow">{meta.eyebrow}</p>
          <h1>{meta.title}</h1>
          <p className="legal-page__intro">{meta.intro}</p>
          <p className="legal-page__updated">Last updated: {LEGAL_UPDATED}</p>

          {meta.sections.map((section) => (
            <section key={section.heading} className="legal-page__section">
              <h2>{section.heading}</h2>
              {section.body.map((para) => (
                <p key={para.slice(0, 48)}>{para}</p>
              ))}
            </section>
          ))}

          {meta.related && (
            <nav className="legal-page__related" aria-label="Related policies">
              {meta.related.map((r) => (
                <Link key={r.to} to={r.to}>
                  {r.label} →
                </Link>
              ))}
            </nav>
          )}

          <p className="legal-page__contact">
            Questions? <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
          </p>
          <Link to="/" className="btn btn--ghost btn--sm">
            ← Back to home
          </Link>
        </div>
      </main>
      <PortalFooter />
    </div>
  );
}
