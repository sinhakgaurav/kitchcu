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
    dish_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    special_instructions: str | None = None


class ManualOrderCreateRequest(BaseModel):
    items: list[OrderItemInput] = Field(..., min_length=1)
    delivery_type: Literal["pickup", "delivery"] = "pickup"
    payment_method: Literal["cod", "online", "upi"] = "cod"
    customer_name: str | None = None
    customer_phone: str | None = None
    delivery_fee: float = Field(default=0, ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    delivery_fee_accepted: bool | None = None
    customer_latitude: float | None = Field(default=None, ge=-90, le=90)
    customer_longitude: float | None = Field(default=None, ge=-180, le=180)


class CustomerOrderCreateRequest(BaseModel):
    items: list[OrderItemInput] = Field(..., min_length=1)
    delivery_type: Literal["pickup", "delivery"] = "pickup"
    payment_method: Literal["cod", "online", "upi"] = "cod"
    delivery_fee: float = Field(default=0, ge=0)
    customer_phone: str | None = None
    distance_km: float | None = Field(default=None, ge=0)
    delivery_fee_accepted: bool | None = None
    customer_latitude: float | None = Field(default=None, ge=-90, le=90)
    customer_longitude: float | None = Field(default=None, ge=-180, le=180)


class MasterOrderGroupInput(BaseModel):
    kitchen_id: uuid.UUID
    items: list[OrderItemInput] = Field(..., min_length=1, max_length=50)
    delivery_type: Literal["pickup", "delivery"] = "pickup"
    delivery_fee: float = Field(default=0, ge=0)
    distance_km: float | None = Field(default=None, ge=0)
    delivery_fee_accepted: bool | None = None
    customer_latitude: float | None = Field(default=None, ge=-90, le=90)
    customer_longitude: float | None = Field(default=None, ge=-180, le=180)


class MasterOrderCreateRequest(BaseModel):
    groups: list[MasterOrderGroupInput] = Field(..., min_length=2, max_length=10)
    payment_method: Literal["cod", "online", "upi"]

    @model_validator(mode="after")
    def kitchens_must_be_distinct(self) -> "MasterOrderCreateRequest":
        kitchen_ids = [group.kitchen_id for group in self.groups]
        if len(set(kitchen_ids)) != len(kitchen_ids):
            raise ValueError("Each kitchen may appear only once")
        return self


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    dish_id: uuid.UUID
    dish_name: str
    quantity: int
    unit_price: float
    special_instructions: str | None
    prep_time_min: int

    model_config = {"from_attributes": True}


class StatusEventResponse(BaseModel):
    id: uuid.UUID
    from_status: str | None
    to_status: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    master_order_id: uuid.UUID | None
    bill_id: str
    order_code: str
    status: str
    source: str
    delivery_type: str
    payment_method: str
    customer_name: str | None
    customer_phone: str | None
    subtotal: float
    delivery_fee: float
    distance_km: float | None = None
    delivery_fee_accepted: bool | None = None
    tracking_token: str | None = None
    total: float
    estimated_prep_min: int | None
    estimated_ready_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    items: list[OrderItemResponse] = []
    status_events: list[StatusEventResponse] = []


class MasterOrderResponse(BaseModel):
    id: uuid.UUID
    master_order_code: str
    status: str
    payment_method: str
    currency: str
    subtotal: float
    delivery_fee: float
    total: float
    created_at: datetime
    orders: list[OrderResponse]


class OrderListResponse(BaseModel):
    kitchen_id: uuid.UUID
    orders: list[OrderResponse]
    total: int


class OrderStatusUpdateRequest(BaseModel):
    status: Literal[
        "accepted", "preparing", "ready", "out_for_delivery", "delivered", "cancelled"
    ]
    note: str | None = None
    cancel_reason: str | None = None

    @model_validator(mode="after")
    def cancel_requires_reason(self) -> "OrderStatusUpdateRequest":
        if self.status == "cancelled" and not self.cancel_reason:
            raise ValueError("Cancel reason is required")
        return self


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
) -> tuple[str, float, int, int]:
    result = await session.execute(
        text(
            "SELECT name, price, prep_time_min, COALESCE(delivery_time_min, 0) "
            "FROM ckac_catalog.dishes "
            "WHERE id = :did AND kitchen_id = :kid AND is_active = true LIMIT 1"
        ),
        {"did": dish_id, "kid": kitchen_id},
    )
    row = result.one_or_none()
    if not row:
        raise ValueError(f"Dish {dish_id} not found or inactive")
    return row[0], float(row[1]), int(row[2]), int(row[3])


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
) -> tuple[float, float | None, bool | None]:
    if delivery_type != "delivery":
        return 0.0, None, None

    if customer_latitude is None or customer_longitude is None:
        if delivery_fee > 0 and delivery_fee_accepted is not True:
            raise ValueError("delivery_fee_accepted must be true when location is unknown")
        return delivery_fee, distance_km, delivery_fee_accepted

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
    if dist > max_km:
        raise ValueError("Delivery address is outside kitchen service range")

    if dist <= free_km:
        quoted = 0.0
    else:
        chargeable_km = math.ceil(dist - free_km)
        quoted = round(
            float(row["delivery_fee_flat_beyond"])
            + chargeable_km * float(row["delivery_fee_per_km"]),
            2,
        )
    min_free = row["min_order_for_free_delivery"]
    if min_free is not None and subtotal >= float(min_free) and quoted > 0:
        quoted = 0.0

    if round(delivery_fee, 2) != quoted:
        raise ValueError(f"Delivery fee mismatch: expected {quoted:.2f}")
    if quoted > 0 and delivery_fee_accepted is not True:
        raise ValueError("Customer must accept delivery fee before placing order")
    return quoted, dist, True if quoted > 0 else delivery_fee_accepted


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
) -> Order:
    bill_id, order_code = await _next_bill_id(session, kitchen_id)

    line_items: list[tuple[str, float, int, int, OrderItemInput]] = []
    max_prep = 0
    max_delivery = 0
    subtotal = 0.0

    for item in data.items:
        name, price, prep_min, delivery_min = await _load_dish(session, kitchen_id, item.dish_id)
        line_items.append((name, price, prep_min, delivery_min, item))
        max_prep = max(max_prep, prep_min)
        max_delivery = max(max_delivery, delivery_min)
        subtotal += price * item.quantity

    delivery_fee, distance_km, fee_accepted = await _quote_delivery_fee(
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
    eta_minutes = max_prep + (max_delivery if data.delivery_type == "delivery" else 0)
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
        tracking_token=tracking_token,
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

    return order


async def create_customer_order(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    customer_id: uuid.UUID,
    customer_name: str,
    customer_phone: str,
    data: CustomerOrderCreateRequest,
    publisher: EventPublisher | None,
) -> Order:
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
        order = await create_manual_order(
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
    return await create_customer_order(
        session,
        order.kitchen_id,
        customer_id,
        order.customer_name or "Customer",
        order.customer_phone or "",
        request,
        publisher,
    )


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
    message_text: str = Field(..., min_length=1)
    source: Literal["whatsapp", "manual_message"] = "manual_message"
    customer_phone: str | None = None


class ParsedItemResponse(BaseModel):
    raw: str
    dish_id: uuid.UUID | None = None
    dish_name: str | None = None
    quantity: int
    matched: bool
    unit_price: float | None = None


class OrderDraftResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    status: str
    source: str
    raw_message: str
    customer_phone: str | None
    parsed_items: list[ParsedItemResponse]
    unmatched_lines: list[str]
    special_notes: list[str]
    order_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderDraftListResponse(BaseModel):
    kitchen_id: uuid.UUID
    drafts: list[OrderDraftResponse]
    total: int


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
    from app.parser import match_dishes, parse_message_text

    menu = await _load_kitchen_menu(session, kitchen_id)
    parsed = parse_message_text(data.message_text)
    parsed = match_dishes(parsed, menu)

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
    order = await create_manual_order(
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
    ingredient_id: uuid.UUID
    ingredient_name: str
    unit: str
    required: float
    available: float
    shortfall: float
    is_low: bool


class OrderStockWarningsResponse(BaseModel):
    order_id: uuid.UUID
    warnings: list[StockWarning]
    has_shortfall: bool


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
