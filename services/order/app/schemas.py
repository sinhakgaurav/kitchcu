"""Order domain — manual/customer/master orders, status lifecycle, WhatsApp intake.

Order status machine (owner-driven, one-way except cancellation):

    received -> accepted -> preparing -> ready -> out_for_delivery -> delivered
                   \\_________________________________________________/
                                         -> cancelled (from any non-terminal state)

`delivered` and `cancelled` are terminal — no further transitions allowed.
See `app.models.VALID_TRANSITIONS` / `can_transition` for the enforced graph.

Order sources (`Order.source`):
    - "manual"        — owner keyed the order in directly (walk-in/phone)
    - "customer_pwa"  — placed via the customer PWA checkout (single kitchen)
    - "customer_pwa_multi" — a sub-order of a multi-kitchen master order
    - "whatsapp"      — parsed from an inbound WhatsApp message (via a draft)
    - "manual_message" — parsed from a manually pasted order message (via a draft)

Pricing invariant: `total == subtotal + delivery_fee` on every order, always
computed server-side from live catalog prices and kitchen delivery-radius rules
— client-supplied totals are never trusted.
"""

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MasterOrder, Order, OrderItem, OrderStatusEvent, can_transition
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher


class OrderItemInput(BaseModel):
    """A single ordered dish + quantity, used in manual, customer, and master order requests."""

    dish_id: uuid.UUID = Field(
        ...,
        description="UUID of an active dish in the kitchen's catalog. Must belong to the same kitchen as the order.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    quantity: int = Field(..., gt=0, description="Number of units ordered. Must be a positive integer.", examples=[2])
    special_instructions: str | None = Field(
        default=None,
        description="Free-text preparation note for the kitchen (e.g. spice level, allergies).",
        examples=["Less spicy, no onions"],
    )


class ManualOrderCreateRequest(BaseModel):
    """Owner-entered order for a single kitchen — walk-in, phone call, or manual confirmation.

    `total` is always computed server-side as `subtotal + delivery_fee`. When
    `delivery_type` is `"delivery"` and customer coordinates are supplied, the
    delivery fee is recomputed from the kitchen's radius rules and must match
    `delivery_fee`, or the request is rejected as a business-rule error (400).
    """

    items: list[OrderItemInput] = Field(
        ..., min_length=1, description="Order line items. At least one item is required."
    )
    delivery_type: Literal["pickup", "delivery"] = Field(
        default="pickup",
        description="'pickup' — no delivery fee, customer collects. 'delivery' — fee computed from kitchen radius rules.",
    )
    payment_method: Literal["cod", "online", "upi"] = Field(
        default="cod",
        description="Payment method the customer will use. 'cod' = cash/pay on pickup or delivery.",
    )
    customer_name: str | None = Field(
        default=None, description="Walk-in or phone customer's name, if known.", examples=["Rahul Sharma"]
    )
    customer_phone: str | None = Field(
        default=None,
        description="Customer phone number (E.164 preferred) for order tracking/notifications, if known.",
        examples=["+919876543210"],
    )
    delivery_fee: float = Field(
        default=0,
        ge=0,
        description=(
            "Delivery fee to charge. When customer lat/lng are provided, must exactly match the "
            "fee quoted by the kitchen's delivery-radius rules (free radius, per-km beyond, flat charge)."
        ),
        examples=[0, 40],
    )
    distance_km: float | None = Field(
        default=None,
        ge=0,
        description="Straight-line distance to the customer, in km. Recomputed and overridden server-side when lat/lng are supplied.",
    )
    delivery_fee_accepted: bool | None = Field(
        default=None,
        description="Whether the customer has acknowledged a non-zero delivery fee. Required (must be true) whenever the quoted fee is greater than zero.",
    )
    customer_latitude: float | None = Field(
        default=None, ge=-90, le=90, description="Delivery destination latitude, used to compute the delivery fee and distance server-side."
    )
    customer_longitude: float | None = Field(
        default=None, ge=-180, le=180, description="Delivery destination longitude, used to compute the delivery fee and distance server-side."
    )


class CustomerOrderCreateRequest(BaseModel):
    """Customer PWA checkout order for a single kitchen (customer identity comes from the JWT)."""

    items: list[OrderItemInput] = Field(
        ..., min_length=1, description="Cart line items. At least one item is required."
    )
    delivery_type: Literal["pickup", "delivery"] = Field(
        default="pickup",
        description="'pickup' — no delivery fee, customer collects. 'delivery' — fee computed from kitchen radius rules.",
    )
    payment_method: Literal["cod", "online", "upi"] = Field(
        default="cod", description="Payment method the customer will use at checkout."
    )
    delivery_fee: float = Field(
        default=0,
        ge=0,
        description="Delivery fee to charge; must match the fee quoted from kitchen radius rules when location is supplied.",
        examples=[0, 40],
    )
    customer_phone: str | None = Field(
        default=None,
        description="Overrides the phone on the customer's profile, if provided. One of profile phone / this field is required.",
        examples=["+919876543210"],
    )
    distance_km: float | None = Field(
        default=None, ge=0, description="Straight-line distance to the customer, in km. Recomputed server-side when lat/lng are supplied."
    )
    delivery_fee_accepted: bool | None = Field(
        default=None, description="Customer has acknowledged a non-zero delivery fee. Required (true) whenever the quoted fee is greater than zero."
    )
    customer_latitude: float | None = Field(
        default=None, ge=-90, le=90, description="Delivery destination latitude, used to compute the delivery fee server-side."
    )
    customer_longitude: float | None = Field(
        default=None, ge=-180, le=180, description="Delivery destination longitude, used to compute the delivery fee server-side."
    )


class MasterOrderGroupInput(BaseModel):
    """One kitchen's sub-cart within a multi-kitchen master order checkout (F06)."""

    kitchen_id: uuid.UUID = Field(
        ..., description="UUID of an active kitchen this group's items are ordered from.", examples=["8f14e45f-ceea-467e-9f1c-1234567890ab"]
    )
    items: list[OrderItemInput] = Field(
        ..., min_length=1, max_length=50, description="Line items for this kitchen. 1-50 items per group."
    )
    delivery_type: Literal["pickup", "delivery"] = Field(
        default="pickup", description="Delivery type for this kitchen's sub-order specifically."
    )
    delivery_fee: float = Field(
        default=0, ge=0, description="Delivery fee for this kitchen's sub-order; validated against radius rules when location is supplied."
    )
    distance_km: float | None = Field(
        default=None, ge=0, description="Straight-line distance to the customer for this kitchen, in km."
    )
    delivery_fee_accepted: bool | None = Field(
        default=None, description="Customer has acknowledged this sub-order's non-zero delivery fee."
    )
    customer_latitude: float | None = Field(default=None, ge=-90, le=90, description="Delivery destination latitude for this sub-order.")
    customer_longitude: float | None = Field(default=None, ge=-180, le=180, description="Delivery destination longitude for this sub-order.")


class MasterOrderCreateRequest(BaseModel):
    """Multi-kitchen checkout — one payment, grouped sub-orders per kitchen (F06, F44).

    Requires an `Idempotency-Key` header (8-128 chars); replaying the same key
    for the same customer returns the original master order instead of creating
    a duplicate. Each kitchen may appear in at most one group.
    """

    groups: list[MasterOrderGroupInput] = Field(
        ..., min_length=2, max_length=10, description="Per-kitchen sub-carts. 2-10 distinct kitchens required (single-kitchen checkout uses the regular order endpoints)."
    )
    payment_method: Literal["cod", "online", "upi"] = Field(
        ..., description="Single payment method applied to the aggregated master order total."
    )

    @model_validator(mode="after")
    def kitchens_must_be_distinct(self) -> "MasterOrderCreateRequest":
        kitchen_ids = [group.kitchen_id for group in self.groups]
        if len(set(kitchen_ids)) != len(kitchen_ids):
            raise ValueError("Each kitchen may appear only once")
        return self


class OrderItemResponse(BaseModel):
    """A priced, resolved line item as persisted on the order (snapshot of dish name/price at order time)."""

    id: uuid.UUID = Field(..., description="Order item UUID.")
    dish_id: uuid.UUID = Field(..., description="Referenced dish UUID (from `ckac_catalog.dishes`).")
    dish_name: str = Field(..., description="Dish name snapshotted at order time (unaffected by later menu edits).", examples=["Paneer Butter Masala"])
    quantity: int = Field(..., description="Units ordered.", examples=[2])
    unit_price: float = Field(..., description="Price per unit snapshotted at order time, in INR.", examples=[220.0])
    special_instructions: str | None = Field(default=None, description="Prep note supplied at order time.")
    prep_time_min: int = Field(..., description="Dish prep time in minutes, used to compute the order's `estimated_ready_at`.")

    model_config = {"from_attributes": True}


class StatusEventResponse(BaseModel):
    """One entry in an order's status-change audit trail (`ckac_orders.order_status_events`)."""

    id: uuid.UUID = Field(..., description="Status event UUID.")
    from_status: str | None = Field(
        default=None, description="Status before this transition. `null` for the initial 'received' event."
    )
    to_status: str = Field(..., description="Status after this transition.", examples=["accepted"])
    note: str | None = Field(default=None, description="Optional note attached by the owner when changing status.")
    created_at: datetime = Field(..., description="Timestamp the transition was recorded, UTC.")

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    """Full order read model — header, computed totals, line items, and status history.

    Status machine: `received -> accepted -> preparing -> ready -> out_for_delivery
    -> delivered`, with `cancelled` reachable from any non-terminal state.
    `delivered`/`cancelled` are terminal. `total` always equals `subtotal + delivery_fee`.
    """

    id: uuid.UUID = Field(..., description="Order UUID — the canonical order identifier used by other services/events.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen UUID (tenant scope).")
    master_order_id: uuid.UUID | None = Field(
        default=None, description="Parent master order UUID if this order is a sub-order of a multi-kitchen checkout, else `null`."
    )
    bill_id: str = Field(..., description="Per-kitchen daily sequential bill number.", examples=["BILL-20260712-0042"])
    order_code: str = Field(..., description="Human-facing order code: `{kitchen_code}-{bill_id}`.", examples=["CKPNQ001-BILL-20260712-0042"])
    status: str = Field(
        ...,
        description="Current lifecycle status.",
        examples=["received", "accepted", "preparing", "ready", "out_for_delivery", "delivered", "cancelled"],
    )
    source: str = Field(
        ...,
        description="How the order was created.",
        examples=["manual", "customer_pwa", "customer_pwa_multi", "whatsapp", "manual_message"],
    )
    delivery_type: str = Field(..., description="'pickup' or 'delivery'.", examples=["delivery"])
    payment_method: str = Field(..., description="'cod', 'online', or 'upi'.", examples=["cod"])
    customer_name: str | None = Field(default=None, description="Customer's name, if known.")
    customer_phone: str | None = Field(default=None, description="Customer's phone number, if known.")
    subtotal: float = Field(..., description="Sum of `unit_price * quantity` across all line items, in INR.", examples=[440.0])
    delivery_fee: float = Field(..., description="Delivery fee charged; 0 for pickup orders.", examples=[40.0])
    distance_km: float | None = Field(default=None, description="Distance from kitchen to customer, in km, when `delivery_type` is 'delivery'.")
    delivery_fee_accepted: bool | None = Field(
        default=None, description="Whether the customer acknowledged a non-zero delivery fee before checkout."
    )
    delivery_mode: str | None = Field(
        default=None, description="'self' or 'platform' once owner chooses fulfillment."
    )
    delivery_payer: str | None = Field(
        default=None, description="'owner' (in-range) or 'customer' (out-of-range)."
    )
    owner_delivery_cost: float = Field(
        default=0, description="Platform courier cost paid by kitchen when delivery_payer is owner."
    )
    customer_latitude: float | None = Field(default=None)
    customer_longitude: float | None = Field(default=None)
    tracking_token: str | None = Field(
        default=None, description="Opaque public tracking token for `GET /api/v1/delivery/track/{token}` on the delivery service. Set only for delivery orders."
    )
    total: float = Field(..., description="Amount charged to the customer: `subtotal + delivery_fee`.", examples=[480.0])
    estimated_prep_min: int | None = Field(default=None, description="Max prep time across line items, in minutes.")
    estimated_ready_at: datetime | None = Field(
        default=None, description="Predicted ready time: order creation time + prep time (+ dish delivery time if `delivery_type` is 'delivery')."
    )
    cancel_reason: str | None = Field(default=None, description="Reason supplied when the order was cancelled. `null` unless `status == 'cancelled'`.")
    created_at: datetime = Field(..., description="Order creation timestamp, UTC.")
    items: list[OrderItemResponse] = Field(default=[], description="Ordered dishes with quantities and snapshotted prices.")
    status_events: list[StatusEventResponse] = Field(default=[], description="Full status-change audit trail, oldest first.")


class MasterOrderResponse(BaseModel):
    """Aggregated multi-kitchen checkout — one payment/receipt spanning several per-kitchen sub-orders (F06, F44)."""

    id: uuid.UUID = Field(..., description="Master order UUID.")
    master_order_code: str = Field(..., description="Human-facing master order code.", examples=["MORD-20260712-A7F3"])
    status: str = Field(..., description="Master order status.", examples=["created"])
    payment_method: str = Field(..., description="Single payment method applied to the whole master order.", examples=["upi"])
    currency: str = Field(..., description="ISO 4217 currency code.", examples=["INR"])
    subtotal: float = Field(..., description="Sum of all sub-orders' subtotals.")
    delivery_fee: float = Field(..., description="Sum of all sub-orders' delivery fees.")
    total: float = Field(..., description="Grand total charged: `subtotal + delivery_fee` across all sub-orders.")
    created_at: datetime = Field(..., description="Master order creation timestamp, UTC.")
    orders: list[OrderResponse] = Field(..., description="Per-kitchen sub-orders, each independently trackable through the status machine.")


class OrderListResponse(BaseModel):
    """Paginated-free list wrapper for kitchen or customer order history."""

    kitchen_id: uuid.UUID = Field(
        ..., description="Kitchen UUID for owner listings. For customer order history spanning multiple kitchens, this is the most recent order's kitchen (or a nil UUID if the list is empty)."
    )
    orders: list[OrderResponse] = Field(..., description="Orders matching the query, newest first.")
    total: int = Field(..., description="Number of orders returned in `orders`.")


class OrderStatusUpdateRequest(BaseModel):
    """Owner-driven status transition. Only forward moves in the status machine (or cancellation) are accepted.

    Valid transitions: `received -> accepted -> preparing -> ready -> out_for_delivery
    -> delivered`; `cancelled` is reachable from any non-terminal status. Any other
    transition is rejected with 400. `cancel_reason` is required when `status` is `"cancelled"`.
    """

    status: Literal[
        "accepted", "preparing", "ready", "out_for_delivery", "delivered", "cancelled"
    ] = Field(..., description="Target status. Must be a valid forward transition from the order's current status.")
    note: str | None = Field(default=None, description="Optional note recorded on the status event (e.g. reason for delay).")
    cancel_reason: str | None = Field(
        default=None, description="Required when `status` is `'cancelled'`; explains why the order was cancelled.", examples=["Out of stock"]
    )

    @model_validator(mode="after")
    def cancel_requires_reason(self) -> "OrderStatusUpdateRequest":
        if self.status == "cancelled" and not self.cancel_reason:
            raise ValueError("Cancel reason is required")
        return self


class DeliveryFulfillmentRequest(BaseModel):
    """Owner chooses self delivery vs platform courier for a delivery order."""

    mode: Literal["self", "platform"] = Field(..., description="'self' or 'platform'.")
    customer_fee: float | None = Field(
        default=None,
        ge=0,
        description="Optional override of customer delivery fee (out-of-range self only).",
    )


async def set_delivery_fulfillment(
    session: AsyncSession,
    order: Order,
    data: DeliveryFulfillmentRequest,
    publisher: EventPublisher | None,
) -> Order:
    if order.delivery_type != "delivery":
        raise ValueError("Only delivery orders have fulfillment modes")
    if order.status in ("delivered", "cancelled"):
        raise ValueError("Cannot change delivery mode on a terminal order")

    distance = float(order.distance_km or 0)
    import math
    import os

    kitchen_row = (
        await session.execute(
            text(
                """
                SELECT
                    max_delivery_radius_km,
                    free_delivery_radius_km,
                    COALESCE(delivery_fee_per_km, 10) AS delivery_fee_per_km,
                    COALESCE(delivery_fee_flat_beyond, 0) AS delivery_fee_flat_beyond,
                    min_order_for_free_delivery,
                    COALESCE(delivery_subsidy_percent, 50) AS delivery_subsidy_percent,
                    ST_Y(location::geometry) AS kitchen_lat,
                    ST_X(location::geometry) AS kitchen_lng
                FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1
                """
            ),
            {"kid": order.kitchen_id},
        )
    ).mappings().one_or_none()
    max_km = float(kitchen_row["max_delivery_radius_km"]) if kitchen_row else 10.0
    in_range = distance <= max_km if order.distance_km is not None else True

    # Platform / Porter gross quote
    base = float(os.getenv("DELIVERY_PARTNER_BASE_FEE", "25"))
    per_km = float(os.getenv("DELIVERY_PARTNER_PER_KM", "12"))
    platform_gross = round(base + math.ceil(max(0.0, distance)) * per_km, 2)
    partner_name = "mock"
    porter_job = None
    if data.mode == "platform" and (os.getenv("DELIVERY_PARTNER") or "").lower() == "porter":
        try:
            from app.porter_client import quote_and_book_porter

            booked = await quote_and_book_porter(session, order)
            if booked:
                platform_gross = float(booked.get("fee") or platform_gross)
                partner_name = "porter"
                porter_job = booked.get("job_id")
        except Exception:
            partner_name = "porter_fallback"

    subsidy_pct = float(kitchen_row["delivery_subsidy_percent"]) if kitchen_row else 50.0
    min_order = (
        float(kitchen_row["min_order_for_free_delivery"])
        if kitchen_row and kitchen_row["min_order_for_free_delivery"] is not None
        else None
    )
    subtotal = float(order.subtotal or 0)

    def _share(gross: float) -> tuple[float, float, str]:
        if in_range:
            return 0.0, gross if data.mode == "platform" else 0.0, "owner"
        qualifies = min_order is not None and subtotal >= min_order and subsidy_pct > 0 and gross > 0
        if not qualifies:
            return gross, 0.0, "customer"
        owner_fee = round(gross * min(100.0, subsidy_pct) / 100.0, 2)
        customer_fee = round(gross - owner_fee, 2)
        if customer_fee <= 0:
            return 0.0, gross, "owner"
        if owner_fee <= 0:
            return gross, 0.0, "customer"
        return customer_fee, owner_fee, "shared"

    order.delivery_mode = data.mode
    if data.mode == "platform":
        cust_fee, own_fee, payer = _share(platform_gross)
        order.delivery_fee = cust_fee
        order.owner_delivery_cost = own_fee
        order.delivery_payer = payer
    else:
        free_km = float(kitchen_row["free_delivery_radius_km"]) if kitchen_row else 3.0
        fee_per = float(kitchen_row["delivery_fee_per_km"]) if kitchen_row else 10.0
        flat = float(kitchen_row["delivery_fee_flat_beyond"]) if kitchen_row else 0.0
        chargeable = max(1, math.ceil(max(0.0, distance - free_km)))
        self_gross = 0.0 if in_range else round(flat + chargeable * fee_per, 2)
        if data.customer_fee is not None and not in_range:
            self_gross = float(data.customer_fee)
        cust_fee, own_fee, payer = _share(self_gross)
        order.delivery_fee = cust_fee
        order.owner_delivery_cost = own_fee
        order.delivery_payer = payer

    if porter_job or partner_name == "porter":
        order.courier_partner = partner_name
        order.courier_job_id = porter_job

    order.total = float(order.subtotal) + float(order.delivery_fee)
    order.updated_at = datetime.now(UTC)
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="order.delivery_mode.set",
            aggregate_type="order",
            aggregate_id=str(order.id),
            producer="order-service",
            payload={
                "order_id": str(order.id),
                "mode": data.mode,
                "payer": order.delivery_payer,
                "customer_fee": float(order.delivery_fee),
                "owner_cost": float(order.owner_delivery_cost or 0),
                "partner": partner_name,
                "porter_job_id": porter_job,
            },
        )
        await publisher.publish(stream_key("orders", "order"), event, session=session)
    return order


async def _get_kitchen_code(session: AsyncSession, kitchen_id: uuid.UUID) -> str:
    result = await session.execute(
        text("SELECT code FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
        {"kid": kitchen_id},
    )
    code = result.scalar_one_or_none()
    if not code:
        raise ValueError("Kitchen not found")
    return code


async def _next_bill_id(session: AsyncSession, kitchen_id: uuid.UUID) -> tuple[str, str]:
    today = datetime.now(UTC).strftime("%Y%m%d")
    prefix = f"BILL-{today}-"
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"bill_seq:{kitchen_id}:{today}"},
    )
    result = await session.execute(
        select(func.count(Order.id)).where(
            Order.kitchen_id == kitchen_id,
            Order.bill_id.like(f"{prefix}%"),
        )
    )
    seq = (result.scalar_one() or 0) + 1
    bill_id = f"{prefix}{seq:04d}"
    kitchen_code = await _get_kitchen_code(session, kitchen_id)
    order_code = f"{kitchen_code}-{bill_id}"
    return bill_id, order_code


async def _next_master_order_code(session: AsyncSession) -> str:
    today = datetime.now(UTC).strftime("%Y%m%d")
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"master_order_code:{today}"},
    )
    for _ in range(10):
        code = f"MORD-{today}-{uuid.uuid4().hex[:4].upper()}"
        exists = await session.execute(
            select(MasterOrder.id).where(MasterOrder.master_order_code == code)
        )
        if exists.scalar_one_or_none() is None:
            return code
    raise ValueError("Could not allocate master order code")


async def _load_dish(
    session: AsyncSession, kitchen_id: uuid.UUID, dish_id: uuid.UUID
) -> tuple[str, float, int, int, int]:
    """Return name, price, prep_min, delivery_min, max_time_min (customer-facing ceiling)."""
    result = await session.execute(
        text(
            "SELECT name, price, prep_time_min, COALESCE(delivery_time_min, 0), "
            "COALESCE(max_time_min, prep_time_min + COALESCE(delivery_time_min, 0)) "
            "FROM ckac_catalog.dishes "
            "WHERE id = :did AND kitchen_id = :kid AND is_active = true LIMIT 1"
        ),
        {"did": dish_id, "kid": kitchen_id},
    )
    row = result.one_or_none()
    if not row:
        raise ValueError(f"Dish {dish_id} not found or inactive")
    return row[0], float(row[1]), int(row[2]), int(row[3]), int(row[4])


async def _quote_delivery_fee(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    *,
    delivery_type: str,
    subtotal: float,
    delivery_fee: float,
    distance_km: float | None,
    delivery_fee_accepted: bool | None,
    customer_latitude: float | None,
    customer_longitude: float | None,
) -> tuple[float, float | None, bool | None, str | None, bool]:
    """Return customer_fee, distance, accepted, payer, in_range.

    In range → customer fee 0 (owner pays logistics). Out of range → customer pays.
    """
    if delivery_type != "delivery":
        return 0.0, None, None, None, True

    if customer_latitude is None or customer_longitude is None:
        if delivery_fee > 0 and delivery_fee_accepted is not True:
            raise ValueError("delivery_fee_accepted must be true when location is unknown")
        payer = "customer" if delivery_fee > 0 else "owner"
        return delivery_fee, distance_km, delivery_fee_accepted, payer, True

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
            {"kid": kitchen_id, "lat": customer_latitude, "lng": customer_longitude},
        )
    ).mappings().one_or_none()
    if row is None:
        raise ValueError("Kitchen not found or inactive")

    import math

    dist = round(float(row["distance_km"]), 2)
    free_km = float(row["free_delivery_radius_km"])
    max_km = float(row["max_delivery_radius_km"])
    in_range = dist <= max_km

    if in_range:
        quoted = 0.0
        payer = "owner"
    else:
        chargeable_km = max(1, math.ceil(max(0.0, dist - free_km)))
        gross = round(
            float(row["delivery_fee_flat_beyond"])
            + chargeable_km * float(row["delivery_fee_per_km"]),
            2,
        )
        min_free = row["min_order_for_free_delivery"]
        # Match delivery-service cost share (default 50% kitchen subsidy when min order met).
        subsidy_row = (
            await session.execute(
                text(
                    "SELECT COALESCE(delivery_subsidy_percent, 50) "
                    "FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"
                ),
                {"kid": kitchen_id},
            )
        ).scalar_one_or_none()
        subsidy_pct = float(subsidy_row if subsidy_row is not None else 50)
        if min_free is not None and subtotal >= float(min_free) and gross > 0 and subsidy_pct > 0:
            owner_share = round(gross * min(100.0, subsidy_pct) / 100.0, 2)
            quoted = round(gross - owner_share, 2)
            payer = "shared" if quoted > 0 and owner_share > 0 else ("owner" if quoted <= 0 else "customer")
            if quoted <= 0:
                quoted = 0.0
                payer = "owner"
        else:
            quoted = gross
            payer = "customer"

    if round(delivery_fee, 2) != quoted:
        raise ValueError(f"Delivery fee mismatch: expected {quoted:.2f}")
    if quoted > 0 and delivery_fee_accepted is not True:
        raise ValueError("Customer must accept delivery fee before placing order")
    return quoted, dist, True if quoted > 0 else delivery_fee_accepted, payer, in_range


def _new_tracking_token() -> str:
    return secrets.token_urlsafe(24)


async def create_manual_order(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: ManualOrderCreateRequest,
    publisher: EventPublisher | None,
    *,
    source: str = "manual",
    customer_phone: str | None = None,
    status_note: str = "Manual order created",
    idempotency_key: str | None = None,
) -> tuple[Order, bool]:
    if idempotency_key:
        # Same pattern as create_master_order: advisory lock + existing-row check
        # so a client retry (double-tap, network timeout) never double-charges/orders.
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"order_idempotency:{kitchen_id}:{idempotency_key}"},
        )
        existing_result = await session.execute(
            select(Order).where(
                Order.kitchen_id == kitchen_id,
                Order.idempotency_key == idempotency_key,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return existing, False

    bill_id, order_code = await _next_bill_id(session, kitchen_id)

    line_items: list[tuple[str, float, int, int, OrderItemInput]] = []
    max_prep = 0
    max_projected = 0
    subtotal = 0.0

    for item in data.items:
        name, price, prep_min, delivery_min, max_time = await _load_dish(
            session, kitchen_id, item.dish_id
        )
        line_items.append((name, price, prep_min, delivery_min, item))
        max_prep = max(max_prep, prep_min)
        # Quality-first: project cart/order ETA from each dish's owner max_time (not sum of preps).
        if data.delivery_type == "delivery":
            max_projected = max(max_projected, max_time)
        else:
            max_projected = max(max_projected, prep_min)
        subtotal += price * item.quantity

    delivery_fee, distance_km, fee_accepted, delivery_payer, _in_range = await _quote_delivery_fee(
        session,
        kitchen_id,
        delivery_type=data.delivery_type,
        subtotal=subtotal,
        delivery_fee=data.delivery_fee,
        distance_km=data.distance_km,
        delivery_fee_accepted=data.delivery_fee_accepted,
        customer_latitude=data.customer_latitude,
        customer_longitude=data.customer_longitude,
    )
    total = subtotal + delivery_fee
    eta_minutes = max_projected or max_prep
    estimated_ready_at = datetime.now(UTC) + timedelta(minutes=eta_minutes)
    tracking_token = _new_tracking_token() if data.delivery_type == "delivery" else None

    order = Order(
        kitchen_id=kitchen_id,
        bill_id=bill_id,
        order_code=order_code,
        status="received",
        source=source,
        delivery_type=data.delivery_type,
        payment_method=data.payment_method,
        customer_name=data.customer_name,
        customer_phone=customer_phone or data.customer_phone,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        distance_km=distance_km,
        delivery_fee_accepted=fee_accepted,
        delivery_payer=delivery_payer if data.delivery_type == "delivery" else None,
        owner_delivery_cost=0,
        customer_latitude=data.customer_latitude,
        customer_longitude=data.customer_longitude,
        tracking_token=tracking_token,
        idempotency_key=idempotency_key,
        total=total,
        estimated_prep_min=max_prep,
        estimated_ready_at=estimated_ready_at,
    )
    session.add(order)
    await session.flush()

    for name, price, prep_min, _delivery_min, item in line_items:
        session.add(
            OrderItem(
                order_id=order.id,
                dish_id=item.dish_id,
                dish_name=name,
                quantity=item.quantity,
                unit_price=price,
                special_instructions=item.special_instructions,
                prep_time_min=prep_min,
            )
        )

    session.add(
        OrderStatusEvent(
            order_id=order.id,
            from_status=None,
            to_status="received",
            note=status_note,
            created_by=owner_id,
        )
    )
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="order.placed",
            aggregate_type="order",
            aggregate_id=str(order.id),
            producer="order-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "order_id": str(order.id),
                "order_code": order_code,
                "source": source,
                "total": total,
            },
        )
        await publisher.publish(stream_key("orders", "order"), event, session=session)
        if order.tracking_token:
            track_event = EventPublisher.build(
                event_type="delivery.tracking_created",
                aggregate_type="tracking",
                aggregate_id=order.tracking_token,
                producer="order-service",
                payload={
                    "order_id": str(order.id),
                    "kitchen_id": str(kitchen_id),
                    "tracking_token": order.tracking_token,
                    "distance_km": distance_km,
                },
            )
            await publisher.publish(stream_key("delivery", "tracking"), track_event, session=session)

    return order, True


async def create_customer_order(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    customer_id: uuid.UUID,
    customer_name: str,
    customer_phone: str,
    data: CustomerOrderCreateRequest,
    publisher: EventPublisher | None,
    *,
    idempotency_key: str | None = None,
) -> tuple[Order, bool]:
    manual = ManualOrderCreateRequest(
        items=data.items,
        delivery_type=data.delivery_type,
        payment_method=data.payment_method,
        delivery_fee=data.delivery_fee,
        customer_name=customer_name,
        customer_phone=customer_phone,
        distance_km=data.distance_km,
        delivery_fee_accepted=data.delivery_fee_accepted,
        customer_latitude=data.customer_latitude,
        customer_longitude=data.customer_longitude,
    )
    return await create_manual_order(
        session,
        kitchen_id,
        customer_id,
        manual,
        publisher,
        source="customer_pwa",
        customer_phone=customer_phone,
        status_note="Customer checkout order placed",
        idempotency_key=idempotency_key,
    )


async def create_master_order(
    session: AsyncSession,
    customer_id: uuid.UUID,
    customer_name: str,
    customer_phone: str,
    idempotency_key: str,
    data: MasterOrderCreateRequest,
    publisher: EventPublisher | None,
) -> tuple[MasterOrder, bool]:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"master_order_idempotency:{customer_id}:{idempotency_key}"},
    )
    existing_result = await session.execute(
        select(MasterOrder).where(
            MasterOrder.customer_id == customer_id,
            MasterOrder.idempotency_key == idempotency_key,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return existing, False

    for group in data.groups:
        kitchen_result = await session.execute(
            text(
                "SELECT 1 FROM ckac_identity.kitchens "
                "WHERE id = :kid AND status = 'active' LIMIT 1"
            ),
            {"kid": group.kitchen_id},
        )
        if kitchen_result.scalar_one_or_none() is None:
            raise ValueError(f"Kitchen {group.kitchen_id} is not available")

    master = MasterOrder(
        master_order_code=await _next_master_order_code(session),
        customer_id=customer_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        idempotency_key=idempotency_key,
        status="created",
        payment_method=data.payment_method,
        currency="INR",
        subtotal=0,
        delivery_fee=0,
        total=0,
    )
    session.add(master)
    await session.flush()

    subtotal = 0.0
    delivery_fee = 0.0
    order_ids: list[str] = []
    kitchen_ids: list[str] = []
    for group in data.groups:
        order_data = ManualOrderCreateRequest(
            items=group.items,
            delivery_type=group.delivery_type,
            payment_method=data.payment_method,
            delivery_fee=group.delivery_fee,
            customer_name=customer_name,
            customer_phone=customer_phone,
            distance_km=group.distance_km,
            delivery_fee_accepted=group.delivery_fee_accepted,
            customer_latitude=group.customer_latitude,
            customer_longitude=group.customer_longitude,
        )
        order, _created = await create_manual_order(
            session,
            group.kitchen_id,
            customer_id,
            order_data,
            publisher,
            source="customer_pwa_multi",
            customer_phone=customer_phone,
            status_note=f"Sub-order for {master.master_order_code}",
        )
        order.master_order_id = master.id
        subtotal += float(order.subtotal)
        delivery_fee += float(order.delivery_fee)
        order_ids.append(str(order.id))
        kitchen_ids.append(str(group.kitchen_id))

    master.subtotal = subtotal
    master.delivery_fee = delivery_fee
    master.total = subtotal + delivery_fee
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="master_order.created",
            aggregate_type="master_order",
            aggregate_id=str(master.id),
            producer="order-service",
            payload={
                "master_order_id": str(master.id),
                "master_order_code": master.master_order_code,
                "customer_id": str(customer_id),
                "order_ids": order_ids,
                "kitchen_ids": kitchen_ids,
                "total": float(master.total),
                "payment_method": master.payment_method,
            },
        )
        await publisher.publish(
            stream_key("orders", "master_order"),
            event,
            session=session,
        )

    return master, True


async def get_master_order_for_customer(
    session: AsyncSession,
    master_order_id: uuid.UUID,
    customer_id: uuid.UUID,
) -> MasterOrder | None:
    result = await session.execute(
        select(MasterOrder).where(
            MasterOrder.id == master_order_id,
            MasterOrder.customer_id == customer_id,
        )
    )
    return result.scalar_one_or_none()


async def list_customer_orders(
    session: AsyncSession,
    customer_phone: str,
    limit: int = 50,
) -> list[Order]:
    result = await session.execute(
        select(Order)
        .where(Order.customer_phone == customer_phone)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def repeat_customer_order(
    session: AsyncSession,
    order: Order,
    customer_id: uuid.UUID,
    publisher: EventPublisher | None,
) -> Order:
    items_result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    items = items_result.scalars().all()
    if not items:
        raise ValueError("Order has no items to repeat")

    request = CustomerOrderCreateRequest(
        items=[
            OrderItemInput(
                dish_id=item.dish_id,
                quantity=item.quantity,
                special_instructions=item.special_instructions,
            )
            for item in items
        ],
        delivery_type=order.delivery_type,  # type: ignore[arg-type]
        payment_method=order.payment_method,  # type: ignore[arg-type]
        delivery_fee=float(order.delivery_fee),
    )
    new_order, _created = await create_customer_order(
        session,
        order.kitchen_id,
        customer_id,
        order.customer_name or "Customer",
        order.customer_phone or "",
        request,
        publisher,
    )
    return new_order


async def update_order_status(
    session: AsyncSession,
    order: Order,
    owner_id: uuid.UUID,
    data: OrderStatusUpdateRequest,
    publisher: EventPublisher | None,
) -> Order:
    if not can_transition(order.status, data.status):
        raise ValueError(f"Invalid transition from {order.status} to {data.status}")

    previous = order.status
    order.status = data.status
    order.updated_at = datetime.now(UTC)
    if data.status == "cancelled":
        order.cancel_reason = data.cancel_reason

    session.add(
        OrderStatusEvent(
            order_id=order.id,
            from_status=previous,
            to_status=data.status,
            note=data.note,
            created_by=owner_id,
        )
    )
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="order.status.changed",
            aggregate_type="order",
            aggregate_id=str(order.id),
            producer="order-service",
            payload={
                "kitchen_id": str(order.kitchen_id),
                "order_id": str(order.id),
                "order_code": order.order_code,
                "from_status": previous,
                "to_status": data.status,
                "note": data.note,
            },
        )
        await publisher.publish(stream_key("orders", "order"), event, session=session)

    return order


async def order_to_response(session: AsyncSession, order: Order) -> OrderResponse:
    items_result = await session.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    events_result = await session.execute(
        select(OrderStatusEvent)
        .where(OrderStatusEvent.order_id == order.id)
        .order_by(OrderStatusEvent.created_at)
    )
    return OrderResponse(
        id=order.id,
        kitchen_id=order.kitchen_id,
        master_order_id=order.master_order_id,
        bill_id=order.bill_id,
        order_code=order.order_code,
        status=order.status,
        source=order.source,
        delivery_type=order.delivery_type,
        payment_method=order.payment_method,
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        subtotal=float(order.subtotal),
        delivery_fee=float(order.delivery_fee),
        distance_km=float(order.distance_km) if order.distance_km is not None else None,
        delivery_fee_accepted=order.delivery_fee_accepted,
        delivery_mode=getattr(order, "delivery_mode", None),
        delivery_payer=getattr(order, "delivery_payer", None),
        owner_delivery_cost=float(getattr(order, "owner_delivery_cost", 0) or 0),
        customer_latitude=getattr(order, "customer_latitude", None),
        customer_longitude=getattr(order, "customer_longitude", None),
        tracking_token=order.tracking_token,
        total=float(order.total),
        estimated_prep_min=order.estimated_prep_min,
        estimated_ready_at=order.estimated_ready_at,
        cancel_reason=order.cancel_reason,
        created_at=order.created_at,
        items=[OrderItemResponse.model_validate(i) for i in items_result.scalars().all()],
        status_events=[StatusEventResponse.model_validate(e) for e in events_result.scalars().all()],
    )


async def master_order_to_response(
    session: AsyncSession,
    master: MasterOrder,
) -> MasterOrderResponse:
    orders_result = await session.execute(
        select(Order)
        .where(Order.master_order_id == master.id)
        .order_by(Order.created_at, Order.id)
    )
    orders = [
        await order_to_response(session, order)
        for order in orders_result.scalars().all()
    ]
    return MasterOrderResponse(
        id=master.id,
        master_order_code=master.master_order_code,
        status=master.status,
        payment_method=master.payment_method,
        currency=master.currency,
        subtotal=float(master.subtotal),
        delivery_fee=float(master.delivery_fee),
        total=float(master.total),
        created_at=master.created_at,
        orders=orders,
    )


async def list_kitchen_orders(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    *,
    status: str | None = None,
    source: str | None = None,
) -> list[Order]:
    query = select(Order).where(Order.kitchen_id == kitchen_id)
    if status:
        query = query.where(Order.status == status)
    if source:
        query = query.where(Order.source == source)
    query = query.order_by(Order.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


class ParseMessageRequest(BaseModel):
    """Free-text order message to parse into line items against the kitchen's live menu."""

    message_text: str = Field(
        ..., min_length=1, description="Raw order text, one item per line (e.g. WhatsApp message body).", examples=["2x paneer butter masala\n1 naan\nno onions please"]
    )
    source: Literal["whatsapp", "manual_message"] = Field(
        default="manual_message", description="Origin of the message. Set to 'whatsapp' automatically on the internal WhatsApp intake route."
    )
    customer_phone: str | None = Field(default=None, description="Customer phone associated with the message, if known.")


class ParsedItemResponse(BaseModel):
    """One parsed line from the raw message, matched (or not) against the kitchen menu."""

    raw: str = Field(..., description="Original text of this line, unmodified.")
    dish_id: uuid.UUID | None = Field(default=None, description="Matched dish UUID, or `null` if unmatched.")
    dish_name: str | None = Field(default=None, description="Matched dish name, or `null` if unmatched.")
    quantity: int = Field(..., description="Parsed quantity for this line.")
    matched: bool = Field(..., description="Whether this line was successfully matched to an active menu dish.")
    unit_price: float | None = Field(default=None, description="Matched dish's current price, or `null` if unmatched.")


class OrderDraftResponse(BaseModel):
    """A parsed-but-unconfirmed order awaiting owner review (`ckac_orders.order_drafts`)."""

    id: uuid.UUID = Field(..., description="Draft UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen UUID.")
    status: str = Field(..., description="'draft' (awaiting confirmation) or 'confirmed' (converted to an order).", examples=["draft"])
    source: str = Field(..., description="'whatsapp' or 'manual_message'.")
    raw_message: str = Field(..., description="Original unparsed message text.")
    customer_phone: str | None = Field(default=None, description="Customer phone associated with the message, if known.")
    parsed_items: list[ParsedItemResponse] = Field(..., description="All parsed lines, matched and unmatched.")
    unmatched_lines: list[str] = Field(..., description="Raw lines that could not be matched to any active dish.")
    special_notes: list[str] = Field(..., description="Free-text notes extracted from the message (not tied to a specific item).")
    order_id: uuid.UUID | None = Field(default=None, description="UUID of the order created once this draft is confirmed, else `null`.")
    created_at: datetime = Field(..., description="Draft creation timestamp, UTC.")

    model_config = {"from_attributes": True}


class OrderDraftListResponse(BaseModel):
    """List of pending (unconfirmed) drafts for a kitchen."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen UUID.")
    drafts: list[OrderDraftResponse] = Field(..., description="Pending drafts, newest first.")
    total: int = Field(..., description="Number of drafts returned.")


async def _load_kitchen_menu(session: AsyncSession, kitchen_id: uuid.UUID) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT id, name, price, prep_time_min FROM ckac_catalog.dishes "
            "WHERE kitchen_id = :kid AND is_active = true"
        ),
        {"kid": kitchen_id},
    )
    return [
        {"id": row[0], "name": row[1], "price": float(row[2]), "prep_time_min": int(row[3])}
        for row in result.all()
    ]


def _draft_to_response(draft) -> OrderDraftResponse:
    items = [
        ParsedItemResponse(
            raw=p.get("raw", ""),
            dish_id=uuid.UUID(p["dish_id"]) if p.get("dish_id") else None,
            dish_name=p.get("dish_name"),
            quantity=p.get("quantity", 1),
            matched=p.get("matched", False),
            unit_price=p.get("unit_price"),
        )
        for p in (draft.parsed_items or [])
    ]
    return OrderDraftResponse(
        id=draft.id,
        kitchen_id=draft.kitchen_id,
        status=draft.status,
        source=draft.source,
        raw_message=draft.raw_message,
        customer_phone=draft.customer_phone,
        parsed_items=items,
        unmatched_lines=draft.unmatched_lines or [],
        special_notes=draft.special_notes or [],
        order_id=draft.order_id,
        created_at=draft.created_at,
    )


async def create_draft_from_message(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: ParseMessageRequest,
    publisher: EventPublisher | None,
) -> "OrderDraft":
    from app.models import OrderDraft
    from app.llm_parser import parse_order_message

    menu = await _load_kitchen_menu(session, kitchen_id)
    parsed = await parse_order_message(session, data.message_text, menu)

    parsed_items = [
        {
            "raw": ln.raw,
            "dish_id": ln.dish_id,
            "dish_name": ln.dish_name,
            "quantity": ln.quantity,
            "matched": ln.matched,
            "unit_price": ln.unit_price,
            "prep_time_min": ln.prep_time_min,
        }
        for ln in parsed.lines
    ]

    draft = OrderDraft(
        kitchen_id=kitchen_id,
        status="draft",
        source=data.source,
        raw_message=data.message_text,
        customer_phone=data.customer_phone,
        parsed_items=parsed_items,
        unmatched_lines=parsed.unmatched_lines,
        special_notes=parsed.special_notes,
    )
    session.add(draft)
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="order.draft.created",
            aggregate_type="order_draft",
            aggregate_id=str(draft.id),
            producer="order-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "draft_id": str(draft.id),
                "source": data.source,
                "matched_count": len(parsed.matched_items),
                "unmatched_count": len(parsed.unmatched_lines),
            },
        )
        await publisher.publish(stream_key("orders", "draft"), event, session=session)

    return draft


async def list_kitchen_drafts(session: AsyncSession, kitchen_id: uuid.UUID) -> list:
    from app.models import OrderDraft

    result = await session.execute(
        select(OrderDraft)
        .where(OrderDraft.kitchen_id == kitchen_id, OrderDraft.status == "draft")
        .order_by(OrderDraft.created_at.desc())
    )
    return list(result.scalars().all())


async def confirm_draft(
    session: AsyncSession,
    draft_id: uuid.UUID,
    kitchen_id: uuid.UUID,
    owner_id: uuid.UUID,
    publisher: EventPublisher | None,
) -> Order:
    from app.models import OrderDraft

    result = await session.execute(
        select(OrderDraft).where(
            OrderDraft.id == draft_id,
            OrderDraft.kitchen_id == kitchen_id,
            OrderDraft.status == "draft",
        )
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise ValueError("Draft not found")

    matched = [p for p in (draft.parsed_items or []) if p.get("matched") and p.get("dish_id")]
    if not matched:
        raise ValueError("No matched items to confirm")

    note = "; ".join(draft.special_notes) if draft.special_notes else None
    items = [
        OrderItemInput(
            dish_id=uuid.UUID(p["dish_id"]),
            quantity=p["quantity"],
            special_instructions=note,
        )
        for p in matched
    ]
    body = ManualOrderCreateRequest(
        items=items,
        customer_phone=draft.customer_phone,
    )
    order, _created = await create_manual_order(
        session,
        kitchen_id,
        owner_id,
        body,
        publisher,
        source=draft.source,
        customer_phone=draft.customer_phone,
    )
    draft.status = "confirmed"
    draft.order_id = order.id
    draft.updated_at = datetime.now(UTC)
    await session.flush()
    return order


class StockWarning(BaseModel):
    """Ingredient shortfall projected from this order's dishes against current stock (F19)."""

    ingredient_id: uuid.UUID = Field(..., description="Ingredient UUID (from `ckac_catalog.ingredients`).")
    ingredient_name: str = Field(..., description="Ingredient name.", examples=["Paneer"])
    unit: str = Field(..., description="Unit of measure.", examples=["kg"])
    required: float = Field(..., description="Quantity this order would consume.")
    available: float = Field(..., description="Quantity currently in stock.")
    shortfall: float = Field(..., description="`max(0, required - available)` — amount missing to fulfil the order.")
    is_low: bool = Field(..., description="Whether stock falls below the kitchen's configured low-stock threshold after this order.")


class OrderStockWarningsResponse(BaseModel):
    """Best-effort stock check for an order's ingredients. Returns an empty/false result if catalog is unreachable — never blocks order flow."""

    order_id: uuid.UUID = Field(..., description="Order UUID this check was run for.")
    warnings: list[StockWarning] = Field(..., description="Per-ingredient shortfall/low-stock warnings. Empty if all ingredients are sufficiently stocked.")
    has_shortfall: bool = Field(..., description="True if any ingredient has `shortfall > 0`.")


async def get_order_stock_warnings(session: AsyncSession, order: Order) -> OrderStockWarningsResponse:
    from app.catalog_client import check_low_stock

    items_result = await session.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    items = [
        {"dish_id": str(i.dish_id), "quantity": i.quantity}
        for i in items_result.scalars().all()
    ]
    if not items:
        return OrderStockWarningsResponse(order_id=order.id, warnings=[], has_shortfall=False)

    try:
        result = await check_low_stock(order.kitchen_id, order.id, items)
    except Exception:
        return OrderStockWarningsResponse(order_id=order.id, warnings=[], has_shortfall=False)

    warnings = [StockWarning(**w) for w in result.get("warnings", [])]
    return OrderStockWarningsResponse(
        order_id=order.id,
        warnings=warnings,
        has_shortfall=bool(result.get("has_shortfall")),
    )
