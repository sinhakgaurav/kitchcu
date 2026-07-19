"""Porter quote + booking helpers for order delivery_mode=platform."""

from __future__ import annotations

import logging
import os
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def quote_porter_fee(
    *,
    pickup_lat: float,
    pickup_lng: float,
    drop_lat: float,
    drop_lng: float,
    distance_km: float,
    session: AsyncSession | None = None,
) -> float | None:
    """Best-effort Porter quote; returns fee INR or None (caller uses mock formula)."""
    from ckac_common.platform_config import third_party_integrations_enabled

    if not await third_party_integrations_enabled(session, default=False):
        return None
    api_key = (os.getenv("PORTER_API_KEY") or "").strip()
    if not api_key:
        return None
    import httpx

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
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
            )
            res.raise_for_status()
            body = res.json()
            if not isinstance(body, dict):
                return None
            for key in ("fare", "amount", "total_fare", "delivery_charge", "price"):
                val = body.get(key)
                if isinstance(val, (int, float)):
                    return round(float(val), 2)
            vehicles = body.get("vehicles") or body.get("vehicle_fare_list") or []
            if isinstance(vehicles, list) and vehicles and isinstance(vehicles[0], dict):
                for key in ("fare", "amount", "total_fare", "price"):
                    val = vehicles[0].get(key)
                    if isinstance(val, (int, float)):
                        return round(float(val), 2)
            _ = distance_km  # reserved for future distance sanity checks
            return None
    except Exception as exc:
        logger.warning("Porter quote failed: %s", exc)
        return None


async def quote_and_book_porter(
    session: AsyncSession,
    order,
    *,
    pickup_time=None,
) -> dict | None:
    """Book Porter when configured; returns {fee, job_id} or None.

    ``pickup_time`` (datetime) is sent when present so the partner arrives near food-ready.
    When ``third_party_integrations`` is OFF, returns a simulated booking (no HTTP).
    """
    from ckac_common.platform_config import third_party_integrations_enabled

    if (os.getenv("DELIVERY_PARTNER") or "").strip().lower() != "porter":
        return None
    if not await third_party_integrations_enabled(session, default=False):
        return {
            "fee": None,
            "job_id": f"sim-{uuid.uuid4()}",
            "partner": "porter_simulated",
        }
    if not (os.getenv("PORTER_API_KEY") or "").strip():
        return None

    row = (
        await session.execute(
            text(
                """
                SELECT
                    ST_Y(location::geometry) AS kitchen_lat,
                    ST_X(location::geometry) AS kitchen_lng,
                    address_line
                FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1
                """
            ),
            {"kid": order.kitchen_id},
        )
    ).mappings().one_or_none()
    if not row or order.customer_latitude is None or order.customer_longitude is None:
        return None

    # Import delivery partner adapter (same package path unavailable cross-service).
    # Inline thin call mirroring delivery platform_courier.book_porter_delivery.
    import httpx

    api_key = os.environ["PORTER_API_KEY"].strip()
    base = (os.getenv("PORTER_BASE_URL") or "https://api.porter.in").rstrip("/")
    path = os.getenv("PORTER_ORDER_PATH") or "/v1/orders"
    url = f"{base}{path if path.startswith('/') else '/' + path}"
    phone = (order.customer_phone or "+919999999999").lstrip("+")
    payload = {
        "request_id": str(order.id),
        "pickup_details": {
            "address": {
                "street_address1": row["address_line"] or "Kitchen",
                "city": "India",
                "country": "India",
                "lat": float(row["kitchen_lat"]),
                "lng": float(row["kitchen_lng"]),
                "contact_details": {"name": "Kitchen", "phone_number": "+919999999999"},
            }
        },
        "drop_details": {
            "address": {
                "street_address1": "Customer",
                "city": "India",
                "country": "India",
                "lat": float(order.customer_latitude),
                "lng": float(order.customer_longitude),
                "contact_details": {
                    "name": order.customer_name or "Customer",
                    "phone_number": f"+{phone}" if not str(order.customer_phone or "").startswith("+") else order.customer_phone,
                },
            }
        },
    }
    if pickup_time is not None:
        try:
            payload["pickup_time"] = pickup_time.isoformat()
        except Exception:
            pass
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
            )
            res.raise_for_status()
            body = res.json()
            job_id = None
            fee = None
            if isinstance(body, dict):
                job_id = body.get("order_id") or body.get("id") or body.get("crn")
                fare = body.get("fare") or body.get("amount")
                if isinstance(fare, (int, float)):
                    fee = float(fare)
            return {
                "fee": fee,
                "job_id": str(job_id) if job_id else str(uuid.uuid4()),
                "partner": "porter",
            }
    except Exception as exc:
        logger.warning("Porter book from order failed: %s", exc)
        return None
