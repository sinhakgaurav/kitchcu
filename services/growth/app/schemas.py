"""Growth intelligence domain — combos, patterns, suggestions, daily menu (F09–F11, F39)."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from itertools import combinations
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from sqlalchemy import bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SeasonalPattern, Suggestion
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

LOCAL_TZ = ZoneInfo("Asia/Kolkata")
CHURN_INACTIVE_DAYS = 21
DAY_NAMES = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


class DishCombo(BaseModel):
    dish_a_id: uuid.UUID
    dish_a_name: str
    dish_b_id: uuid.UUID
    dish_b_name: str
    pair_count: int
    support_pct: float
    suggested_bundle_price: float | None = None


class DishCombosResponse(BaseModel):
    window_days: int
    multi_item_orders: int
    combos: list[DishCombo]


class DayPattern(BaseModel):
    day_of_week: int
    day_name: str
    orders: int
    revenue: float


class HourPattern(BaseModel):
    hour: int
    orders: int


class OrderPatternsResponse(BaseModel):
    window_days: int
    days: list[DayPattern]
    peak_hours: list[HourPattern]
    insight: str


class SuggestionResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    suggestion_type: str
    title: str
    description: str
    action_payload: dict
    priority: int
    dismissed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SuggestionListResponse(BaseModel):
    suggestions: list[SuggestionResponse]
    total: int


class SuggestionUpdateRequest(BaseModel):
    dismissed: bool = True


class SeasonalPatternResponse(BaseModel):
    id: uuid.UUID
    region: str
    season_event: str
    dish_category: str
    demand_multiplier: float
    sample_dishes: list[str]

    model_config = {"from_attributes": True}


class SeasonalPatternListResponse(BaseModel):
    patterns: list[SeasonalPatternResponse]
    total: int


class DailyMenuPushRequest(BaseModel):
    dish_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    message: str | None = Field(default=None, max_length=500)


class DailyMenuPushResponse(BaseModel):
    kitchen_id: uuid.UUID
    dish_ids: list[uuid.UUID]
    dish_names: list[str]
    recipient_count: int
    message: str
    status: str


def _window_start(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def suggestion_to_response(row: Suggestion) -> SuggestionResponse:
    return SuggestionResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        suggestion_type=row.suggestion_type,
        title=row.title,
        description=row.description,
        action_payload=row.action_payload or {},
        priority=row.priority,
        dismissed=row.dismissed,
        created_at=row.created_at,
    )


async def dish_combinations(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    days: int = 90,
    limit: int = 5,
) -> DishCombosResponse:
    since = _window_start(days)
    rows = (
        await session.execute(
            text(
                """
                SELECT oi.order_id, oi.dish_id, oi.dish_name
                FROM ckac_orders.order_items oi
                JOIN ckac_orders.orders o ON o.id = oi.order_id
                WHERE o.kitchen_id = :kid
                  AND o.status = 'delivered'
                  AND o.created_at >= :since
                ORDER BY oi.order_id, oi.dish_id
                """
            ),
            {"kid": kitchen_id, "since": since},
        )
    ).mappings().all()

    by_order: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = {}
    for row in rows:
        oid = row["order_id"]
        by_order.setdefault(oid, []).append((row["dish_id"], row["dish_name"]))

    multi_orders = {oid: items for oid, items in by_order.items() if len({d[0] for d in items}) >= 2}
    pair_counter: Counter[tuple[uuid.UUID, uuid.UUID]] = Counter()
    pair_names: dict[tuple[uuid.UUID, uuid.UUID], tuple[str, str]] = {}

    for items in multi_orders.values():
        unique = {dish_id: name for dish_id, name in items}
        dish_ids = sorted(unique.keys(), key=str)
        for a, b in combinations(dish_ids, 2):
            pair_counter[(a, b)] += 1
            pair_names[(a, b)] = (unique[a], unique[b])

    total_multi = len(multi_orders)
    combos: list[DishCombo] = []
    for (a, b), count in pair_counter.most_common(limit):
        names = pair_names[(a, b)]
        support = round(count / total_multi * 100, 1) if total_multi else 0.0
        combos.append(
            DishCombo(
                dish_a_id=a,
                dish_a_name=names[0],
                dish_b_id=b,
                dish_b_name=names[1],
                pair_count=count,
                support_pct=support,
            )
        )

    return DishCombosResponse(
        window_days=days,
        multi_item_orders=total_multi,
        combos=combos,
    )


async def order_patterns(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    days: int = 90,
) -> OrderPatternsResponse:
    since = _window_start(days)
    day_rows = (
        await session.execute(
            text(
                """
                SELECT
                    EXTRACT(DOW FROM created_at AT TIME ZONE :tz)::int AS dow,
                    COUNT(*) AS orders,
                    COALESCE(SUM(total), 0) AS revenue
                FROM ckac_orders.orders
                WHERE kitchen_id = :kid
                  AND status <> 'cancelled'
                  AND created_at >= :since
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"kid": kitchen_id, "since": since, "tz": str(LOCAL_TZ)},
        )
    ).mappings().all()

    hour_rows = (
        await session.execute(
            text(
                """
                SELECT
                    EXTRACT(HOUR FROM created_at AT TIME ZONE :tz)::int AS hour,
                    COUNT(*) AS orders
                FROM ckac_orders.orders
                WHERE kitchen_id = :kid
                  AND status <> 'cancelled'
                  AND created_at >= :since
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"kid": kitchen_id, "since": since, "tz": str(LOCAL_TZ)},
        )
    ).mappings().all()

    days_list = [
        DayPattern(
            day_of_week=int(r["dow"]),
            day_name=DAY_NAMES[int(r["dow"])],
            orders=int(r["orders"]),
            revenue=round(float(r["revenue"]), 2),
        )
        for r in day_rows
    ]
    peak_hours = [
        HourPattern(hour=int(r["hour"]), orders=int(r["orders"]))
        for r in hour_rows
    ]

    insight = "Not enough order history yet for pattern insights."
    if days_list:
        busiest = max(days_list, key=lambda d: d.orders)
        if peak_hours:
            peak = max(peak_hours, key=lambda h: h.orders)
            meal = "lunch" if 11 <= peak.hour <= 14 else "dinner" if 18 <= peak.hour <= 21 else "day"
            insight = (
                f"Mostly orders on {busiest.day_name} — peak around {peak.hour}:00 ({meal}). "
                f"Consider prepping more for {busiest.day_name} {meal} rush."
            )
        else:
            insight = f"Mostly orders on {busiest.day_name}."

    return OrderPatternsResponse(
        window_days=days,
        days=days_list,
        peak_hours=peak_hours,
        insight=insight,
    )


async def list_suggestions(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    include_dismissed: bool = False,
) -> SuggestionListResponse:
    stmt = select(Suggestion).where(Suggestion.kitchen_id == kitchen_id)
    if not include_dismissed:
        stmt = stmt.where(Suggestion.dismissed.is_(False))
    stmt = stmt.order_by(Suggestion.priority.desc(), Suggestion.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()
    items = [suggestion_to_response(r) for r in rows]
    return SuggestionListResponse(suggestions=items, total=len(items))


async def _count_churn_risk(session: AsyncSession, kitchen_id: uuid.UUID) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=CHURN_INACTIVE_DAYS)
    return int(
        (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM (
                        SELECT customer_phone
                        FROM ckac_orders.orders
                        WHERE kitchen_id = :kid
                          AND status <> 'cancelled'
                          AND customer_phone IS NOT NULL
                        GROUP BY customer_phone
                        HAVING COUNT(*) >= 2
                           AND MAX(created_at) < :cutoff
                    ) at_risk
                    """
                ),
                {"kid": kitchen_id, "cutoff": cutoff},
            )
        ).scalar_one()
    )


async def _dish_promo_candidates(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    days: int,
) -> list[dict]:
    since = _window_start(days)
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    d.id AS dish_id,
                    d.name AS dish_name,
                    d.price,
                    COALESCE(a.overall_rating, 0) AS overall_rating,
                    COALESCE(SUM(oi.quantity), 0) AS qty_sold
                FROM ckac_catalog.dishes d
                LEFT JOIN ckac_ratings.dish_rating_aggregates a
                    ON a.dish_id = d.id AND a.kitchen_id = d.kitchen_id
                LEFT JOIN ckac_orders.order_items oi ON oi.dish_id = d.id
                LEFT JOIN ckac_orders.orders o
                    ON o.id = oi.order_id
                   AND o.kitchen_id = :kid
                   AND o.status = 'delivered'
                   AND o.created_at >= :since
                WHERE d.kitchen_id = :kid AND d.is_active = true
                GROUP BY d.id, d.name, d.price, a.overall_rating
                HAVING COALESCE(a.overall_rating, 0) >= 4.0
                   AND COALESCE(SUM(oi.quantity), 0) <= 10
                ORDER BY a.overall_rating DESC NULLS LAST
                LIMIT 3
                """
            ),
            {"kid": kitchen_id, "since": since},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def generate_suggestions(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    publisher: EventPublisher,
    days: int = 90,
) -> SuggestionListResponse:
    created: list[Suggestion] = []

    churn_count = await _count_churn_risk(session, kitchen_id)
    if churn_count > 0:
        row = Suggestion(
            kitchen_id=kitchen_id,
            suggestion_type="customer_winback",
            title="Win back loyal customers",
            description=(
                f"{churn_count} repeat customers haven't ordered in {CHURN_INACTIVE_DAYS}+ days. "
                "Send them a coupon from CRM."
            ),
            action_payload={"churn_count": churn_count, "suggested_coupon_pct": 15},
            priority=80,
        )
        session.add(row)
        created.append(row)

    combos = await dish_combinations(session, kitchen_id, days=days, limit=1)
    if combos.combos and combos.combos[0].support_pct >= 30.0:
        top = combos.combos[0]
        row = Suggestion(
            kitchen_id=kitchen_id,
            suggestion_type="combo_opportunity",
            title=f"Bundle {top.dish_a_name} + {top.dish_b_name}",
            description=(
                f"Customers who order {top.dish_a_name} also order {top.dish_b_name} "
                f"{top.support_pct:.0f}% of the time — create a combo."
            ),
            action_payload={
                "dish_a_id": str(top.dish_a_id),
                "dish_b_id": str(top.dish_b_id),
                "support_pct": top.support_pct,
            },
            priority=70,
        )
        session.add(row)
        created.append(row)

    patterns = await order_patterns(session, kitchen_id, days=days)
    if patterns.peak_hours:
        avg_orders = sum(h.orders for h in patterns.peak_hours) / len(patterns.peak_hours)
        peak = max(patterns.peak_hours, key=lambda h: h.orders)
        if peak.orders >= avg_orders * 2 and peak.orders >= 3:
            row = Suggestion(
                kitchen_id=kitchen_id,
                suggestion_type="peak_staffing",
                title=f"Peak at {peak.hour}:00 IST",
                description=(
                    f"{peak.hour}:00 sees {peak.orders} orders — "
                    f"{round(peak.orders / max(avg_orders, 1), 1)}× your hourly average. Prep extra portions."
                ),
                action_payload={"peak_hour": peak.hour, "orders": peak.orders},
                priority=60,
            )
            session.add(row)
            created.append(row)

    seasonal = (
        await session.execute(
            select(SeasonalPattern)
            .where(SeasonalPattern.region == "india")
            .order_by(SeasonalPattern.demand_multiplier.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if seasonal:
        samples = seasonal.sample_dishes or []
        sample_text = ", ".join(samples[:3]) if samples else seasonal.dish_category
        row = Suggestion(
            kitchen_id=kitchen_id,
            suggestion_type="seasonal",
            title=f"Seasonal opportunity: {seasonal.season_event.title()}",
            description=(
                f"Similar kitchens see {float(seasonal.demand_multiplier):.0%} uplift on "
                f"{seasonal.dish_category.replace('_', ' ')} — try {sample_text}."
            ),
            action_payload={
                "season_event": seasonal.season_event,
                "dish_category": seasonal.dish_category,
                "sample_dishes": samples,
            },
            priority=50,
        )
        session.add(row)
        created.append(row)

    for promo in await _dish_promo_candidates(session, kitchen_id, days):
        row = Suggestion(
            kitchen_id=kitchen_id,
            suggestion_type="dish_promo",
            title=f"Promote {promo['dish_name']}",
            description=(
                f"{promo['dish_name']} rates {float(promo['overall_rating']):.1f} but only "
                f"{int(promo['qty_sold'])} sold recently — feature it this week."
            ),
            action_payload={
                "dish_id": str(promo["dish_id"]),
                "suggested_price": float(promo["price"]),
            },
            priority=55,
        )
        session.add(row)
        created.append(row)

    await session.flush()

    for row in created:
        event = publisher.build(
            event_type="suggestion.generated",
            aggregate_type="suggestion",
            aggregate_id=str(row.id),
            producer="growth-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "suggestion_type": row.suggestion_type,
                "title": row.title,
            },
        )
        await publisher.publish(stream_key("growth", "suggestion"), event, session=session)

    return SuggestionListResponse(
        suggestions=[suggestion_to_response(r) for r in created],
        total=len(created),
    )


async def update_suggestion(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    dismissed: bool,
) -> SuggestionResponse:
    row = (
        await session.execute(
            select(Suggestion).where(
                Suggestion.id == suggestion_id,
                Suggestion.kitchen_id == kitchen_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise ValueError("Suggestion not found")
    row.dismissed = dismissed
    await session.flush()
    return suggestion_to_response(row)


async def list_seasonal_patterns(
    session: AsyncSession,
    region: str = "india",
) -> SeasonalPatternListResponse:
    rows = (
        await session.execute(
            select(SeasonalPattern)
            .where(SeasonalPattern.region == region.lower())
            .order_by(SeasonalPattern.demand_multiplier.desc())
        )
    ).scalars().all()
    patterns = [
        SeasonalPatternResponse(
            id=r.id,
            region=r.region,
            season_event=r.season_event,
            dish_category=r.dish_category,
            demand_multiplier=float(r.demand_multiplier),
            sample_dishes=r.sample_dishes or [],
        )
        for r in rows
    ]
    return SeasonalPatternListResponse(patterns=patterns, total=len(patterns))


async def push_daily_menu(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    body: DailyMenuPushRequest,
    publisher: EventPublisher,
) -> DailyMenuPushResponse:
    dish_stmt = (
        text(
            """
            SELECT id, name FROM ckac_catalog.dishes
            WHERE kitchen_id = :kid AND is_active = true AND id IN :dids
            """
        ).bindparams(bindparam("dids", expanding=True))
    )
    dish_rows = (
        await session.execute(dish_stmt, {"kid": kitchen_id, "dids": body.dish_ids})
    ).mappings().all()

    if len(dish_rows) != len(body.dish_ids):
        raise ValueError("One or more dishes not found or inactive")

    dish_names = [r["name"] for r in dish_rows]
    kitchen_name = (
        await session.execute(
            text("SELECT name FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none() or "Your kitchen"

    recipient_count = int(
        (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM ckac_marketing.kitchen_customers
                    WHERE kitchen_id = :kid
                    """
                ),
                {"kid": kitchen_id},
            )
        ).scalar_one()
    )

    menu_line = ", ".join(dish_names)
    message = body.message or f"Today's menu at {kitchen_name}: {menu_line}. Order on kitchCU!"

    event = publisher.build(
        event_type="daily_menu.blast_requested",
        aggregate_type="daily_menu",
        aggregate_id=str(kitchen_id),
        producer="growth-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "dish_ids": [str(d) for d in body.dish_ids],
            "dish_names": dish_names,
            "message": message,
            "recipient_count": recipient_count,
        },
    )
    await publisher.publish(stream_key("growth", "daily_menu"), event, session=session)

    return DailyMenuPushResponse(
        kitchen_id=kitchen_id,
        dish_ids=body.dish_ids,
        dish_names=dish_names,
        recipient_count=recipient_count,
        message=message,
        status="queued",
    )
