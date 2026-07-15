/** Feature callouts on the left auth panel — under the headline, above the art. */

export type AuthHighlightSurface = "kitchen" | "customer" | "admin";

const HIGHLIGHTS: Record<AuthHighlightSurface, string[]> = {
  kitchen: [
    "Zero food commission vs 25–30% apps",
    "Honest ready-within dish timing",
    "In-range delivery you cover; Maps track",
    "Beyond range — customer pays logistics",
  ],
  customer: [
    "Ready-within times you can trust",
    "Google Maps from kitchen to door",
    "Dashboard: refunds, addresses, tips",
    "In-range: no delivery markup games",
  ],
  admin: [
    "Customers, refunds & money oversight",
    "API keys, flags & journey control",
    "Kitchen suspend & subscription force",
    "Zero-commission SaaS governance",
  ],
};

export function AuthLoginHighlights({ surface }: { surface: AuthHighlightSurface }) {
  const points = HIGHLIGHTS[surface];
  return (
    <ul className="auth-login-highlights" aria-label="What you get">
      {points.map((point) => (
        <li key={point}>{point}</li>
      ))}
    </ul>
  );
}
