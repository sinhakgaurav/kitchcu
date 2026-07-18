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

export const features = [
  {
    title: "WhatsApp Order Hub",
    desc: "Turn chat messages into structured orders. Confirm drafts in one tap.",
    image: { src: m("samosa.jpg"), alt: "WhatsApp orders food" },
  },
  {
    title: "Live-Capture Menu",
    desc: "Hero dish photos are captured live so customers trust what they order.",
    image: { src: m("skewers.jpg"), alt: "Live cooking" },
  },
  {
    title: "Branded kitchen page",
    desc: "Publish a shareable storefront at /k/your-code — your brand, menu, and checkout.",
    image: { src: m("dining.jpg"), alt: "Branded kitchen storefront" },
  },
  {
    title: "Golden performance day",
    desc: "ML reads ratings and comments to pin your best cooking days and recipes.",
    image: { src: m("bowls.jpg"), alt: "Peak kitchen performance" },
  },
  {
    title: "Live dish showcase",
    desc: "Go live with ingredients → prep → prepared so customers see the real dish.",
    image: { src: m("kitchen.jpg"), alt: "Live cooking showcase" },
  },
  {
    title: "Order Lifecycle",
    desc: "Track every order from received to delivered with status updates.",
    image: { src: m("service.jpg"), alt: "Kitchen service" },
  },
  {
    title: "Owner Dashboard",
    desc: "Menus, orders, WhatsApp & payments, growth — one kitchen workspace.",
    image: { src: m("restaurant.jpg"), alt: "Commercial kitchen" },
  },
];

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

export const howItWorks = [
  {
    step: "01",
    title: "Register your kitchen",
    desc: "Sign up as an owner, verify OTP, and create your cloud kitchen profile.",
    image: images.onboardRegister,
  },
  {
    step: "02",
    title: "Publish your menu",
    desc: "Add dishes with live photos. Share your customer menu link.",
    image: images.onboardMenu,
  },
  {
    step: "03",
    title: "Serve customers",
    desc: "Accept WhatsApp orders, manage lifecycle, and grow repeat customers.",
    image: images.onboardWhatsapp,
  },
];

export const stats = [
  { value: "0%", label: "Food commission" },
  { value: "<5m", label: "Time to first order" },
  { value: "₹499", label: "Starter plan from" },
];

export const pricingPlans = [
  {
    id: "starter",
    name: "Starter",
    price: 499,
    period: "month",
    description: "Perfect for home chefs launching their first cloud kitchen.",
    featured: false,
    features: [
      "1 kitchen location",
      "Manual & WhatsApp orders",
      "Live-capture menu (cuisine → veg/non-veg → dish)",
      "Order lifecycle tracking",
      "Customer menu link sharing",
      "Email support",
    ],
    cta: "Start free trial",
  },
  {
    id: "growth",
    name: "Growth",
    price: 999,
    period: "month",
    description: "For kitchens ready to grow repeat customers and revenue.",
    featured: true,
    features: [
      "Everything in Starter",
      "Growth reports & revenue analytics",
      "Golden performance day + recipe pins",
      "Top dishes & peak-hour insights",
      "Branded customer storefront (/k/code)",
      "Customer CRM & repeat-rate tracking",
      "Churn win-back customer list",
      "Kitchen WhatsApp + Razorpay integrations",
      "Priority email support",
    ],
    cta: "Most popular",
  },
  {
    id: "scale",
    name: "Scale",
    price: 1999,
    period: "month",
    description: "Multi-kitchen operators scaling across neighbourhoods.",
    featured: false,
    features: [
      "Everything in Growth",
      "Up to 5 kitchens",
      "Multi-kitchen dashboard",
      "Advanced customer segmentation",
      "Festival & daily menu campaigns",
      "Live dish showcase (ingredients → prep → prepared)",
      "Dedicated onboarding call",
      "Priority support + AI assistant",
    ],
    cta: "Contact sales",
  },
];

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
