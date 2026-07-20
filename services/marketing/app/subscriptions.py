"""F34/F35 — kitchen monthly subscription plans + customer enrollments."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    OPEN_SUBSCRIPTION_STATUSES,
    PLAN_TYPES,
    CustomerSubscription,
    SubscriptionPlan,
)
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

MODULE_KEY = "tiffin_plans"


class DishesConfig(BaseModel):
    dish_ids: list[uuid.UUID] = Field(default_factory=list, max_length=40)
    weekdays: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4],
        description="0=Mon … 6=Sun (IST delivery days).",
    )
    meals_per_day: int = Field(default=1, ge=1, le=3)
    notes: str | None = Field(default=None, max_length=500)
    image_url: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional cover image URL (kitchen media upload).",
    )

    @field_validator("weekdays")
    @classmethod
    def valid_weekdays(cls, days: list[int]) -> list[int]:
        cleaned = sorted({d for d in days if 0 <= int(d) <= 6})
        if not cleaned:
            raise ValueError("At least one weekday required")
        return cleaned


def validate_plan_dish_selection(plan_type: str, dishes_config: DishesConfig | dict) -> None:
    """F35 — combo = multi-dish pack; single_dish = one dish monthly subscription."""
    if isinstance(dishes_config, DishesConfig):
        dish_ids = dishes_config.dish_ids
    else:
        dish_ids = list(dishes_config.get("dish_ids") or [])
    n = len(dish_ids)
    if n == 0:
        raise ValueError("Link at least one menu dish to this plan")
    if plan_type == "single_dish" and n != 1:
        raise ValueError("Single dish pack requires exactly one linked dish")
    if plan_type == "combo" and n < 2:
        raise ValueError("Combo plan requires at least two linked dishes")


class SubscriptionPlanCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, examples=["Veg Thali Monthly"])
    description: str | None = Field(
        default=None,
        max_length=20000,
        description="Plain text or sanitized rich HTML for the plan story.",
    )
    plan_type: Literal["tiffin", "thali", "combo", "single_dish"] = "tiffin"
    dishes_config: DishesConfig = Field(default_factory=DishesConfig)
    price_monthly: float = Field(..., gt=0, le=100000, examples=[2499.0])
    billing_cycle: Literal["monthly"] = "monthly"
    delivery_included: bool = True
    max_subscribers: int | None = Field(default=None, ge=1, le=10000)
    is_active: bool = True


class SubscriptionPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    plan_type: Literal["tiffin", "thali", "combo", "single_dish"] | None = None
    dishes_config: DishesConfig | None = None
    price_monthly: float | None = Field(default=None, gt=0, le=100000)
    delivery_included: bool | None = None
    max_subscribers: int | None = Field(default=None, ge=1, le=10000)
    is_active: bool | None = None


class SubscriptionPlanResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    name: str
    description: str | None
    plan_type: str
    dishes_config: dict[str, Any]
    price_monthly: float
    billing_cycle: str
    delivery_included: bool
    max_subscribers: int | None
    is_active: bool
    active_subscriber_count: int = 0
    pending_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionPlanListResponse(BaseModel):
    plans: list[SubscriptionPlanResponse]
    total: int


class SubscribeRequest(BaseModel):
    customer_name: str | None = Field(default=None, max_length=255)
    starts_on: date | None = None
    note: str | None = Field(default=None, max_length=500)


class SubscriptionDecisionRequest(BaseModel):
    owner_note: str | None = Field(default=None, max_length=500)
    starts_on: date | None = None


class CustomerSubscriptionResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    plan_id: uuid.UUID
    plan_name: str | None = None
    plan_type: str | None = None
    price_monthly: float | None = None
    customer_id: uuid.UUID
    customer_phone: str
    customer_name: str | None
    status: str
    billing_status: str
    owner_note: str | None
    starts_on: date | None
    created_at: datetime
    decided_at: datetime | None = None

    model_config = {"from_attributes": True}


class CustomerSubscriptionListResponse(BaseModel):
    subscriptions: list[CustomerSubscriptionResponse]
    total: int


class SubscriptionSummaryResponse(BaseModel):
    kitchen_id: uuid.UUID
    plans_total: int
    plans_active: int
    pending: int
    active: int
    paused: int
    denied: int
    cancelled: int
    mrr_estimate: float = Field(
        ...,
        description="Sum of price_monthly for active enrollments (INR) — not collected yet if billing=manual.",
    )


def _config_dict(cfg: DishesConfig | dict) -> dict:
    if isinstance(cfg, DishesConfig):
        data = cfg.model_dump()
        data["dish_ids"] = [str(x) for x in data["dish_ids"]]
        return data
    return dict(cfg or {})


async def _counts_for_plan(session: AsyncSession, plan_id: uuid.UUID) -> tuple[int, int]:
    active = (
        await session.execute(
            select(func.count())
            .select_from(CustomerSubscription)
            .where(
                CustomerSubscription.plan_id == plan_id,
                CustomerSubscription.status == "active",
            )
        )
    ).scalar_one()
    pending = (
        await session.execute(
            select(func.count())
            .select_from(CustomerSubscription)
            .where(
                CustomerSubscription.plan_id == plan_id,
                CustomerSubscription.status == "pending",
            )
        )
    ).scalar_one()
    return int(active or 0), int(pending or 0)


async def plan_to_response(session: AsyncSession, plan: SubscriptionPlan) -> SubscriptionPlanResponse:
    active_n, pending_n = await _counts_for_plan(session, plan.id)
    return SubscriptionPlanResponse(
        id=plan.id,
        kitchen_id=plan.kitchen_id,
        name=plan.name,
        description=plan.description,
        plan_type=plan.plan_type,
        dishes_config=plan.dishes_config if isinstance(plan.dishes_config, dict) else {},
        price_monthly=float(plan.price_monthly),
        billing_cycle=plan.billing_cycle,
        delivery_included=bool(plan.delivery_included),
        max_subscribers=plan.max_subscribers,
        is_active=bool(plan.is_active),
        active_subscriber_count=active_n,
        pending_count=pending_n,
        created_at=plan.created_at,
    )


async def subscription_to_response(
    session: AsyncSession, sub: CustomerSubscription
) -> CustomerSubscriptionResponse:
    plan = await session.get(SubscriptionPlan, sub.plan_id)
    return CustomerSubscriptionResponse(
        id=sub.id,
        kitchen_id=sub.kitchen_id,
        plan_id=sub.plan_id,
        plan_name=plan.name if plan else None,
        plan_type=plan.plan_type if plan else None,
        price_monthly=float(plan.price_monthly) if plan else None,
        customer_id=sub.customer_id,
        customer_phone=sub.customer_phone,
        customer_name=sub.customer_name,
        status=sub.status,
        billing_status=sub.billing_status,
        owner_note=sub.owner_note,
        starts_on=sub.starts_on,
        created_at=sub.created_at,
        decided_at=sub.decided_at,
    )


async def create_plan(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: SubscriptionPlanCreate,
    publisher: EventPublisher | None,
) -> SubscriptionPlan:
    if data.plan_type not in PLAN_TYPES:
        raise ValueError("Invalid plan_type")
    validate_plan_dish_selection(data.plan_type, data.dishes_config)
    plan = SubscriptionPlan(
        kitchen_id=kitchen_id,
        name=data.name.strip(),
        description=data.description,
        plan_type=data.plan_type,
        dishes_config=_config_dict(data.dishes_config),
        price_monthly=data.price_monthly,
        billing_cycle=data.billing_cycle,
        delivery_included=data.delivery_included,
        max_subscribers=data.max_subscribers,
        is_active=data.is_active,
    )
    session.add(plan)
    await session.flush()
    if publisher:
        event = EventPublisher.build(
            event_type="subscription.plan.created",
            aggregate_type="subscription_plan",
            aggregate_id=str(plan.id),
            producer="marketing-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "plan_id": str(plan.id),
                "name": plan.name,
                "plan_type": plan.plan_type,
                "price_monthly": float(plan.price_monthly),
            },
        )
        await publisher.publish(stream_key("marketing", "subscription"), event, session=session)
    return plan


async def update_plan(
    session: AsyncSession,
    plan: SubscriptionPlan,
    data: SubscriptionPlanUpdate,
    publisher: EventPublisher | None,
) -> SubscriptionPlan:
    if data.name is not None:
        plan.name = data.name.strip()
    if data.description is not None:
        plan.description = data.description
    if data.plan_type is not None:
        plan.plan_type = data.plan_type
    if data.dishes_config is not None:
        plan.dishes_config = _config_dict(data.dishes_config)
    next_type = data.plan_type if data.plan_type is not None else plan.plan_type
    next_cfg = data.dishes_config if data.dishes_config is not None else plan.dishes_config
    if data.plan_type is not None or data.dishes_config is not None:
        if isinstance(next_cfg, dict):
            validate_plan_dish_selection(
                next_type,
                DishesConfig(
                    dish_ids=[uuid.UUID(str(x)) for x in (next_cfg.get("dish_ids") or [])],
                    weekdays=list(next_cfg.get("weekdays") or [0, 1, 2, 3, 4]),
                    meals_per_day=int(next_cfg.get("meals_per_day") or 1),
                    notes=next_cfg.get("notes"),
                    image_url=next_cfg.get("image_url"),
                ),
            )
        else:
            validate_plan_dish_selection(next_type, next_cfg)
    if data.price_monthly is not None:
        plan.price_monthly = data.price_monthly
    if data.delivery_included is not None:
        plan.delivery_included = data.delivery_included
    if data.max_subscribers is not None:
        plan.max_subscribers = data.max_subscribers
    if data.is_active is not None:
        plan.is_active = data.is_active
    plan.updated_at = datetime.now(UTC)
    await session.flush()
    if publisher:
        event = EventPublisher.build(
            event_type="subscription.plan.updated",
            aggregate_type="subscription_plan",
            aggregate_id=str(plan.id),
            producer="marketing-service",
            payload={
                "kitchen_id": str(plan.kitchen_id),
                "plan_id": str(plan.id),
                "is_active": bool(plan.is_active),
                "price_monthly": float(plan.price_monthly),
            },
        )
        await publisher.publish(stream_key("marketing", "subscription"), event, session=session)
    return plan


async def list_plans(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    *,
    active_only: bool = False,
) -> list[SubscriptionPlan]:
    stmt = select(SubscriptionPlan).where(SubscriptionPlan.kitchen_id == kitchen_id)
    if active_only:
        stmt = stmt.where(SubscriptionPlan.is_active.is_(True))
    stmt = stmt.order_by(SubscriptionPlan.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def get_plan_for_kitchen(
    session: AsyncSession, kitchen_id: uuid.UUID, plan_id: uuid.UUID
) -> SubscriptionPlan:
    plan = await session.get(SubscriptionPlan, plan_id)
    if not plan or plan.kitchen_id != kitchen_id:
        raise ValueError("Plan not found")
    return plan


async def request_subscribe(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    plan_id: uuid.UUID,
    *,
    customer_id: uuid.UUID,
    customer_phone: str,
    customer_name: str | None,
    data: SubscribeRequest,
    publisher: EventPublisher | None,
) -> CustomerSubscription:
    plan = await get_plan_for_kitchen(session, kitchen_id, plan_id)
    if not plan.is_active:
        raise ValueError("Plan is not accepting new subscribers")

    existing = (
        await session.execute(
            select(CustomerSubscription).where(
                CustomerSubscription.kitchen_id == kitchen_id,
                CustomerSubscription.plan_id == plan_id,
                CustomerSubscription.customer_id == customer_id,
                CustomerSubscription.status.in_(tuple(OPEN_SUBSCRIPTION_STATUSES)),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Already have an open subscription ({existing.status})")

    active_n, _ = await _counts_for_plan(session, plan.id)
    if plan.max_subscribers is not None and active_n >= int(plan.max_subscribers):
        raise ValueError("Plan is at max subscribers")

    sub = CustomerSubscription(
        kitchen_id=kitchen_id,
        plan_id=plan_id,
        customer_id=customer_id,
        customer_phone=customer_phone,
        customer_name=customer_name or data.customer_name,
        status="pending",
        billing_status="manual",
        owner_note=data.note,
        starts_on=data.starts_on,
    )
    session.add(sub)
    await session.flush()
    if publisher:
        event = EventPublisher.build(
            event_type="subscription.requested",
            aggregate_type="customer_subscription",
            aggregate_id=str(sub.id),
            producer="marketing-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "plan_id": str(plan_id),
                "subscription_id": str(sub.id),
                "customer_id": str(customer_id),
            },
        )
        await publisher.publish(stream_key("marketing", "subscription"), event, session=session)
    return sub


async def get_subscription_for_kitchen(
    session: AsyncSession, kitchen_id: uuid.UUID, sub_id: uuid.UUID
) -> CustomerSubscription:
    sub = await session.get(CustomerSubscription, sub_id)
    if not sub or sub.kitchen_id != kitchen_id:
        raise ValueError("Subscription not found")
    return sub


async def decide_subscription(
    session: AsyncSession,
    sub: CustomerSubscription,
    *,
    action: Literal["accept", "deny", "activate", "deactivate"],
    owner_id: uuid.UUID,
    data: SubscriptionDecisionRequest,
    publisher: EventPublisher | None,
) -> CustomerSubscription:
    now = datetime.now(UTC)
    transitions = {
        "accept": ("pending", "active", "subscription.accepted"),
        "deny": ("pending", "denied", "subscription.denied"),
        "activate": ("paused", "active", "subscription.activated"),
        "deactivate": ("active", "paused", "subscription.deactivated"),
    }
    expected_from, to_status, event_type = transitions[action]
    if sub.status != expected_from:
        raise ValueError(f"Cannot {action} from status {sub.status}")

    if action == "accept":
        plan = await session.get(SubscriptionPlan, sub.plan_id)
        if plan and plan.max_subscribers is not None:
            active_n, _ = await _counts_for_plan(session, plan.id)
            if active_n >= int(plan.max_subscribers):
                raise ValueError("Plan is at max subscribers")

    sub.status = to_status
    sub.decided_at = now
    sub.decided_by = owner_id
    sub.updated_at = now
    if data.owner_note is not None:
        sub.owner_note = data.owner_note
    if data.starts_on is not None:
        sub.starts_on = data.starts_on
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type=event_type,
            aggregate_type="customer_subscription",
            aggregate_id=str(sub.id),
            producer="marketing-service",
            payload={
                "kitchen_id": str(sub.kitchen_id),
                "plan_id": str(sub.plan_id),
                "subscription_id": str(sub.id),
                "status": sub.status,
            },
        )
        await publisher.publish(stream_key("marketing", "subscription"), event, session=session)
    return sub


async def cancel_subscription(
    session: AsyncSession,
    sub: CustomerSubscription,
    *,
    customer_id: uuid.UUID,
    publisher: EventPublisher | None,
) -> CustomerSubscription:
    if sub.customer_id != customer_id:
        raise ValueError("Subscription not found")
    if sub.status in ("cancelled", "denied"):
        raise ValueError("Subscription already closed")
    sub.status = "cancelled"
    sub.updated_at = datetime.now(UTC)
    await session.flush()
    if publisher:
        event = EventPublisher.build(
            event_type="subscription.cancelled",
            aggregate_type="customer_subscription",
            aggregate_id=str(sub.id),
            producer="marketing-service",
            payload={
                "kitchen_id": str(sub.kitchen_id),
                "subscription_id": str(sub.id),
                "by": "customer",
            },
        )
        await publisher.publish(stream_key("marketing", "subscription"), event, session=session)
    return sub


async def list_kitchen_subscriptions(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    *,
    status: str | None = None,
    limit: int = 100,
) -> list[CustomerSubscription]:
    limit = max(1, min(200, limit))
    stmt = select(CustomerSubscription).where(CustomerSubscription.kitchen_id == kitchen_id)
    if status:
        stmt = stmt.where(CustomerSubscription.status == status)
    stmt = stmt.order_by(CustomerSubscription.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def list_customer_subscriptions(
    session: AsyncSession, customer_id: uuid.UUID
) -> list[CustomerSubscription]:
    stmt = (
        select(CustomerSubscription)
        .where(CustomerSubscription.customer_id == customer_id)
        .order_by(CustomerSubscription.created_at.desc())
        .limit(100)
    )
    return list((await session.execute(stmt)).scalars().all())


async def subscription_summary(
    session: AsyncSession, kitchen_id: uuid.UUID
) -> SubscriptionSummaryResponse:
    plans = await list_plans(session, kitchen_id)
    plans_active = sum(1 for p in plans if p.is_active)
    counts = {s: 0 for s in ("pending", "active", "paused", "denied", "cancelled")}
    rows = (
        await session.execute(
            select(CustomerSubscription.status, func.count())
            .where(CustomerSubscription.kitchen_id == kitchen_id)
            .group_by(CustomerSubscription.status)
        )
    ).all()
    for status, n in rows:
        if status in counts:
            counts[status] = int(n)

    mrr_rows = (
        await session.execute(
            select(func.coalesce(func.sum(SubscriptionPlan.price_monthly), 0))
            .select_from(CustomerSubscription)
            .join(SubscriptionPlan, SubscriptionPlan.id == CustomerSubscription.plan_id)
            .where(
                CustomerSubscription.kitchen_id == kitchen_id,
                CustomerSubscription.status == "active",
            )
        )
    ).scalar_one()

    return SubscriptionSummaryResponse(
        kitchen_id=kitchen_id,
        plans_total=len(plans),
        plans_active=plans_active,
        pending=counts["pending"],
        active=counts["active"],
        paused=counts["paused"],
        denied=counts["denied"],
        cancelled=counts["cancelled"],
        mrr_estimate=float(mrr_rows or 0),
    )
