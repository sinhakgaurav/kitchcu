"""Pluggable local delivery partner quote (platform-integrated courier).

Dev/default is a transparent distance formula. Point `DELIVERY_PARTNER=http`
+ `DELIVERY_PARTNER_QUOTE_URL` at a real partner when available.
"""

from __future__ import annotations

import math
import os

import httpx


def quote_platform_delivery_fee(distance_km: float) -> dict:
    """Return ``{fee, currency, partner, breakdown}`` for a local courier job."""
    partner = (os.getenv("DELIVERY_PARTNER") or "mock").strip().lower()
    distance_km = max(0.0, float(distance_km))

    if partner == "http":
        url = os.getenv("DELIVERY_PARTNER_QUOTE_URL", "").strip()
        if url:
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.post(url, json={"distance_km": distance_km})
                    res.raise_for_status()
                    body = res.json()
                    fee = float(body["fee"])
                    return {
                        "fee": round(fee, 2),
                        "currency": body.get("currency", "INR"),
                        "partner": body.get("partner", "http"),
                        "breakdown": body.get("breakdown", {"distance_km": distance_km}),
                    }
            except Exception:
                pass  # fall through to mock

    base = float(os.getenv("DELIVERY_PARTNER_BASE_FEE", "25"))
    per_km = float(os.getenv("DELIVERY_PARTNER_PER_KM", "12"))
    fee = round(base + math.ceil(distance_km) * per_km, 2)
    return {
        "fee": fee,
        "currency": "INR",
        "partner": "kitchcu_local_mock",
        "breakdown": {
            "base": base,
            "per_km": per_km,
            "chargeable_km": math.ceil(distance_km),
            "distance_km": distance_km,
        },
    }
