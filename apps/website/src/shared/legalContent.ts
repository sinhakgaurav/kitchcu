/** Public legal copy for portal pages + signup consent links. */

export type LegalSection = { heading: string; body: string[] };

export const LEGAL_UPDATED = "19 July 2026";

export const TERMS_SECTIONS: LegalSection[] = [
  {
    heading: "1. Who we are",
    body: [
      "kitchCU is a Growth Operating System for cloud kitchens, home food businesses, and tiffin services. We provide software tools for owners and a customer experience for ordering — we are not a food aggregator and we do not charge a per-order food commission.",
      "By creating an account or using kitchCU you agree to these Terms and our Privacy Policy.",
    ],
  },
  {
    heading: "2. Accounts",
    body: [
      "Kitchen owner accounts are for operators who run a kitchen on kitchen.kitchcu domains. Customer accounts are for people who browse menus and place orders. Platform admin access is for kitchCU staff only and is not offered as a public product persona.",
      "You must provide accurate contact details and keep OTP / login credentials confidential.",
    ],
  },
  {
    heading: "3. Kitchen owners",
    body: [
      "Owners are responsible for menu accuracy, live-capture honesty where required, food safety, delivery promises they set, and customer communications.",
      "Subscription fees for kitchCU software are separate from any money customers pay the kitchen for food or delivery.",
    ],
  },
  {
    heading: "4. Customers",
    body: [
      "Orders are fulfilled by the kitchen you choose. Prices, prep times, and delivery windows are set by that kitchen.",
      "Refunds follow the Kitchen Refund Policy for that kitchen, supported by the Platform Refund Policy.",
    ],
  },
  {
    heading: "5. Acceptable use",
    body: [
      "Do not misuse the platform, attempt cross-tenant access, abuse messaging, or upload deceptive media as live-capture dish heroes.",
    ],
  },
  {
    heading: "6. Changes",
    body: [
      "We may update these Terms. Material changes will be reflected on this page with an updated date. Continued use after changes means you accept the revised Terms.",
    ],
  },
];

export const PRIVACY_SECTIONS: LegalSection[] = [
  {
    heading: "1. Data we collect",
    body: [
      "Account data: name, phone, email (if provided), kitchen profile, and delivery addresses.",
      "Order and payment metadata needed to run checkout, subscriptions, and refunds. We do not sell your personal data.",
    ],
  },
  {
    heading: "2. How we use data",
    body: [
      "To operate OTP login, menus, orders, delivery quotes, notifications, support tickets, and owner analytics scoped to each kitchen.",
      "Kitchen CRM data (spend, patterns, tags) belongs to that kitchen and is not shared across kitchens.",
    ],
  },
  {
    heading: "3. Sharing",
    body: [
      "We share data with service providers required to run the product (e.g. SMS/WhatsApp, payment gateways, courier partners) under contracts that limit use to providing those services.",
      "We may disclose data when required by law.",
    ],
  },
  {
    heading: "4. Retention & security",
    body: [
      "We retain data as long as needed for the product, legal, and accounting purposes. Access is role-scoped; secrets are not logged.",
    ],
  },
  {
    heading: "5. Your choices",
    body: [
      "Contact support to request correction or deletion where applicable. Owners control their kitchen CRM and menu content.",
    ],
  },
];

/** Primary customer-facing refund rules — owned by kitchens, enforced on platform. */
export const KITCHEN_REFUND_SECTIONS: LegalSection[] = [
  {
    heading: "1. Principle",
    body: [
      "Each kitchen owns the customer relationship and refund decision for its orders. kitchCU does not take a food commission and does not sit in the middle of food payments as an aggregator.",
      "When you order from a kitchen, that kitchen’s refund practices apply, within the platform rules below.",
    ],
  },
  {
    heading: "2. When refunds may apply",
    body: [
      "Wrong or missing items, quality issues raised with evidence, cancellations before acceptance, or other cases the kitchen accepts in good faith.",
      "Delivery delays alone are not automatic refunds when the kitchen set honest prep/delivery windows.",
    ],
  },
  {
    heading: "3. Full vs partial",
    body: [
      "Owners may issue a full refund or a partial refund for the affected amount.",
      "Online payments that were captured may be reversed via the kitchen’s payment gateway where available. Partial refunds and COD / uncaptured payments are completed as a direct transfer to the customer’s UPI or bank details on file, with the order code as the transfer remark and proof uploaded by the kitchen.",
    ],
  },
  {
    heading: "4. Customer payout details",
    body: [
      "Customers should keep UPI / bank payout details updated in their account so kitchens can complete direct refunds quickly.",
    ],
  },
  {
    heading: "5. Timeline",
    body: [
      "Kitchens should respond to refund requests promptly. Gateway refunds follow the payment provider’s settlement timing. Direct transfers depend on the kitchen completing the payout and marking evidence on the platform.",
    ],
  },
];

/**
 * Platform refund policy — derived from kitchen refund policy.
 * Platform does not invent a separate food-refund product; it binds kitchens to kitchen policy + rails.
 */
export const PLATFORM_REFUND_SECTIONS: LegalSection[] = [
  {
    heading: "1. Driven by kitchen policy",
    body: [
      "The Platform Refund Policy is the enforcement layer for the Kitchen Refund Policy. kitchCU does not replace kitchen refunds with a platform “food wallet” or commission clawback model.",
      "Every kitchen on kitchCU must honour the Kitchen Refund Policy when operating through the platform tools (orders, payments, refund workflows).",
    ],
  },
  {
    heading: "2. What the platform provides",
    body: [
      "Software rails for owners to request and complete full (gateway) or partial/direct refunds, with tenant isolation and audit events.",
      "Customer payout profile storage so kitchens can pay the right destination.",
      "Support escalation for disputes when a kitchen fails to follow the Kitchen Refund Policy after a valid claim.",
    ],
  },
  {
    heading: "3. What the platform does not do",
    body: [
      "kitchCU does not automatically refund food orders from platform funds.",
      "kitchCU does not charge per-order food commission and therefore does not “refund commission” as an aggregator would.",
    ],
  },
  {
    heading: "4. Multi-kitchen checkouts",
    body: [
      "When a customer pays across multiple kitchens, refunds remain per kitchen sub-order under that kitchen’s policy and payment split — consistent with the Kitchen Refund Policy applied kitchen-by-kitchen.",
    ],
  },
  {
    heading: "5. Changes",
    body: [
      "If the Kitchen Refund Policy is updated, this Platform Refund Policy updates in lockstep so platform enforcement always follows kitchen-facing rules.",
    ],
  },
];
