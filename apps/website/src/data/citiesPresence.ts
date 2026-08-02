/** Curated platform presence — marketing + discovery. Not raw DB distinct cities. */

export type CityPresenceStatus = "live" | "coming_soon";

export type CityPresence = {
  slug: string;
  name: string;
  state: string;
  code: string;
  status: CityPresenceStatus;
  center: { lat: number; lng: number };
  sortOrder: number;
  featured?: boolean;
};

/**
 * Cities we operate in or are expanding to.
 * Kitchen codes use the same 3-letter codes as identity CITY_CODES.
 */
export const CITIES_PRESENCE: CityPresence[] = [
  {
    slug: "pune",
    name: "Pune",
    state: "Maharashtra",
    code: "PNQ",
    status: "live",
    center: { lat: 18.5204, lng: 73.8567 },
    sortOrder: 1,
    featured: true,
  },
  {
    slug: "mumbai",
    name: "Mumbai",
    state: "Maharashtra",
    code: "BOM",
    status: "live",
    center: { lat: 19.076, lng: 72.8777 },
    sortOrder: 2,
    featured: true,
  },
  {
    slug: "delhi",
    name: "Delhi",
    state: "Delhi",
    code: "DEL",
    status: "live",
    center: { lat: 28.6139, lng: 77.209 },
    sortOrder: 3,
    featured: true,
  },
  {
    slug: "gurgaon",
    name: "Gurugram",
    state: "Haryana",
    code: "GGN",
    status: "live",
    center: { lat: 28.4595, lng: 77.0266 },
    sortOrder: 4,
    featured: true,
  },
  {
    slug: "noida",
    name: "Noida",
    state: "Uttar Pradesh",
    code: "NOI",
    status: "live",
    center: { lat: 28.5355, lng: 77.391 },
    sortOrder: 5,
    featured: true,
  },
  {
    slug: "lucknow",
    name: "Lucknow",
    state: "Uttar Pradesh",
    code: "LKO",
    status: "live",
    center: { lat: 26.8467, lng: 80.9462 },
    sortOrder: 6,
  },
  {
    slug: "kanpur",
    name: "Kanpur",
    state: "Uttar Pradesh",
    code: "KNU",
    status: "live",
    center: { lat: 26.4499, lng: 80.3319 },
    sortOrder: 7,
  },
  {
    slug: "prayagraj",
    name: "Prayagraj",
    state: "Uttar Pradesh",
    code: "IXD",
    status: "live",
    center: { lat: 25.4358, lng: 81.8463 },
    sortOrder: 8,
  },
  {
    slug: "varanasi",
    name: "Varanasi",
    state: "Uttar Pradesh",
    code: "VNS",
    status: "live",
    center: { lat: 25.3176, lng: 82.9739 },
    sortOrder: 9,
  },
  {
    slug: "jhansi",
    name: "Jhansi",
    state: "Uttar Pradesh",
    code: "JHS",
    status: "live",
    center: { lat: 25.4484, lng: 78.5685 },
    sortOrder: 10,
  },
  {
    slug: "dehradun",
    name: "Dehradun",
    state: "Uttarakhand",
    code: "DED",
    status: "live",
    center: { lat: 30.3165, lng: 78.0322 },
    sortOrder: 11,
  },
  {
    slug: "bengaluru",
    name: "Bengaluru",
    state: "Karnataka",
    code: "BLR",
    status: "coming_soon",
    center: { lat: 12.9716, lng: 77.5946 },
    sortOrder: 12,
  },
  {
    slug: "hyderabad",
    name: "Hyderabad",
    state: "Telangana",
    code: "HYD",
    status: "coming_soon",
    center: { lat: 17.385, lng: 78.4867 },
    sortOrder: 13,
  },
  {
    slug: "chennai",
    name: "Chennai",
    state: "Tamil Nadu",
    code: "MAA",
    status: "coming_soon",
    center: { lat: 13.0827, lng: 80.2707 },
    sortOrder: 14,
  },
  {
    slug: "kolkata",
    name: "Kolkata",
    state: "West Bengal",
    code: "CCU",
    status: "coming_soon",
    center: { lat: 22.5726, lng: 88.3639 },
    sortOrder: 15,
  },
];

export function liveCities(): CityPresence[] {
  return CITIES_PRESENCE.filter((c) => c.status === "live").sort(
    (a, b) => a.sortOrder - b.sortOrder,
  );
}

export function featuredCities(): CityPresence[] {
  return CITIES_PRESENCE.filter((c) => c.featured).sort((a, b) => a.sortOrder - b.sortOrder);
}
