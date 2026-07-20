#!/usr/bin/env python3
"""Assert India region boxes map city coordinates to expected languages.

Mirrors apps/website/src/i18n/regions.json + localeFromCoordinates
(first matching box wins; inside India with no box → hi).

Exit codes:
  0 — PASS
  1 — FAIL
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGIONS_PATH = ROOT / "apps" / "website" / "src" / "i18n" / "regions.json"

# City samples required by product gate
CASES: list[tuple[str, float, float, str]] = [
    ("Pune", 18.52, 73.86, "mr"),
    ("Mumbai", 19.07, 72.87, "mr"),
    ("Kolhapur", 16.7, 74.2, "mr"),
    ("Delhi", 28.61, 77.20, "hi"),
    ("Bengaluru", 12.97, 77.59, "kn"),
    ("Chennai", 13.08, 80.27, "ta"),
    ("Hyderabad", 17.38, 78.48, "te"),
    ("Kochi", 9.93, 76.26, "ml"),
    ("Kolkata", 22.57, 88.36, "bn"),
    ("Amritsar", 31.63, 74.87, "pa"),
]


def locale_from_coordinates(regions: list[dict], lat: float, lng: float) -> str | None:
    if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float))):
        return None
    if lat < 6.5 or lat > 37.5 or lng < 67.5 or lng > 97.5:
        return None
    for box in regions:
        if lat >= box["s"] and lat <= box["n"] and lng >= box["w"] and lng <= box["e"]:
            return str(box["lang"])
    return "hi"


def main() -> int:
    if not REGIONS_PATH.is_file():
        print(f"FAIL: missing {REGIONS_PATH}")
        return 1
    try:
        regions = json.loads(REGIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot load regions.json: {exc}")
        return 1
    if not isinstance(regions, list) or not regions:
        print("FAIL: regions.json must be a non-empty array")
        return 1

    failed = False
    for name, lat, lng, expected in CASES:
        got = locale_from_coordinates(regions, lat, lng)
        status = "PASS" if got == expected else "FAIL"
        print(f"{name} ({lat}, {lng}): expected={expected} got={got} {status}")
        if got != expected:
            failed = True

    if failed:
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
