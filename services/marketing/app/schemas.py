"""Marketing domain — CRM sync, coupons, targeted promotions (F36–F38)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Coupon, KitchenCustomer, Promotion
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

LOCAL_TZ = ZoneInfo("Asia/Kolkata")
CHURN_INACTIVE_DAYS = 21


class FavoriteDish(BaseModel):
    """One of a customer's top-5 most-ordered dishes at this kitchen."""

    dish_id: uuid.UUID = Field(..., description="Dish UUID.")
    dish_name: str = Field(..., description="Dish name at time of aggregation.", examples=["Paneer Butter Masala"])
    quantity: int = Field(..., description="Total quantity ordered across all non-cancelled orders.", examples=[12])


class OrderPatterns(BaseModel):
    """Derived ordering-behavior signals used for segmentation and promotions."""

    peak_hours: list[int] = Field(
        default_factory=list, description="Up to 3 hours-of-day (0-23, IST) with the most orders from this customer.", examples=[[13, 20, 21]]
    )
    weekday_orders: int = Field(default=0, description="Count of non-cancelled orders placed Mon-Fri (IST).")
    weekend_orders: int = Field(default=0, description="Count of non-cancelled orders placed Sat-Sun (IST).")


class KitchenCustomerResponse(BaseModel):
    """A kitchen's CRM profile for one customer (F37) — owner-only, per-kitchen (never shared across kitchens)."""

    id: uuid.UUID = Field(..., description="CRM profile row UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen UUID.")
    customer_id: uuid.UUID | None = Field(default=None, description="Linked platform customer UUID, if the phone matches a registered customer account.")
    customer_phone: str = Field(..., description="Customer phone (E.164), the CRM join key.", examples=["+919876543210"])
    customer_name: str | None = Field(default=None, description="Most recent name on record for this phone.")
    total_spend: float = Field(..., description="Lifetime spend (INR) across non-cancelled orders at this kitchen.", examples=[4250.0])
    monthly_spend: float = Field(..., description="Spend (INR) since the start of the current calendar month (Asia/Kolkata).", examples=[620.0])
    order_count: int = Field(..., description="Total non-cancelled order count at this kitchen.", examples=[9])
    favorite_dishes: list[FavoriteDish] = Field(..., description="Top-5 dishes by quantity ordered.")
    order_patterns: OrderPatterns = Field(..., description="Peak hours + weekday/weekend order split.")
    tags: list[str] = Field(..., description="Owner-assigned free-form tags (e.g. 'vip', 'spicy-lover'). Owner CRM belongs to the kitchen, never shared.")
    last_order_at: datetime | None = Field(default=None, description="Timestamp of the customer's most recent non-cancelled order, UTC.")

    model_config = {"from_attributes": True}


class KitchenCustomerListResponse(BaseModel):
    """CRM roster for a kitchen, ranked by total spend."""

    customers: list[KitchenCustomerResponse] = Field(..., description="Customer profiles ordered by `total_spend` descending.")
    total: int = Field(..., description="Number of customer profiles returned.")
    synced_at: datetime | None = Field(default=None, description="Set only when `refresh=true` was requested — UTC timestamp of this re-sync from order history.")


class KitchenCustomerTagsUpdate(BaseModel):
    """Replace an owner's free-form tags for one CRM profile."""

    tags: list[str] = Field(default_factory=list, max_length=20, description="Up to 20 tags; normalized to lowercase/trimmed.", examples=[["vip", "no-onion"]])

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        cleaned = [t.strip().lower() for t in tags if t.strip()]
        if len(cleaned) > 20:
            raise ValueError("At most 20 tags allowed")
        return cleaned


class CouponCreateRequest(BaseModel):
    """Owner request to create a discount coupon (F36) for a kitchen."""

    code: str = Field(min_length=3, max_length=32, description="Coupon code, normalized to uppercase.", examples=["WELCOME10"])
    discount_type: Literal["percent", "fixed"] = Field(..., description="'percent' — % off subtotal (capped at 100). 'fixed' — flat INR amount off, capped at subtotal.")
    discount_value: float = Field(gt=0, description="Discount magnitude — a percent (0-100) or a flat INR amount depending on `discount_type`.", examples=[10.0])
    min_order_amount: float | None = Field(default=None, ge=0, description="Minimum cart subtotal (INR) required to apply this coupon.", examples=[199.0])
    max_uses: int | None = Field(default=None, ge=1, description="Maximum total redemptions across all customers; unlimited if omitted.")
    valid_from: datetime | None = Field(default=None, description="Coupon becomes valid at this UTC timestamp; immediately valid if omitted.")
    valid_until: datetime | None = Field(default=None, description="Coupon expires at this UTC timestamp; never expires if omitted.")

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, code: str) -> str:
        return code.strip().upper()

    @field_validator("discount_value")
    @classmethod
    def validate_discount(cls, value: float, info) -> float:
        if info.data.get("discount_type") == "percent" and value > 100:
            raise ValueError("Percent discount cannot exceed 100")
        return value


class CouponUpdateRequest(BaseModel):
    """Owner request to activate/deactivate an existing coupon."""

    is_active: bool = Field(..., description="Set false to pause redemptions without deleting the coupon (preserves usage history).")


class CouponResponse(BaseModel):
    """A kitchen's discount coupon."""

    id: uuid.UUID = Field(..., description="Coupon UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen UUID.")
    code: str = Field(..., description="Uppercase coupon code, unique per kitchen.", examples=["WELCOME10"])
    discount_type: str = Field(..., description="'percent' or 'fixed'.")
    discount_value: float = Field(..., description="Discount magnitude (percent or flat INR, per `discount_type`).")
    min_order_amount: float | None = Field(default=None, description="Minimum cart subtotal (INR) required to apply.")
    max_uses: int | None = Field(default=None, description="Maximum total redemptions, or unlimited if null.")
    used_count: int = Field(..., description="Redemptions consumed so far.")
    valid_from: datetime | None = Field(default=None, description="Valid-from UTC timestamp, or null if immediately valid.")
    valid_until: datetime | None = Field(default=None, description="Expiry UTC timestamp, or null if never expires.")
    is_active: bool = Field(..., description="Whether the coupon currently accepts redemptions.")
    created_at: datetime = Field(..., description="Creation timestamp, UTC.")

    model_config = {"from_attributes": True}


class CouponListResponse(BaseModel):
    """Full coupon roster for a kitchen (owner view)."""

    coupons: list[CouponResponse] = Field(..., description="Coupons ordered by creation date, newest first.")
    total: int = Field(..., description="Number of coupons returned.")


class CouponValidateRequest(BaseModel):
    """Customer-side request to validate + price a coupon during checkout."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen the coupon belongs to.")
    code: str = Field(..., description="Coupon code as entered by the customer (case-insensitive).", examples=["WELCOME10"])
    subtotal: float = Field(ge=0, description="Cart subtotal (INR) to evaluate `min_order_amount` and compute the discount amount.", examples=[450.0])

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, code: str) -> str:
        return code.strip().upper()


class CouponValidateResponse(BaseModel):
    """Result of validating a coupon against a cart — checkout uses this to price the order."""

    valid: bool = Field(..., description="Whether the coupon can be applied to this cart right now.")
    coupon_id: uuid.UUID | None = Field(default=None, description="Coupon UUID, when valid.")
    code: str | None = Field(default=None, description="Normalized coupon code, when valid.")
    discount_type: str | None = Field(default=None, description="'percent' or 'fixed', when valid.")
    discount_amount: float = Field(default=0, description="Computed discount in INR to subtract from the order total. `0` when invalid.", examples=[45.0])
    message: str = Field(..., description="Human-readable status, e.g. 'Coupon applied', 'Coupon expired', 'Minimum order ₹199 required'.")


class PromotionCreateRequest(BaseModel):
    """Owner request to create a targeted, time-boxed dish promotion (F38)."""

    name: str = Field(min_length=2, max_length=120, description="Internal promotion name shown to the owner.", examples=["Weekend VIP Special"])
    dish_id: uuid.UUID = Field(..., description="Dish this promotion discounts; must belong to the same kitchen.")
    special_price: float = Field(gt=0, description="Promotional price (INR) for the dish while the promotion is active.", examples=[99.0])
    segment: Literal["all", "top_spenders", "repeat", "vip", "churn_risk"] = Field(
        default="all",
        description=(
            "Customer segment eligible for the promo: 'all' — every customer; 'repeat' — 2+ orders; "
            "'vip' — 5+ orders; 'churn_risk' — 2+ orders but inactive 21+ days; "
            "'top_spenders' — top-N by total spend (see `segment_limit`)."
        ),
    )
    segment_limit: int | None = Field(default=None, ge=1, le=500, description="Required when `segment='top_spenders'` — the N in top-N by spend.")
    starts_at: datetime = Field(..., description="Promotion start, UTC.")
    ends_at: datetime = Field(..., description="Promotion end, UTC. Must be after `starts_at`.")

    @field_validator("ends_at")
    @classmethod
    def ends_after_starts(cls, ends_at: datetime, info) -> datetime:
        starts = info.data.get("starts_at")
        if starts and ends_at <= starts:
            raise ValueError("ends_at must be after starts_at")
        return ends_at


class PromotionResponse(BaseModel):
    """A kitchen's targeted promotion (owner view — full detail)."""

    id: uuid.UUID = Field(..., description="Promotion UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen UUID.")
    name: str = Field(..., description="Internal promotion name.")
    dish_id: uuid.UUID = Field(..., description="Discounted dish UUID.")
    dish_name: str = Field(..., description="Dish name at creation time.")
    special_price: float = Field(..., description="Promotional price in INR.")
    segment: str = Field(..., description="Eligible customer segment.")
    segment_limit: int | None = Field(default=None, description="Top-N cutoff when `segment='top_spenders'`.")
    starts_at: datetime = Field(..., description="Promotion start, UTC.")
    ends_at: datetime = Field(..., description="Promotion end, UTC.")
    is_active: bool = Field(..., description="Owner-controlled active flag (independent of the start/end window).")
    created_at: datetime = Field(..., description="Creation timestamp, UTC.")

    model_config = {"from_attributes": True}


class PromotionListResponse(BaseModel):
    """Full promotion roster for a kitchen (owner view)."""

    promotions: list[PromotionResponse] = Field(..., description="Promotions ordered by creation date, newest first.")
    total: int = Field(..., description="Number of promotions returned.")


class ActivePromotionResponse(BaseModel):
    """Minimal, customer-facing view of a currently-live promotion the caller is eligible for."""

    promotion_id: uuid.UUID = Field(..., description="Promotion UUID.")
    name: str = Field(..., description="Promotion name shown to the customer.")
    dish_id: uuid.UUID = Field(..., description="Discounted dish UUID.")
    dish_name: str = Field(..., description="Dish name.")
    special_price: float = Field(..., description="Promotional price in INR.")
    segment: str = Field(..., description="Segment this promotion targets (informational).")


class ActivePromotionListResponse(BaseModel):
    """Currently-live promotions visible to the caller, filtered by segment eligibility."""

    promotions: list[ActivePromotionResponse] = Field(
        ..., description="Live promotions the caller (or anonymous public caller) is eligible for right now."
    )


def customer_to_response(row: KitchenCustomer) -> KitchenCustomerResponse:
    fav = row.favorite_dishes or []
    patterns = row.order_patterns or {}
    return KitchenCustomerResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        customer_id=row.customer_id,
        customer_phone=row.customer_phone,
        customer_name=row.customer_name,
        total_spend=round(float(row.total_spend), 2),
        monthly_spend=round(float(row.monthly_spend), 2),
        order_count=int(row.order_count),
        favorite_dishes=[FavoriteDish(**f) for f in fav],
        order_patterns=OrderPatterns(**patterns) if patterns else OrderPatterns(),
        tags=list(row.tags or []),
        last_order_at=row.last_order_at,
    )


def coupon_to_response(row: Coupon) -> CouponResponse:
    return CouponResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        code=row.code,
        discount_type=row.discount_type,
        discount_value=round(float(row.discount_value), 2),
        min_order_amount=(
            round(float(row.min_order_amount), 2) if row.min_order_amount is not None else None
        ),
        max_uses=row.max_uses,
        used_count=int(row.used_count),
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        is_active=bool(row.is_active),
        created_at=row.created_at,
    )


def promotion_to_response(row: Promotion) -> PromotionResponse:
    return PromotionResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        name=row.name,
        dish_id=row.dish_id,
        dish_name=row.dish_name,
        special_price=round(float(row.special_price), 2),
        segment=row.segment,
        segment_limit=row.segment_limit,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        is_active=bool(row.is_active),
        created_at=row.created_at,
    )


def _month_start_utc() -> datetime:
    now_local = datetime.now(LOCAL_TZ)
    start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(UTC)


async def sync_crm_from_orders(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    publisher: EventPublisher,
) -> datetime:
    month_start = _month_start_utc()
    agg_rows = (
        await session.execute(
            text(
                """
                SELECT
                    o.customer_phone,
                    MAX(o.customer_name) AS customer_name,
                    COUNT(*) AS order_count,
                    COALESCE(SUM(o.total), 0) AS total_spend,
                    COALESCE(SUM(o.total) FILTER (WHERE o.created_at >= :month_start), 0)
                        AS monthly_spend,
                    MAX(o.created_at) AS last_order_at
                FROM ckac_orders.orders o
                WHERE o.kitchen_id = :kid
                  AND o.status <> 'cancelled'
                  AND o.customer_phone IS NOT NULL
                GROUP BY o.customer_phone
                """
            ),
            {"kid": kitchen_id, "month_start": month_start},
        )
    ).mappings().all()

    synced_at = datetime.now(UTC)
    for row in agg_rows:
        phone = row["customer_phone"]
        fav_rows = (
            await session.execute(
                text(
                    """
                    SELECT
                        oi.dish_id,
                        oi.dish_name,
                        SUM(oi.quantity)::int AS quantity
                    FROM ckac_orders.order_items oi
                    JOIN ckac_orders.orders o ON o.id = oi.order_id
                    WHERE o.kitchen_id = :kid
                      AND o.customer_phone = :phone
                      AND o.status <> 'cancelled'
                    GROUP BY oi.dish_id, oi.dish_name
                    ORDER BY quantity DESC
                    LIMIT 5
                    """
                ),
                {"kid": kitchen_id, "phone": phone},
            )
        ).mappings().all()
        favorite_dishes = [
            {
                "dish_id": str(r["dish_id"]),
                "dish_name": r["dish_name"],
                "quantity": int(r["quantity"]),
            }
            for r in fav_rows
        ]

        pattern_row = (
            await session.execute(
                text(
                    """
                    SELECT
                        ARRAY(
                            SELECT EXTRACT(HOUR FROM (created_at AT TIME ZONE 'Asia/Kolkata'))::int
                            FROM ckac_orders.orders
                            WHERE kitchen_id = :kid AND customer_phone = :phone
                              AND status <> 'cancelled'
                            GROUP BY 1
                            ORDER BY COUNT(*) DESC
                            LIMIT 3
                        ) AS peak_hours,
                        COUNT(*) FILTER (
                            WHERE EXTRACT(DOW FROM (created_at AT TIME ZONE 'Asia/Kolkata')) IN (0, 6)
                        )::int AS weekend_orders,
                        COUNT(*) FILTER (
                            WHERE EXTRACT(DOW FROM (created_at AT TIME ZONE 'Asia/Kolkata')) NOT IN (0, 6)
                        )::int AS weekday_orders
                    FROM ckac_orders.orders
                    WHERE kitchen_id = :kid AND customer_phone = :phone
                      AND status <> 'cancelled'
                    """
                ),
                {"kid": kitchen_id, "phone": phone},
            )
        ).mappings().one()

        cust_id_result = await session.execute(
            text(
                "SELECT id FROM ckac_identity.customers WHERE phone = :phone LIMIT 1"
            ),
            {"phone": phone},
        )
        customer_id = cust_id_result.scalar_one_or_none()

        existing = await session.execute(
            select(KitchenCustomer).where(
                KitchenCustomer.kitchen_id == kitchen_id,
                KitchenCustomer.customer_phone == phone,
            )
        )
        profile = existing.scalar_one_or_none()
        if profile:
            profile.customer_id = customer_id
            profile.customer_name = row["customer_name"]
            profile.total_spend = float(row["total_spend"])
            profile.monthly_spend = float(row["monthly_spend"])
            profile.order_count = int(row["order_count"])
            profile.favorite_dishes = favorite_dishes
            profile.order_patterns = {
                "peak_hours": list(pattern_row["peak_hours"] or []),
                "weekday_orders": int(pattern_row["weekday_orders"] or 0),
                "weekend_orders": int(pattern_row["weekend_orders"] or 0),
            }
            profile.last_order_at = row["last_order_at"]
            profile.updated_at = synced_at
        else:
            session.add(
                KitchenCustomer(
                    kitchen_id=kitchen_id,
                    customer_id=customer_id,
                    customer_phone=phone,
                    customer_name=row["customer_name"],
                    total_spend=float(row["total_spend"]),
                    monthly_spend=float(row["monthly_spend"]),
                    order_count=int(row["order_count"]),
                    favorite_dishes=favorite_dishes,
                    order_patterns={
                        "peak_hours": list(pattern_row["peak_hours"] or []),
                        "weekday_orders": int(pattern_row["weekday_orders"] or 0),
                        "weekend_orders": int(pattern_row["weekend_orders"] or 0),
                    },
                    last_order_at=row["last_order_at"],
                    updated_at=synced_at,
                )
            )

    await session.flush()
    event = EventPublisher.build(
        event_type="crm.synced",
        aggregate_type="kitchen_crm",
        aggregate_id=str(kitchen_id),
        producer="marketing-service",
        payload={"kitchen_id": str(kitchen_id), "customer_count": len(agg_rows)},
    )
    await publisher.publish(stream_key("marketing", "crm"), event, session=session)
    return synced_at


async def list_kitchen_customers(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    *,
    refresh: bool,
    publisher: EventPublisher,
) -> KitchenCustomerListResponse:
    synced_at = None
    if refresh:
        synced_at = await sync_crm_from_orders(session, kitchen_id, publisher)
        await session.commit()

    result = await session.execute(
        select(KitchenCustomer)
        .where(KitchenCustomer.kitchen_id == kitchen_id)
        .order_by(KitchenCustomer.total_spend.desc())
    )
    rows = result.scalars().all()
    return KitchenCustomerListResponse(
        customers=[customer_to_response(r) for r in rows],
        total=len(rows),
        synced_at=synced_at,
    )


async def update_customer_tags(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    customer_id: uuid.UUID,
    body: KitchenCustomerTagsUpdate,
) -> KitchenCustomerResponse:
    result = await session.execute(
        select(KitchenCustomer).where(
            KitchenCustomer.id == customer_id,
            KitchenCustomer.kitchen_id == kitchen_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise ValueError("Customer not found")
    row.tags = body.tags
    row.updated_at = datetime.now(UTC)
    await session.flush()
    return customer_to_response(row)


async def create_coupon(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    body: CouponCreateRequest,
    publisher: EventPublisher,
) -> Coupon:
    existing = await session.execute(
        select(Coupon).where(Coupon.kitchen_id == kitchen_id, Coupon.code == body.code)
    )
    if existing.scalar_one_or_none():
        raise ValueError("Coupon code already exists")

    coupon = Coupon(
        kitchen_id=kitchen_id,
        code=body.code,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        min_order_amount=body.min_order_amount,
        max_uses=body.max_uses,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    session.add(coupon)
    await session.flush()

    event = EventPublisher.build(
        event_type="coupon.created",
        aggregate_type="coupon",
        aggregate_id=str(coupon.id),
        producer="marketing-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "code": coupon.code,
            "discount_type": coupon.discount_type,
            "discount_value": float(coupon.discount_value),
        },
    )
    await publisher.publish(stream_key("marketing", "coupon"), event, session=session)
    return coupon


async def list_coupons(session: AsyncSession, kitchen_id: uuid.UUID) -> CouponListResponse:
    result = await session.execute(
        select(Coupon)
        .where(Coupon.kitchen_id == kitchen_id)
        .order_by(Coupon.created_at.desc())
    )
    rows = result.scalars().all()
    return CouponListResponse(
        coupons=[coupon_to_response(r) for r in rows],
        total=len(rows),
    )


async def update_coupon(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    coupon_id: uuid.UUID,
    body: CouponUpdateRequest,
) -> Coupon:
    result = await session.execute(
        select(Coupon).where(Coupon.id == coupon_id, Coupon.kitchen_id == kitchen_id)
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise ValueError("Coupon not found")
    coupon.is_active = body.is_active
    await session.flush()
    return coupon


def _coupon_discount_amount(coupon: Coupon, subtotal: float) -> float:
    if coupon.discount_type == "percent":
        return round(subtotal * float(coupon.discount_value) / 100, 2)
    return round(min(float(coupon.discount_value), subtotal), 2)


async def validate_coupon(
    session: AsyncSession,
    body: CouponValidateRequest,
) -> CouponValidateResponse:
    result = await session.execute(
        select(Coupon).where(
            Coupon.kitchen_id == body.kitchen_id,
            Coupon.code == body.code,
        )
    )
    coupon = result.scalar_one_or_none()
    if not coupon:
        return CouponValidateResponse(valid=False, message="Invalid coupon code")

    now = datetime.now(UTC)
    if not coupon.is_active:
        return CouponValidateResponse(valid=False, message="Coupon is inactive")
    if coupon.valid_from and now < coupon.valid_from:
        return CouponValidateResponse(valid=False, message="Coupon not yet valid")
    if coupon.valid_until and now > coupon.valid_until:
        return CouponValidateResponse(valid=False, message="Coupon expired")
    if coupon.max_uses is not None and coupon.used_count >= coupon.max_uses:
        return CouponValidateResponse(valid=False, message="Coupon usage limit reached")
    if coupon.min_order_amount is not None and body.subtotal < float(coupon.min_order_amount):
        return CouponValidateResponse(
            valid=False,
            message=f"Minimum order ₹{float(coupon.min_order_amount):.0f} required",
        )

    discount = _coupon_discount_amount(coupon, body.subtotal)
    return CouponValidateResponse(
        valid=True,
        coupon_id=coupon.id,
        code=coupon.code,
        discount_type=coupon.discount_type,
        discount_amount=discount,
        message="Coupon applied",
    )


async def _load_dish_name(session: AsyncSession, kitchen_id: uuid.UUID, dish_id: uuid.UUID) -> str:
    result = await session.execute(
        text(
            "SELECT name FROM ckac_catalog.dishes "
            "WHERE id = :did AND kitchen_id = :kid LIMIT 1"
        ),
        {"did": dish_id, "kid": kitchen_id},
    )
    name = result.scalar_one_or_none()
    if not name:
        raise ValueError("Dish not found for this kitchen")
    return name


async def create_promotion(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    body: PromotionCreateRequest,
    publisher: EventPublisher,
) -> Promotion:
    dish_name = await _load_dish_name(session, kitchen_id, body.dish_id)
    if body.segment == "top_spenders" and not body.segment_limit:
        raise ValueError("segment_limit required for top_spenders")

    promo = Promotion(
        kitchen_id=kitchen_id,
        name=body.name,
        dish_id=body.dish_id,
        dish_name=dish_name,
        special_price=body.special_price,
        segment=body.segment,
        segment_limit=body.segment_limit,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    session.add(promo)
    await session.flush()

    event = EventPublisher.build(
        event_type="promotion.created",
        aggregate_type="promotion",
        aggregate_id=str(promo.id),
        producer="marketing-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "dish_id": str(body.dish_id),
            "segment": body.segment,
            "special_price": float(body.special_price),
        },
    )
    await publisher.publish(stream_key("marketing", "promotion"), event, session=session)
    return promo


async def list_promotions(session: AsyncSession, kitchen_id: uuid.UUID) -> PromotionListResponse:
    result = await session.execute(
        select(Promotion)
        .where(Promotion.kitchen_id == kitchen_id)
        .order_by(Promotion.created_at.desc())
    )
    rows = result.scalars().all()
    return PromotionListResponse(
        promotions=[promotion_to_response(r) for r in rows],
        total=len(rows),
    )


def _customer_in_segment(profile: KitchenCustomer | None, segment: str, rank: int | None) -> bool:
    if segment == "all":
        return True
    if not profile:
        return False
    orders = int(profile.order_count)
    if segment == "repeat":
        return orders >= 2
    if segment == "vip":
        return orders >= 5
    if segment == "churn_risk":
        if orders < 2 or not profile.last_order_at:
            return False
        cutoff = datetime.now(UTC) - timedelta(days=CHURN_INACTIVE_DAYS)
        return profile.last_order_at < cutoff
    if segment == "top_spenders":
        return rank is not None
    return False


async def list_active_promotions(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    customer_phone: str | None,
) -> ActivePromotionListResponse:
    now = datetime.now(UTC)
    result = await session.execute(
        select(Promotion).where(
            Promotion.kitchen_id == kitchen_id,
            Promotion.is_active.is_(True),
            Promotion.starts_at <= now,
            Promotion.ends_at >= now,
        )
    )
    promos = result.scalars().all()
    if not promos:
        return ActivePromotionListResponse(promotions=[])

    profile: KitchenCustomer | None = None
    rank: int | None = None
    if customer_phone:
        prof_result = await session.execute(
            select(KitchenCustomer).where(
                KitchenCustomer.kitchen_id == kitchen_id,
                KitchenCustomer.customer_phone == customer_phone,
            )
        )
        profile = prof_result.scalar_one_or_none()
        if profile:
            rank_result = await session.execute(
                text(
                    """
                    SELECT COUNT(*) + 1
                    FROM ckac_marketing.kitchen_customers
                    WHERE kitchen_id = :kid AND total_spend > :spend
                    """
                ),
                {"kid": kitchen_id, "spend": profile.total_spend},
            )
            rank = int(rank_result.scalar_one())

    active: list[ActivePromotionResponse] = []
    for promo in promos:
        seg = promo.segment
        include = False
        if seg == "all":
            include = True
        elif seg == "top_spenders":
            limit = promo.segment_limit or 20
            include = rank is not None and rank <= limit
        else:
            include = _customer_in_segment(profile, seg, rank)
        if not include:
            continue
        active.append(
            ActivePromotionResponse(
                promotion_id=promo.id,
                name=promo.name,
                dish_id=promo.dish_id,
                dish_name=promo.dish_name,
                special_price=round(float(promo.special_price), 2),
                segment=promo.segment,
            )
        )
    return ActivePromotionListResponse(promotions=active)
