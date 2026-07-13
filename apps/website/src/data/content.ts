/** High-quality imagery for parallax depth + sections */

const u = (id: string, w = 800) =>
  `https://images.unsplash.com/${id}?w=${w}&q=85&auto=format&fit=crop`;

export const parallaxPhotos = [
  {
    src: u("photo-1555939594-58d7cb561ad1", 700),
    alt: "Grilled skewers",
    speed: 0.42,
    top: "6%",
    left: "-5%",
    width: "280px",
    rotate: "-10deg",
  },
  {
    src: u("photo-1585937421612-70a008592f82", 650),
    alt: "Biryani bowl",
    speed: 0.62,
    top: "58%",
    left: "0%",
    width: "220px",
    rotate: "7deg",
  },
  {
    src: u("photo-1606787366856-119e63814833", 700),
    alt: "Colorful bowls",
    speed: 0.5,
    top: "10%",
    right: "-4%",
    width: "260px",
    rotate: "12deg",
  },
  {
    src: u("photo-1565299624946-b28f40a0ae38", 620),
    alt: "Artisan pizza",
    speed: 0.72,
    top: "65%",
    right: "3%",
    width: "200px",
    rotate: "-6deg",
  },
  {
    src: u("photo-1493770348163-869783f6a188", 580),
    alt: "Brunch spread",
    speed: 0.85,
    top: "32%",
    left: "36%",
    width: "170px",
    rotate: "5deg",
  },
  {
    src: u("photo-1567620905732-2d1ec7ab7518", 640),
    alt: "Pancakes stack",
    speed: 0.48,
    top: "72%",
    left: "28%",
    width: "190px",
    rotate: "-4deg",
  },
  {
    src: u("photo-1512621776951-a57141f2eefd", 600),
    alt: "Fresh salad bowl",
    speed: 0.58,
    top: "18%",
    left: "52%",
    width: "150px",
    rotate: "8deg",
  },
];

/** Masonry-style gallery for customer landing */
export const customerGallery = [
  { src: u("photo-1585937421612-70a008592f82", 600), alt: "Biryani", label: "Biryani", rotate: "-3deg" },
  { src: u("photo-1563379927098-05c457674dd8", 600), alt: "Wok toss", label: "Wok toss", rotate: "2deg" },
  { src: u("photo-1546069901-ba9599a7e63c", 600), alt: "Bowls", label: "Meal bowls", rotate: "-2deg" },
  { src: u("photo-1565958011703-398f087be584", 600), alt: "Burger", label: "Gourmet burger", rotate: "4deg" },
  { src: u("photo-1606491956689-2ea8660f9640", 600), alt: "Thali", label: "Home thali", rotate: "-5deg" },
  { src: u("photo-1565299624946-b28f40a0ae38", 600), alt: "Pizza", label: "Artisan pizza", rotate: "3deg" },
  { src: u("photo-1626074353815-4aa7c2609e59", 600), alt: "Lassi", label: "Mango lassi", rotate: "-2deg" },
  { src: u("photo-1571875250683-875e8d8e8c8e", 600), alt: "Dessert", label: "Gulab jamun", rotate: "5deg" },
];

export const customerShowcase = [
  {
    title: "Live-capture heroes",
    desc: "Every dish photo is captured live in the kitchen — no stock images, no bait-and-switch.",
    image: { src: u("photo-1476124369491-e688486ca310", 900), alt: "Live food photography" },
  },
  {
    title: "Local cloud kitchens",
    desc: "Support neighbourhood home kitchens with honest pricing and direct relationships.",
    image: { src: u("photo-1559339352-11d035aa65de", 900), alt: "Welcoming kitchen" },
  },
  {
    title: "Browse by kitchen code",
    desc: "Your favourite kitchen shares a simple code — find their menu in seconds.",
    image: { src: u("photo-1414235077428-338989a2e8c0", 900), alt: "Fine dining spread" },
  },
];

export const heroParallaxImages = {
  back: {
    src: u("photo-1556910103-1c02745aae4d", 1400),
    alt: "Chef cooking in professional kitchen",
    speed: 0.22,
  },
  mid: {
    src: u("photo-1414235077428-338989a2e8c0", 1000),
    alt: "Fine dining spread",
    speed: 0.4,
  },
  front: {
    src: u("photo-1565958011703-398f087be584", 900),
    alt: "Gourmet burger close-up",
    speed: 0.58,
  },
  accent: {
    src: u("photo-1544025162-d76694265947", 600),
    alt: "BBQ ribs platter",
    speed: 0.75,
  },
};

export const features = [
  {
    title: "WhatsApp Order Hub",
    desc: "Turn chat messages into structured orders. Confirm drafts in one tap.",
    image: { src: u("photo-1523474253046-061af715f927", 800), alt: "WhatsApp orders" },
  },
  {
    title: "Live-Capture Menu",
    desc: "Hero dish photos are captured live so customers trust what they order.",
    image: { src: u("photo-1563379927098-05c457674dd8", 800), alt: "Live wok cooking" },
  },
  {
    title: "Order Lifecycle",
    desc: "Track every order from received to delivered with status updates.",
    image: { src: u("photo-1555396273-367ea4eb4db5", 800), alt: "Kitchen service" },
  },
  {
    title: "Owner Dashboard",
    desc: "Manage kitchens, menus, orders, and customer menu links in one portal.",
    image: { src: u("photo-1552566626-c96b1358752f", 800), alt: "Commercial kitchen" },
  },
];

export const images = {
  hero: heroParallaxImages.back,
  heroSecondary: heroParallaxImages.mid,
  menu: { src: u("photo-1546069901-ba9599a7e63c", 800), alt: "Healthy meal bowls" },
  sushi: { src: u("photo-1579584425555-c3ce17fd1871", 800), alt: "Sushi platter" },
  tacos: { src: u("photo-1565299585323-38d3a815a438", 800), alt: "Street tacos" },
  steak: { src: u("photo-1544025162-d76694265947", 800), alt: "BBQ platter" },
  analytics: { src: u("photo-1517248135467-4c7edcad34c4", 800), alt: "Restaurant atmosphere" },
  onboardRegister: { src: u("photo-1574484284002-952d92456976", 700), alt: "Kitchen team" },
  onboardMenu: { src: u("photo-1626645736296-f996a903369f", 700), alt: "Cloud kitchen prep" },
  onboardWhatsapp: { src: u("photo-1523474253046-061af715f927", 700), alt: "WhatsApp orders" },
  contact: { src: u("photo-1559339352-11d035aa65de", 1000), alt: "Welcoming kitchen" },
  login: { src: u("photo-1556911220-e15b29be8c8f", 1200), alt: "Kitchen owner" },
  customers: { src: u("photo-1493770348163-869783f6a188", 1200), alt: "Brunch for customers" },
  owners: { src: u("photo-1552566626-c96b1358752f", 900), alt: "Commercial kitchen" },
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
      "Top dishes & peak-hour insights",
      "Customer CRM & repeat-rate tracking",
      "Churn win-back customer list",
      "WhatsApp marketing (coming soon)",
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
  ],
  customer: [
    {
      q: "How do I find a kitchen?",
      a: "Open customer.kitchCU.in, enter a kitchen code (e.g. CKPNQ001) from your home chef, or use Nearby with your location to discover cloud kitchens sorted by distance.",
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

/** Sample dish hero URLs (same as scripts/demo_data.py — for add-dish hints) */
export const sampleDishImages = {
  paneerTikka: u("photo-1563379927098-05c457674dd8", 900),
  biryani: u("photo-1585937421612-70a008592f82", 900),
  dosa: u("photo-1630385930673-614492270638", 900),
  butterChicken: u("photo-1603894584373-5e6e4bcb1d5c", 900),
  lassi: u("photo-1626074353815-4aa7c2609e59", 900),
  gulabJamun: u("photo-1571875250683-875e8d8e8c8e", 900),
  thali: u("photo-1606491956689-2ea8660f9640", 900),
  pavBhaji: u("photo-1596797038530-2c107229654b", 900),
} as const;
