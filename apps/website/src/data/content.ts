/** Local marketing imagery — served from public/media (no broken Unsplash deps). */

const m = (file: string) => `/media/food/${file}`;

/** Full-bleed hero shards — large left/right frames that track the cursor */
export const parallaxPhotos = [
  {
    src: m("skewers.jpg"),
    alt: "Grilled skewers",
    speed: 0.38,
    top: "6%",
    left: "-4%",
    width: "360px",
    rotate: "-9deg",
  },
  {
    src: m("biryani.jpg"),
    alt: "Biryani bowl",
    speed: 0.58,
    top: "52%",
    left: "2%",
    width: "320px",
    rotate: "6deg",
  },
  {
    src: m("pizza.jpg"),
    alt: "Artisan pizza",
    speed: 0.48,
    top: "18%",
    left: "22%",
    width: "260px",
    rotate: "7deg",
  },
  {
    src: m("salad.jpg"),
    alt: "Fresh salad bowl",
    speed: 0.66,
    top: "68%",
    left: "28%",
    width: "240px",
    rotate: "-5deg",
  },
  {
    src: m("burger.jpg"),
    alt: "Gourmet burger",
    speed: 0.44,
    top: "8%",
    left: "68%",
    width: "340px",
    rotate: "5deg",
  },
  {
    src: m("bbq.jpg"),
    alt: "BBQ platter",
    speed: 0.62,
    top: "42%",
    left: "74%",
    width: "300px",
    rotate: "-7deg",
  },
  {
    src: m("pasta.jpg"),
    alt: "Home kitchen spread",
    speed: 0.54,
    top: "72%",
    left: "58%",
    width: "280px",
    rotate: "4deg",
  },
  {
    src: m("dessert.jpg"),
    alt: "Dessert plate",
    speed: 0.5,
    top: "28%",
    left: "82%",
    width: "250px",
    rotate: "-4deg",
  },
];

/** Masonry-style gallery for customer landing */
export const customerGallery = [
  { src: m("biryani.jpg"), alt: "Biryani", label: "Biryani", rotate: "-3deg" },
  { src: m("pasta.jpg"), alt: "Wok toss", label: "Wok toss", rotate: "2deg" },
  { src: m("bowls.jpg"), alt: "Bowls", label: "Meal bowls", rotate: "-2deg" },
  { src: m("burger.jpg"), alt: "Burger", label: "Gourmet burger", rotate: "4deg" },
  { src: m("rice.jpg"), alt: "Thali", label: "Home thali", rotate: "-5deg" },
  { src: m("pizza.jpg"), alt: "Pizza", label: "Artisan pizza", rotate: "3deg" },
  { src: m("samosa.jpg"), alt: "Snacks", label: "Evening snacks", rotate: "-2deg" },
  { src: m("dessert.jpg"), alt: "Dessert", label: "Sweet treat", rotate: "5deg" },
];

export const customerShowcase = [
  {
    title: "Live-capture heroes",
    desc: "Every dish photo is captured live in the kitchen — no stock images, no bait-and-switch.",
    image: { src: m("kitchen.jpg"), alt: "Live food photography" },
  },
  {
    title: "Local cloud kitchens",
    desc: "Support neighbourhood home kitchens with honest pricing and direct relationships.",
    image: { src: m("service.jpg"), alt: "Welcoming kitchen" },
  },
  {
    title: "Browse by kitchen code",
    desc: "Your favourite kitchen shares a simple code — find their menu in seconds.",
    image: { src: m("dining.jpg"), alt: "Fine dining spread" },
  },
];

export const heroParallaxImages = {
  back: {
    src: m("kitchen.jpg"),
    alt: "Chef cooking in professional kitchen",
    speed: 0.22,
  },
  mid: {
    src: m("dining.jpg"),
    alt: "Fine dining spread",
    speed: 0.4,
  },
  front: {
    src: m("burger.jpg"),
    alt: "Gourmet burger close-up",
    speed: 0.58,
  },
  accent: {
    src: m("bbq.jpg"),
    alt: "BBQ ribs platter",
    speed: 0.75,
  },
};

/** Portal feature cards — copy via i18n keys (portal.feature*). */
export const featureCards = [
  {
    titleKey: "portal.featureWhatsappTitle",
    descKey: "portal.featureWhatsappDesc",
    image: { src: m("samosa.jpg"), alt: "WhatsApp orders food" },
  },
  {
    titleKey: "portal.featureLiveTitle",
    descKey: "portal.featureLiveDesc",
    image: { src: m("skewers.jpg"), alt: "Live cooking" },
  },
  {
    titleKey: "portal.featureBrandTitle",
    descKey: "portal.featureBrandDesc",
    image: { src: m("dining.jpg"), alt: "Branded kitchen storefront" },
  },
  {
    titleKey: "portal.featureGoldenTitle",
    descKey: "portal.featureGoldenDesc",
    image: { src: m("bowls.jpg"), alt: "Peak kitchen performance" },
  },
  {
    titleKey: "portal.featureStreamTitle",
    descKey: "portal.featureStreamDesc",
    image: { src: m("kitchen.jpg"), alt: "Live cooking showcase" },
  },
  {
    titleKey: "portal.featureTemplatesTitle",
    descKey: "portal.featureTemplatesDesc",
    image: { src: m("service.jpg"), alt: "Kitchen messaging" },
  },
  {
    titleKey: "portal.featureLifecycleTitle",
    descKey: "portal.featureLifecycleDesc",
    image: { src: m("restaurant.jpg"), alt: "Kitchen service" },
  },
  {
    titleKey: "portal.featureDashboardTitle",
    descKey: "portal.featureDashboardDesc",
    image: { src: m("restaurant.jpg"), alt: "Commercial kitchen" },
  },
] as const;

/** @deprecated Use featureCards + t() — kept for parallax story English fallbacks */
export const features = featureCards.map((f) => ({
  title: f.titleKey,
  desc: f.descKey,
  image: f.image,
}));

export const images = {
  hero: heroParallaxImages.back,
  heroSecondary: heroParallaxImages.mid,
  menu: { src: m("bowls.jpg"), alt: "Healthy meal bowls" },
  sushi: { src: m("rice.jpg"), alt: "Rice platter" },
  tacos: { src: m("samosa.jpg"), alt: "Street snacks" },
  steak: { src: m("bbq.jpg"), alt: "BBQ platter" },
  analytics: { src: m("restaurant.jpg"), alt: "Restaurant atmosphere" },
  onboardRegister: { src: m("kitchen.jpg"), alt: "Kitchen team" },
  onboardMenu: { src: m("bowls.jpg"), alt: "Cloud kitchen prep" },
  onboardWhatsapp: { src: m("samosa.jpg"), alt: "WhatsApp orders" },
  contact: { src: m("service.jpg"), alt: "Welcoming kitchen" },
  login: { src: m("kitchen.jpg"), alt: "Kitchen owner" },
  customers: { src: m("dining.jpg"), alt: "Brunch for customers" },
  owners: { src: m("restaurant.jpg"), alt: "Commercial kitchen" },
};

export const howItWorksSteps = [
  {
    step: "01",
    titleKey: "portal.how1Title",
    descKey: "portal.how1Desc",
    image: images.onboardRegister,
  },
  {
    step: "02",
    titleKey: "portal.how2Title",
    descKey: "portal.how2Desc",
    image: images.onboardMenu,
  },
  {
    step: "03",
    titleKey: "portal.how3Title",
    descKey: "portal.how3Desc",
    image: images.onboardWhatsapp,
  },
] as const;

/** @deprecated Use howItWorksSteps + t() */
export const howItWorks = howItWorksSteps.map((s) => ({
  step: s.step,
  title: s.titleKey,
  desc: s.descKey,
  image: s.image,
}));

export const stats = [
  { value: "0%", label: "Food commission" },
  { value: "<5m", label: "Time to first order" },
  { value: "₹499", label: "Starter plan from" },
];

/** Pricing cards — names/features via portal.plan* i18n keys. */
export const pricingPlans = [
  {
    id: "starter",
    price: 499,
    featured: false,
    nameKey: "portal.planStarterName",
    descKey: "portal.planStarterDesc",
    ctaKey: "portal.planStarterCta",
    featureKeys: [
      "portal.planStarterF1",
      "portal.planStarterF2",
      "portal.planStarterF3",
      "portal.planStarterF4",
      "portal.planStarterF5",
      "portal.planStarterF6",
    ],
  },
  {
    id: "growth",
    price: 999,
    featured: true,
    nameKey: "portal.planGrowthName",
    descKey: "portal.planGrowthDesc",
    ctaKey: "portal.planGrowthCta",
    featureKeys: [
      "portal.planGrowthF1",
      "portal.planGrowthF2",
      "portal.planGrowthF3",
      "portal.planGrowthF4",
      "portal.planGrowthF5",
      "portal.planGrowthF6",
    ],
  },
  {
    id: "scale",
    price: 1999,
    featured: false,
    nameKey: "portal.planScaleName",
    descKey: "portal.planScaleDesc",
    ctaKey: "portal.planScaleCta",
    featureKeys: [
      "portal.planScaleF1",
      "portal.planScaleF2",
      "portal.planScaleF3",
      "portal.planScaleF4",
      "portal.planScaleF5",
      "portal.planScaleF6",
    ],
  },
] as const;

export const supportFaqs = {
  owner: [
    {
      q: "How do WhatsApp orders work?",
      a: "Customers message your kitchen on WhatsApp. Paste the message in kitchen.kitchCU.in → Orders → Parse to draft. Review matched items, fix unmatched lines, and confirm in one tap.",
    },
    {
      q: "Is there commission on food orders?",
      a: "No. kitchCU is subscription-only. You pay a flat monthly plan — zero per-order food commission. You keep customer relationships and margins.",
    },
    {
      q: "How do live-capture photos work?",
      a: "Hero dish images must be captured live in your kitchen (camera or live URL with captured_at timestamp). Stock photos are not allowed — this builds customer trust.",
    },
    {
      q: "Can I see revenue and repeat customers?",
      a: "Yes — Growth and Scale plans include Reports: revenue trend, top dishes, busy hours (IST), repeat-customer rate, VIP segments, and win-back lists.",
    },
    {
      q: "What is a Golden performance day?",
      a: "Growth intelligence scores recent orders, home-taste ratings, and comment sentiment. When a day stands out, KitchCu suggests pinning that recipe so you can recreate peak performance.",
    },
    {
      q: "How do kitchen WhatsApp and Razorpay work?",
      a: "Each kitchen connects its own WhatsApp Business phone ID and Razorpay keys under Integrations. Platform Meta/Razorpay SaaS keys stay under Admin → API Keys — kitchen credentials never overwrite those.",
    },
  ],
  customer: [
    {
      q: "How do I find a kitchen?",
      a: "Open the customer app, enter a kitchen code (e.g. CKPNQ001), open a branded link like /k/CKPNQ001, or use Nearby with your location to discover cloud kitchens sorted by distance.",
    },
    {
      q: "Can I order online?",
      a: "Browse live-capture menus and checkout with COD, UPI, or online pay — sign in with WhatsApp OTP on customer.kitchCU.in.",
    },
    {
      q: "Why live-capture photos?",
      a: "Every hero dish photo is taken live in the kitchen — not stock images. You see what the home chef actually cooks, building trust in home-made food.",
    },
    {
      q: "Who do I contact for order issues?",
      a: "Contact the kitchen directly first — kitchCU connects you to the home chef, not a call centre. Platform help: hello@kitchCU.in.",
    },
  ],
};

export const supportChannels = [
  { label: "Email", value: "hello@kitchCU.in", href: "mailto:hello@kitchCU.in" },
  { label: "Hours", value: "Mon–Sat, 9am–7pm IST" },
  { label: "Location", value: "Pune, Maharashtra, India" },
  { label: "Response time", value: "Within 24 hours on weekdays" },
];

/** Sample dish hero URLs for menu cards and add-dish hints */
export const sampleDishImages = {
  paneerTikka: m("skewers.jpg"),
  biryani: m("biryani.jpg"),
  dosa: m("dosa.jpg"),
  butterChicken: m("bbq.jpg"),
  lassi: m("salad.jpg"),
  gulabJamun: m("dessert.jpg"),
  thali: m("rice.jpg"),
  pavBhaji: m("pizza.jpg"),
} as const;

/** Stable placeholder cover for discovery cards (hash by kitchen id). */
export function kitchenCardImage(kitchenId: string): string {
  const values = Object.values(sampleDishImages);
  let h = 0;
  for (let i = 0; i < kitchenId.length; i += 1) h = (h * 31 + kitchenId.charCodeAt(i)) | 0;
  return values[Math.abs(h) % values.length];
}
