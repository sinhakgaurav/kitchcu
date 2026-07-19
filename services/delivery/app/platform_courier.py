"""Pluggable local delivery partner quote (Porter / mock / http).

``DELIVERY_PARTNER``:
- ``mock`` (default) — transparent base + per-km
- ``porter`` — Porter Partner quote API (https://api.porter.in)
- ``http`` — generic POST ``DELIVERY_PARTNER_QUOTE_URL`` with ``{distance_km,...}``

Env:
- ``PORTER_API_KEY``, ``PORTER_BASE_URL`` (default https://api.porter.in)
- ``PORTER_QUOTE_PATH`` (default /v1/get_quote)
- ``DELIVERY_PARTNER_BASE_FEE``, ``DELIVERY_PARTNER_PER_KM``
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _mock_fee(distance_km: float) -> dict[str, Any]:
    base = float(os.getenv("DELIVERY_PARTNER_BASE_FEE", "25"))
    per_km = float(os.getenv("DELIVERY_PARTNER_PER_KM", "12"))
    fee = round(base + math.ceil(max(0.0, distance_km)) * per_km, 2)
    return {
        "fee": fee,
        "currency": "INR",
        "partner": "kitchcu_local_mock",
        "breakdown": {
            "base": base,
            "per_km": per_km,
            "chargeable_km": math.ceil(max(0.0, distance_km)),
            "distance_km": distance_km,
        },
    }


def _extract_porter_fee(body: dict[str, Any]) -> float | None:
    """Best-effort parse of Porter quote payloads (enterprise shapes vary)."""
    for key in ("fee", "amount", "total", "fare", "estimated_fare"):
        if key in body and body[key] is not None:
            val = body[key]
            if isinstance(val, (int, float, str)):
                try:
                    return float(val)
                except ValueError:
                    pass
            if isinstance(val, dict):
                for nested in ("amount", "total", "minor_amount", "value"):
                    if nested in val and val[nested] is not None:
                        try:
                            amt = float(val[nested])
                            # minor_amount often in paise
                            if nested == "minor_amount" and amt > 1000:
                                return round(amt / 100.0, 2)
                            return amt
                        except ValueError:
                            pass
    fare = body.get("fare_details") or body.get("vehicle_fare") or {}
    if isinstance(fare, dict):
        for nested in ("total", "amount", "fare"):
            if nested in fare and fare[nested] is not None:
                try:
                    return float(fare[nested])
                except ValueError:
                    pass
    vehicles = body.get("vehicles") or body.get("vehicle_fare_list") or []
    if isinstance(vehicles, list) and vehicles:
        first = vehicles[0]
        if isinstance(first, dict):
            return _extract_porter_fee(first)
    return None


def quote_porter_delivery_fee(
    *,
    distance_km: float,
    pickup_lat: float | None,
    pickup_lng: float | None,
    drop_lat: float | None,
    drop_lng: float | None,
) -> dict[str, Any] | None:
    from ckac_common.platform_config import third_party_integrations_enabled_sync

    if not third_party_integrations_enabled_sync(default=False):
        return None
    api_key = (os.getenv("PORTER_API_KEY") or "").strip()
    if not api_key:
        return None
    if None in (pickup_lat, pickup_lng, drop_lat, drop_lng):
        return None

    base = (os.getenv("PORTER_BASE_URL") or "https://api.porter.in").rstrip("/")
    path = os.getenv("PORTER_QUOTE_PATH") or "/v1/get_quote"
    url = f"{base}{path if path.startswith('/') else '/' + path}"
    payload = {
        "pickup_details": {"lat": float(pickup_lat), "lng": float(pickup_lng)},
        "drop_details": {"lat": float(drop_lat), "lng": float(drop_lng)},
        "customer": {
            "name": "kitchCU",
            "mobile": {"number": "9999999999", "country_code": "+91"},
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=8.0) as client:
            res = client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            body = res.json()
            fee = _extract_porter_fee(body if isinstance(body, dict) else {})
            if fee is None:
                logger.warning("Porter quote missing fee field — falling back")
                return None
            return {
                "fee": round(float(fee), 2),
                "currency": "INR",
                "partner": "porter",
                "breakdown": {
                    "distance_km": distance_km,
                    "raw_keys": list(body.keys()) if isinstance(body, dict) else [],
                },
            }
    except Exception as exc:
        logger.warning("Porter quote failed: %s", exc)
        return None


def book_porter_delivery(
    *,
    request_id: str,
    pickup_lat: float,
    pickup_lng: float,
    drop_lat: float,
    drop_lng: float,
    pickup_address: str | None = None,
    drop_address: str | None = None,
    customer_name: str = "Customer",
    customer_phone: str = "+919999999999",
) -> dict[str, Any] | None:
    """Create a Porter job when owner chooses platform courier. Best-effort."""
    from ckac_common.platform_config import third_party_integrations_enabled_sync

    if (os.getenv("DELIVERY_PARTNER") or "mock").strip().lower() != "porter":
        return None
    if not third_party_integrations_enabled_sync(default=False):
        return {
            "partner": "porter_simulated",
            "job_id": f"sim-{request_id}",
            "raw": {"simulated": True},
        }
    api_key = (os.getenv("PORTER_API_KEY") or "").strip()
    if not api_key:
        return None

    base = (os.getenv("PORTER_BASE_URL") or "https://api.porter.in").rstrip("/")
    path = os.getenv("PORTER_ORDER_PATH") or "/v1/orders"
    url = f"{base}{path if path.startswith('/') else '/' + path}"
    phone = customer_phone.lstrip("+")
    if phone.startswith("91") and len(phone) > 10:
        phone = phone[2:]
    payload = {
        "request_id": request_id,
        "pickup_details": {
            "address": {
                "street_address1": pickup_address or "Kitchen",
                "city": "India",
                "country": "India",
                "lat": pickup_lat,
                "lng": pickup_lng,
                "contact_details": {"name": "Kitchen", "phone_number": "+919999999999"},
            }
        },
        "drop_details": {
            "address": {
                "street_address1": drop_address or "Customer",
                "city": "India",
                "country": "India",
                "lat": drop_lat,
                "lng": drop_lng,
                "contact_details": {
                    "name": customer_name,
                    "phone_number": f"+91{phone[-10:]}" if len(phone) >= 10 else customer_phone,
                },
            }
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            res = client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            body = res.json()
            job_id = None
            if isinstance(body, dict):
                job_id = body.get("order_id") or body.get("id") or body.get("crn")
            return {"partner": "porter", "job_id": str(job_id) if job_id else None, "raw": body}
    except Exception as exc:
        logger.warning("Porter book failed: %s", exc)
        return None


def quote_platform_delivery_fee(
    distance_km: float,
    *,
    pickup_lat: float | None = None,
    pickup_lng: float | None = None,
    drop_lat: float | None = None,
    drop_lng: float | None = None,
    porter_enabled: bool = True,
) -> dict[str, Any]:
    """Return ``{fee, currency, partner, breakdown}`` for a local courier job."""
    from ckac_common.platform_config import third_party_integrations_enabled_sync

    partner = (os.getenv("DELIVERY_PARTNER") or "mock").strip().lower()
    distance_km = max(0.0, float(distance_km))
    tp_on = third_party_integrations_enabled_sync(default=False)

    if partner == "http" and not tp_on:
        # Generic partner HTTP is also third-party — fall through to mock.
        partner = "mock"

    if partner == "porter" and porter_enabled and tp_on:
        quoted = quote_porter_delivery_fee(
            distance_km=distance_km,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            drop_lat=drop_lat,
            drop_lng=drop_lng,
        )
        if quoted:
            return quoted

    if partner == "http":
        url = os.getenv("DELIVERY_PARTNER_QUOTE_URL", "").strip()
        if url:
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.post(
                        url,
                        json={
                            "distance_km": distance_km,
                            "pickup_lat": pickup_lat,
                            "pickup_lng": pickup_lng,
                            "drop_lat": drop_lat,
                            "drop_lng": drop_lng,
                        },
                    )
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
                pass

    return _mock_fee(distance_km)
