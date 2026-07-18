"""Delivery domain — fee quotes, payer modes, Porter, tracking (F27-F31).

Distance rules (product):
- **In range** (`distance ≤ max_delivery_radius_km`): kitchen bears **full** logistics cost
  (customer fee `0`) — self or Porter/platform.
- **Out of range**: still deliverable. If cart meets `min_order_for_free_delivery`,
  kitchen bears `delivery_subsidy_percent` of cost; else customer bears **full**.
"""

from __future__ import annotations

import math
import os
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cost_share import split_delivery_cost
from app.models import DeliveryQuote
from app.platform_courier import quote_platform_delivery_fee
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher


class DeliveryQuoteRequest(BaseModel):
    """Request a delivery fee quote for a kitchen + customer location before checkout."""

    kitchen_id: uuid.UUID = Field(
        ..., description="UUID of the active kitchen to quote delivery for."
    )
    latitude: float = Field(..., ge=-90, le=90, description="Customer destination latitude.")
    longitude: float = Field(..., ge=-180, le=180, description="Customer destination longitude.")
    subtotal: float = Field(
        default=0, ge=0, description="Cart subtotal in INR.", examples=[350.0]
    )


class DeliveryModeOption(BaseModel):
    mode: str = Field(..., description="'self' or 'platform' (Porter when configured).")
    payer: str = Field(..., description="'owner', 'customer', or 'shared'.")
    customer_fee: float = Field(..., description="INR charged to the customer at checkout.")
    owner_fee: float = Field(..., description="INR kitchen bears of logistics cost.")
    label: str
    description: str
    partner: str | None = Field(default=None, description="Courier partner id when mode=platform.")


class DeliveryQuoteResponse(BaseModel):
    kitchen_id: uuid.UUID
    distance_km: float
    in_range: bool = Field(..., description="True when distance ≤ kitchen max radius.")
    status: str = Field(
        ...,
        description="'ok' in-range (customer fee 0). 'extended' out-of-range but still deliverable.",
    )
    # Convenience: customer-facing fee for the default mode at checkout (in-range → 0).
    fee: float = Field(..., description="Default customer fee for checkout.")
    within_free_radius: bool
    free_delivery_radius_km: float
    max_delivery_radius_km: float
    modes: list[DeliveryModeOption]
    platform_fee: float = Field(..., description="Quoted platform courier fee.")
    kitchen_self_fee: float = Field(
        ..., description="Suggested fee if owner self-delivers (0 in-range; per-km out-of-range)."
    )
    breakdown: dict
    quote_id: uuid.UUID | None = None


class DeliveryFeeDenialRequest(BaseModel):
    """Customer denies a previously quoted delivery fee at checkout (F28)."""

    quote_id: uuid.UUID = Field(..., description="The `quote_id` returned by `POST /delivery/quote`.")
    subtotal: float = Field(default=0, ge=0, description="Cart subtotal at time of denial, in INR.")
    customer_phone: str | None = Field(
        default=None, description="Customer phone (E.164), so the owner can call back."
    )


class DeliveryFeeDenialResponse(BaseModel):
    acknowledged: bool = Field(..., description="Always true — owner has been alerted.")
    kitchen_id: uuid.UUID


class TrackingResponse(BaseModel):
    tracking_token: str
    order_id: uuid.UUID
    order_code: str
    kitchen_id: uuid.UUID
    kitchen_name: str | None = None
    status: str
    delivery_type: str
    delivery_mode: str | None = None
    delivery_payer: str | None = None
    distance_km: float | None = None
    delivery_fee: float
    owner_delivery_cost: float = 0
    estimated_ready_at: datetime | None = None
    tracking_notify_interval_min: int
    updated_at: datetime | None = None
    kitchen_latitude: float | None = None
    kitchen_longitude: float | None = None
    customer_latitude: float | None = None
    customer_longitude: float | None = None
    map_directions_url: str | None = None


def _gross_self_fee(
    *,
    distance_km: float,
    free_km: float,
    fee_per_km: float,
    flat_beyond: float,
) -> tuple[float, dict]:
    """Gross self-delivery logistics cost before cost-share."""
    chargeable_km = max(1, math.ceil(max(0.0, distance_km - free_km)))
    fee = round(flat_beyond + chargeable_km * fee_per_km, 2)
    return fee, {
        "chargeable_km": chargeable_km,
        "fee_per_km": fee_per_km,
        "flat_beyond": flat_beyond,
        "distance_km": distance_km,
    }


def build_mode_options(
    *,
    self_share: dict,
    platform_share: dict,
    partner_name: str,
) -> list[DeliveryModeOption]:
    self_desc = {
        "owner": "Kitchen delivers — in range, kitchen covers logistics (₹0 to you).",
        "customer": "Beyond kitchen range — you pay the full self-delivery fee.",
        "shared": (
            f"Beyond range — kitchen covers {self_share['subsidy_percent_applied']:.0f}% "
            f"(₹{self_share['owner_fee']:.0f}); you pay ₹{self_share['customer_fee']:.0f}."
        ),
    }
    plat_desc = {
        "owner": f"{partner_name} (~₹{platform_share['gross_fee']:.0f}) — kitchen pays in full.",
        "customer": f"{partner_name} (~₹{platform_share['gross_fee']:.0f}) — you pay in full.",
        "shared": (
            f"{partner_name} — kitchen covers {platform_share['subsidy_percent_applied']:.0f}% "
            f"(₹{platform_share['owner_fee']:.0f}); you pay ₹{platform_share['customer_fee']:.0f}."
        ),
    }
    return [
        DeliveryModeOption(
            mode="self",
            payer=self_share["payer"],
            customer_fee=float(self_share["customer_fee"]),
            owner_fee=float(self_share["owner_fee"]),
            label="Self delivery",
            description=self_desc.get(self_share["payer"], self_desc["customer"]),
            partner=None,
        ),
        DeliveryModeOption(
            mode="platform",
            payer=platform_share["payer"],
            customer_fee=float(platform_share["customer_fee"]),
            owner_fee=float(platform_share["owner_fee"]),
            label=f"{partner_name} courier",
            description=plat_desc.get(platform_share["payer"], plat_desc["customer"]),
            partner=partner_name.lower().replace(" ", "_"),
        ),
    ]


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
                    COALESCE(delivery_subsidy_percent, 50) AS delivery_subsidy_percent,
                    ST_Y(location::geometry) AS kitchen_lat,
                    ST_X(location::geometry) AS kitchen_lng,
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
    in_range = distance_km <= max_km
    within_free = distance_km <= free_km
    min_order = (
        float(row["min_order_for_free_delivery"])
        if row["min_order_for_free_delivery"] is not None
        else None
    )
    subsidy_pct = float(row["delivery_subsidy_percent"] or 50)

    try:
        from ckac_common.risk_config import is_risk_capability_enabled

        porter_flag = await is_risk_capability_enabled(
            session, "courier_porter_dunzo", default=False
        )
    except Exception:
        porter_flag = False

    # Porter partner calls require DELIVERY_PARTNER=porter + feature flag.
    partner_env = (os.getenv("DELIVERY_PARTNER") or "mock").strip().lower()
    use_porter = partner_env == "porter" and porter_flag

    platform = quote_platform_delivery_fee(
        distance_km,
        pickup_lat=float(row["kitchen_lat"]) if row["kitchen_lat"] is not None else None,
        pickup_lng=float(row["kitchen_lng"]) if row["kitchen_lng"] is not None else None,
        drop_lat=body.latitude,
        drop_lng=body.longitude,
        porter_enabled=use_porter,
    )
    platform_gross = float(platform["fee"])
    partner_label = "Porter" if platform.get("partner") == "porter" else "Platform"

    self_gross, self_gross_bd = _gross_self_fee(
        distance_km=distance_km,
        free_km=free_km,
        fee_per_km=float(row["delivery_fee_per_km"]),
        flat_beyond=float(row["delivery_fee_flat_beyond"]),
    )
    # In-range self: no partner invoice — customer ₹0, owner_fee ₹0 on self mode.
    self_share = split_delivery_cost(
        gross_fee=0.0 if in_range else self_gross,
        in_range=in_range,
        subtotal=body.subtotal,
        min_order_for_subsidy=min_order,
        subsidy_percent=subsidy_pct,
    )

    platform_share = split_delivery_cost(
        gross_fee=platform_gross,
        in_range=in_range,
        subtotal=body.subtotal,
        min_order_for_subsidy=min_order,
        subsidy_percent=subsidy_pct,
    )

    modes = build_mode_options(
        self_share=self_share,
        platform_share=platform_share,
        partner_name=partner_label,
    )
    default_customer_fee = modes[0].customer_fee
    status = "ok" if in_range else "extended"
    kitchen_self_fee = float(self_share["customer_fee"])
    breakdown = {
        "in_range": in_range,
        "within_free_radius": within_free,
        "self_gross": self_gross_bd,
        "self_share": self_share,
        "platform": platform,
        "platform_share": platform_share,
        "subsidy_percent": subsidy_pct,
        "min_order_for_subsidy": min_order,
    }

    quote = DeliveryQuote(
        kitchen_id=body.kitchen_id,
        customer_lat=body.latitude,
        customer_lng=body.longitude,
        distance_km=distance_km,
        fee=default_customer_fee,
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
                "fee": default_customer_fee,
                "status": status,
                "in_range": in_range,
                "partner": platform.get("partner"),
            },
        )
        await publisher.publish(stream_key("delivery", "quote"), event, session=session)

    return DeliveryQuoteResponse(
        kitchen_id=body.kitchen_id,
        distance_km=distance_km,
        in_range=in_range,
        status=status,
        fee=default_customer_fee,
        within_free_radius=within_free,
        free_delivery_radius_km=free_km,
        max_delivery_radius_km=max_km,
        modes=modes,
        platform_fee=platform_gross,
        kitchen_self_fee=kitchen_self_fee,
        breakdown=breakdown,
        quote_id=quote.id,
    )


async def deny_delivery_fee(
    session: AsyncSession,
    body: DeliveryFeeDenialRequest,
    publisher: EventPublisher | None = None,
) -> DeliveryFeeDenialResponse:
    """F28 deny path: 'If denied -> owner notified -> cancel OR deliver free if order >= min_amount'.

    The free-delivery-above-minimum waiver is already applied automatically inside the
    quote itself (see `_kitchen_self_fee` / `quote_delivery`), so a quote only reaches this
    endpoint when a *real* fee was denied. No order exists yet at quote time — the customer
    never proceeded to checkout — so there is nothing to cancel; this just makes the deny an
    actionable, owner-visible event instead of a silently lost sale.
    """
    quote = (
        await session.execute(select(DeliveryQuote).where(DeliveryQuote.id == body.quote_id))
    ).scalar_one_or_none()
    if quote is None:
        raise ValueError("Delivery quote not found")

    if publisher is not None:
        event = publisher.build(
            event_type="delivery.fee_denied",
            aggregate_type="quote",
            aggregate_id=str(quote.id),
            producer="delivery-service",
            payload={
                "kitchen_id": str(quote.kitchen_id),
                "distance_km": float(quote.distance_km),
                "fee": float(quote.fee),
                "customer_phone": body.customer_phone,
            },
        )
        await publisher.publish(stream_key("delivery", "quote"), event, session=session)

    from app.notify_client import notify_delivery_fee_denied

    await notify_delivery_fee_denied(
        kitchen_id=quote.kitchen_id,
        quote_id=quote.id,
        distance_km=float(quote.distance_km),
        fee=float(quote.fee),
        subtotal=body.subtotal,
        customer_phone=body.customer_phone,
    )

    return DeliveryFeeDenialResponse(acknowledged=True, kitchen_id=quote.kitchen_id)


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
                    o.customer_latitude,
                    o.customer_longitude,
                    COALESCE(o.delivery_mode, NULL) AS delivery_mode,
                    COALESCE(o.delivery_payer, NULL) AS delivery_payer,
                    COALESCE(o.owner_delivery_cost, 0) AS owner_delivery_cost,
                    k.name AS kitchen_name,
                    ST_Y(k.location::geometry) AS kitchen_latitude,
                    ST_X(k.location::geometry) AS kitchen_longitude,
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

    k_lat = float(row["kitchen_latitude"]) if row["kitchen_latitude"] is not None else None
    k_lng = float(row["kitchen_longitude"]) if row["kitchen_longitude"] is not None else None
    c_lat = float(row["customer_latitude"]) if row["customer_latitude"] is not None else None
    c_lng = float(row["customer_longitude"]) if row["customer_longitude"] is not None else None
    map_url = None
    if k_lat is not None and k_lng is not None and c_lat is not None and c_lng is not None:
        map_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={k_lat},{k_lng}&destination={c_lat},{c_lng}&travelmode=driving"
        )

    return TrackingResponse(
        tracking_token=row["tracking_token"],
        order_id=row["order_id"],
        order_code=row["order_code"],
        kitchen_id=row["kitchen_id"],
        kitchen_name=row["kitchen_name"],
        status=row["status"],
        delivery_type=row["delivery_type"],
        delivery_mode=row["delivery_mode"],
        delivery_payer=row["delivery_payer"],
        distance_km=float(row["distance_km"]) if row["distance_km"] is not None else None,
        delivery_fee=float(row["delivery_fee"]),
        owner_delivery_cost=float(row["owner_delivery_cost"] or 0),
        estimated_ready_at=row["estimated_ready_at"],
        tracking_notify_interval_min=int(row["tracking_notify_interval_min"]),
        updated_at=row["updated_at"],
        kitchen_latitude=k_lat,
        kitchen_longitude=k_lng,
        customer_latitude=c_lat,
        customer_longitude=c_lng,
        map_directions_url=map_url,
    )
