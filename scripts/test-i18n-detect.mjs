/** Node smoke test for India location → language mapping (no browser). */
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const regions = JSON.parse(
  readFileSync(join(root, "apps/website/src/i18n/regions.json"), "utf8"),
);

function localeFromCoordinates(lat, lng) {
  if (lat < 6.5 || lat > 37.5 || lng < 67.5 || lng > 97.5) return null;
  for (const box of regions) {
    if (lat >= box.s && lat <= box.n && lng >= box.w && lng <= box.e) return box.lang;
  }
  return "hi";
}

function localeFromBrowserTag(tag) {
  if (!tag) return null;
  const primary = tag.trim().toLowerCase().split("-")[0];
  const known = new Set(["en", "hi", "mr", "ta", "te", "kn", "ml", "bn", "gu", "pa"]);
  return known.has(primary) ? primary : null;
}

const cases = [
  [18.52, 73.85, "mr"], // Pune
  [13.08, 80.27, "ta"], // Chennai
  [12.97, 77.59, "kn"], // Bengaluru
  [28.61, 77.21, "hi"], // Delhi
  [22.57, 88.36, "bn"], // Kolkata
  [23.02, 72.57, "gu"], // Ahmedabad
  [51.5, -0.12, null], // London
];

let failed = 0;
for (const [lat, lng, expect] of cases) {
  const got = localeFromCoordinates(lat, lng);
  if (got !== expect) {
    console.error(`FAIL coords ${lat},${lng}: got ${got}, want ${expect}`);
    failed += 1;
  }
}

if (localeFromBrowserTag("hi-IN") !== "hi") {
  console.error("FAIL browser hi-IN");
  failed += 1;
}
if (localeFromBrowserTag("en-US") !== "en") {
  console.error("FAIL browser en-US");
  failed += 1;
}

if (failed) {
  console.error(`${failed} assertion(s) failed`);
  process.exit(1);
}
console.log(`OK: ${cases.length} geo + browser locale checks`);
