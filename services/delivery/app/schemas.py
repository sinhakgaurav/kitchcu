"""Delivery domain — fee quotes, tracking (F27-F31, F29).

Fee rule (evaluated per kitchen, in order):
1. `distance_km > max_delivery_radius_km` -> `status="out_of_range"`, fee `0` — kitchen
   does not deliver this far; the customer must choose pickup or another kitchen.
2. `distance_km <= free_delivery_radius_km` -> within free radius, fee `0`.
3. Otherwise -> chargeable distance is `ceil(distance_km - free_delivery_radius_km)` whole
   km, fee = `delivery_fee_flat_beyond + chargeable_km * delivery_fee_per_km`.
4. If the kitchen has `min_order_for_free_delivery` set and `subtotal` meets/exceeds it,
   any non-zero fee computed above is waived back to `0`.

Every quote is persisted (`ckac_delivery.delivery_quotes`) and an audit `breakdown` of
which rule applied is returned alongside the fee, so owners/customers can see exactly why
a fee was (or wasn't) charged.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DeliveryQuote
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher


class DeliveryQuoteRequest(BaseModel):
    """Request a delivery fee quote for a kitchen + customer location before checkout."""

    kitchen_id: uuid.UUID = Field(
        ..., description="UUID of the active kitchen to quote delivery for.", examples=["8f14e45f-ceea-467e-9f1c-1234567890ab"]
    )
    latitude: float = Field(..., ge=-90, le=90, description="Customer's delivery destination latitude.")
    longitude: float = Field(..., ge=-180, le=180, description="Customer's delivery destination longitude.")
    subtotal: float = Field(
        default=0, ge=0, description="Cart subtotal in INR — used to evaluate the kitchen's minimum-order-for-free-delivery rule.", examples=[350.0]
    )


class DeliveryQuoteResponse(BaseModel):
    """Computed delivery fee + full rule breakdown for a kitchen/location/subtotal combination."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen this quote was computed for.")
    distance_km: float = Field(..., description="Straight-line distance from kitchen to customer, in km (PostGIS geography distance).", examples=[3.4])
    fee: float = Field(..., description="Quoted delivery fee in INR. `0` when within the free radius, out of range, or waived by a minimum-order rule.", examples=[20.0])
    status: str = Field(
        ..., description="'ok' — deliverable, fee as quoted. 'out_of_range' — beyond the kitchen's max delivery radius; fee is always `0` and delivery is not offered.", examples=["ok", "out_of_range"]
    )
    within_free_radius: bool = Field(..., description="Whether `distance_km` is within the kitchen's free-delivery radius.")
    free_delivery_radius_km: float = Field(..., description="Kitchen's configured free-delivery radius, in km.")
    max_delivery_radius_km: float = Field(..., description="Kitchen's configured maximum delivery radius, in km. Beyond this, `status` is `out_of_range`.")
    breakdown: dict = Field(
        ...,
        description="Audit of which fee rule applied, e.g. `{'rule': 'within_free_radius'}`, "
        "`{'rule': 'per_km_beyond_free', 'chargeable_km': ..., 'fee_per_km': ..., 'flat_beyond': ...}`, "
        "`{'rule': 'min_order_free_delivery', ...}`, or `{'reason': 'beyond_max_radius', ...}`.",
    )
    quote_id: uuid.UUID | None = Field(default=None, description="Persisted quote UUID (`ckac_delivery.delivery_quotes`), for audit/analytics.")


class TrackingResponse(BaseModel):
    """Public, token-authenticated order tracking view — no login required.

    Deliberately minimal: exposes only what a customer following a shared tracking
    link needs (status, ETA, distance), never customer PII belonging to *other*
    orders and never kitchen-internal data.
    """

    tracking_token: str = Field(..., description="The opaque tracking token used to fetch this view.")
    order_id: uuid.UUID = Field(..., description="Tracked order's UUID.")
    order_code: str = Field(..., description="Human-facing order code.", examples=["CKPNQ001-BILL-20260712-0042"])
    kitchen_id: uuid.UUID = Field(..., description="Kitchen UUID fulfilling the order.")
    kitchen_name: str | None = Field(default=None, description="Kitchen display name, if available.")
    status: str = Field(
        ..., description="Current order status.", examples=["received", "accepted", "preparing", "ready", "out_for_delivery", "delivered", "cancelled"]
    )
    delivery_type: str = Field(..., description="'pickup' or 'delivery'.")
    distance_km: float | None = Field(default=None, description="Distance from kitchen to customer, in km, when `delivery_type` is 'delivery'.")
    delivery_fee: float = Field(..., description="Delivery fee charged on this order, in INR.")
    estimated_ready_at: datetime | None = Field(default=None, description="Predicted ready time, UTC.")
    tracking_notify_interval_min: int = Field(
        ..., description="Kitchen-configured interval (minutes) at which the notification service sends WhatsApp tracking updates for this order."
    )
    updated_at: datetime | None = Field(default=None, description="Timestamp of the order's last status update, UTC.")


def _compute_fee(
    *,
    distance_km: float,
    free_km: float,
    max_km: float,
    fee_per_km: float,
    flat_beyond: float,
    subtotal: float,
    min_order_free: float | None,
) -> tuple[str, float, bool, dict]:
    if distance_km > max_km:
        return (
            "out_of_range",
            0.0,
            False,
            {"reason": "beyond_max_radius", "max_delivery_radius_km": max_km},
        )

    within_free = distance_km <= free_km
    if within_free:
        fee = 0.0
        breakdown = {"rule": "within_free_radius"}
    else:
        chargeable_km = math.ceil(distance_km - free_km)
        fee = round(flat_beyond + chargeable_km * fee_per_km, 2)
        breakdown = {
            "rule": "per_km_beyond_free",
            "chargeable_km": chargeable_km,
            "fee_per_km": fee_per_km,
            "flat_beyond": flat_beyond,
        }

    if min_order_free is not None and subtotal >= float(min_order_free) and fee > 0:
        fee = 0.0
        breakdown = {
            "rule": "min_order_free_delivery",
            "min_order_for_free_delivery": float(min_order_free),
            "subtotal": subtotal,
        }

    return "ok", fee, within_free, breakdown


async def quote_delivery(
    session: AsyncSession,
    body: DeliveryQuoteRequest,
    publisher: EventPublisher | None = None,
) -> DeliveryQuoteResponse:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    free_delivery_radius_km,
                    max_delivery_radius_km,
                    COALESCE(delivery_fee_per_km, 10) AS delivery_fee_per_km,
                    COALESCE(delivery_fee_flat_beyond, 0) AS delivery_fee_flat_beyond,
                    min_order_for_free_delivery,
                    ST_Distance(
                        location,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                    ) / 1000.0 AS distance_km
                FROM ckac_identity.kitchens
                WHERE id = :kid AND status = 'active'
                LIMIT 1
                """
            ),
            {"kid": body.kitchen_id, "lat": body.latitude, "lng": body.longitude},
        )
    ).mappings().one_or_none()

    if row is None:
        raise ValueError("Kitchen not found or inactive")

    distance_km = round(float(row["distance_km"]), 2)
    free_km = float(row["free_delivery_radius_km"])
    max_km = float(row["max_delivery_radius_km"])
    status, fee, within_free, breakdown = _compute_fee(
        distance_km=distance_km,
        free_km=free_km,
        max_km=max_km,
        fee_per_km=float(row["delivery_fee_per_km"]),
        flat_beyond=float(row["delivery_fee_flat_beyond"]),
        subtotal=body.subtotal,
        min_order_free=(
            float(row["min_order_for_free_delivery"])
            if row["min_order_for_free_delivery"] is not None
            else None
        ),
    )

    quote = DeliveryQuote(
        kitchen_id=body.kitchen_id,
        customer_lat=body.latitude,
        customer_lng=body.longitude,
        distance_km=distance_km,
        fee=fee,
        status=status,
        breakdown=breakdown,
    )
    session.add(quote)
    await session.flush()

    if publisher is not None:
        event = publisher.build(
            event_type="delivery.fee_quoted",
            aggregate_type="quote",
            aggregate_id=str(quote.id),
            producer="delivery-service",
            payload={
                "kitchen_id": str(body.kitchen_id),
                "distance_km": distance_km,
                "fee": fee,
                "status": status,
            },
        )
        await publisher.publish(stream_key("delivery", "quote"), event, session=session)

    return DeliveryQuoteResponse(
        kitchen_id=body.kitchen_id,
        distance_km=distance_km,
        fee=fee,
        status=status,
        within_free_radius=within_free,
        free_delivery_radius_km=free_km,
        max_delivery_radius_km=max_km,
        breakdown=breakdown,
        quote_id=quote.id,
    )


async def track_by_token(session: AsyncSession, token: str) -> TrackingResponse:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    o.id AS order_id,
                    o.order_code,
                    o.kitchen_id,
                    o.status,
                    o.delivery_type,
                    o.distance_km,
                    o.delivery_fee,
                    o.estimated_ready_at,
                    o.updated_at,
                    o.tracking_token,
                    k.name AS kitchen_name,
                    COALESCE(k.tracking_notify_interval_min, 5) AS tracking_notify_interval_min
                FROM ckac_orders.orders o
                LEFT JOIN ckac_identity.kitchens k ON k.id = o.kitchen_id
                WHERE o.tracking_token = :token
                LIMIT 1
                """
            ),
            {"token": token},
        )
    ).mappings().one_or_none()
    if row is None:
        raise ValueError("Tracking link not found")

    return TrackingResponse(
        tracking_token=row["tracking_token"],
        order_id=row["order_id"],
        order_code=row["order_code"],
        kitchen_id=row["kitchen_id"],
        kitchen_name=row["kitchen_name"],
        status=row["status"],
        delivery_type=row["delivery_type"],
        distance_km=float(row["distance_km"]) if row["distance_km"] is not None else None,
        delivery_fee=float(row["delivery_fee"]),
        estimated_ready_at=row["estimated_ready_at"],
        tracking_notify_interval_min=int(row["tracking_notify_interval_min"]),
        updated_at=row["updated_at"],
    )
