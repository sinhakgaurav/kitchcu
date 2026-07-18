"""Growth intelligence domain — combos, patterns, suggestions, daily menu (F09–F11, F39)."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from itertools import combinations
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from sqlalchemy import bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GoldenRecipePin, SeasonalPattern, Suggestion
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

LOCAL_TZ = ZoneInfo("Asia/Kolkata")
CHURN_INACTIVE_DAYS = 21
DAY_NAMES = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")


class DishCombo(BaseModel):
    """One dish pair frequently ordered together, mined from delivered multi-item orders (F09)."""

    dish_a_id: uuid.UUID = Field(..., description="First dish in the pair.")
    dish_a_name: str = Field(..., description="First dish's name.")
    dish_b_id: uuid.UUID = Field(..., description="Second dish in the pair.")
    dish_b_name: str = Field(..., description="Second dish's name.")
    pair_count: int = Field(..., description="Number of multi-item orders containing both dishes.", examples=[14])
    support_pct: float = Field(..., description="`pair_count` / total multi-item orders in the window, as a percent.", examples=[32.5])
    suggested_bundle_price: float | None = Field(default=None, description="Reserved for a future suggested combo price; currently always null.")


class DishCombosResponse(BaseModel):
    """Top dish-pairing opportunities for a kitchen over a lookback window."""

    window_days: int = Field(..., description="Lookback window in days used for this analysis.")
    multi_item_orders: int = Field(..., description="Total delivered orders with 2+ distinct dishes in the window — the denominator for `support_pct`.")
    combos: list[DishCombo] = Field(..., description="Top dish pairs by pair count, most frequent first.")


class DayPattern(BaseModel):
    """Order volume/revenue for one day of the week within the analysis window."""

    day_of_week: int = Field(..., description="0=Sunday .. 6=Saturday (IST).")
    day_name: str = Field(..., description="Day name, e.g. 'Saturday'.")
    orders: int = Field(..., description="Non-cancelled order count on this weekday within the window.")
    revenue: float = Field(..., description="Total order value (INR) on this weekday within the window.")


class HourPattern(BaseModel):
    """Order volume for one hour of the day (IST) within the analysis window."""

    hour: int = Field(..., description="Hour of day, 0-23 (IST).")
    orders: int = Field(..., description="Non-cancelled order count in this hour within the window.")


class OrderPatternsResponse(BaseModel):
    """Day/hour order distribution + a plain-language operational insight (F10)."""

    window_days: int = Field(..., description="Lookback window in days used for this analysis.")
    days: list[DayPattern] = Field(..., description="Per-weekday order/revenue breakdown.")
    peak_hours: list[HourPattern] = Field(..., description="Per-hour order counts.")
    insight: str = Field(..., description="Auto-generated, human-readable takeaway, e.g. staffing/prep guidance.", examples=["Mostly orders on Saturday — peak around 20:00 (dinner). Consider prepping more for Saturday dinner rush."])


class SuggestionResponse(BaseModel):
    """An actionable, auto-generated growth suggestion for the owner (F11)."""

    id: uuid.UUID = Field(..., description="Suggestion UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Kitchen this suggestion was generated for.")
    suggestion_type: str = Field(
        ...,
        description=(
            "Category: 'customer_winback', 'combo_opportunity', 'peak_staffing', 'seasonal', "
            "'dish_promo', or 'golden_performance_day'."
        ),
        examples=["combo_opportunity"],
    )
    title: str = Field(..., description="Short suggestion headline.")
    description: str = Field(..., description="Full human-readable explanation and recommended action.")
    action_payload: dict = Field(..., description="Structured data backing the suggestion (e.g. dish IDs, counts) for the owner UI to act on directly.")
    priority: int = Field(..., description="Relative priority score, higher = more urgent/impactful. Used for display ordering.", examples=[80])
    dismissed: bool = Field(..., description="Whether the owner has dismissed this suggestion.")
    created_at: datetime = Field(..., description="Generation timestamp, UTC.")

    model_config = {"from_attributes": True}


class SuggestionListResponse(BaseModel):
    """Roster of growth suggestions for a kitchen."""

    suggestions: list[SuggestionResponse] = Field(..., description="Suggestions ordered by priority descending, then newest first.")
    total: int = Field(..., description="Number of suggestions returned.")


class SuggestionUpdateRequest(BaseModel):
    """Owner request to dismiss (or un-dismiss) a suggestion."""

    dismissed: bool = Field(default=True, description="Set true to hide the suggestion from the default list view.")


class GoldenRecipePinResponse(BaseModel):
    """Pinned recipe/ingredient combo from a standout performance day."""

    id: uuid.UUID = Field(..., description="Pin UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen.")
    dish_id: uuid.UUID = Field(..., description="Dish the golden recipe belongs to.")
    suggestion_id: uuid.UUID | None = Field(default=None, description="Source golden-day suggestion, if any.")
    performance_date: date = Field(..., description="Calendar day (IST) of the standout performance.")
    dish_name: str = Field(..., description="Dish name at pin time.")
    recipe_snapshot: dict = Field(..., description="Ingredient lines + prep steps captured that day.")
    metrics: dict = Field(..., description="Order qty, rating, sentiment snapshot.")
    created_at: datetime = Field(..., description="When the owner saved this pin.")

    model_config = {"from_attributes": True}


class GoldenRecipePinListResponse(BaseModel):
    pins: list[GoldenRecipePinResponse] = Field(..., description="Golden recipe pins, newest performance day first.")
    total: int = Field(..., description="Number of pins returned.")


class SeasonalPatternResponse(BaseModel):
    """Reference data — seasonal/regional demand uplift for a dish category (used to generate seasonal suggestions)."""

    id: uuid.UUID = Field(..., description="Pattern row UUID.")
    region: str = Field(..., description="Region this pattern applies to, e.g. 'india'.")
    season_event: str = Field(..., description="Named season/event, e.g. 'monsoon', 'diwali'.")
    dish_category: str = Field(..., description="Dish category expected to see uplift.")
    demand_multiplier: float = Field(..., description="Expected demand multiplier vs baseline (e.g. 1.3 = +30%).", examples=[1.3])
    sample_dishes: list[str] = Field(..., description="Example dish names illustrating the category.")

    model_config = {"from_attributes": True}


class SeasonalPatternListResponse(BaseModel):
    """Reference seasonal patterns for a region, ranked by demand multiplier."""

    patterns: list[SeasonalPatternResponse] = Field(..., description="Patterns ordered by `demand_multiplier` descending.")
    total: int = Field(..., description="Number of patterns returned.")


class DailyMenuPushRequest(BaseModel):
    """Owner request to WhatsApp-blast today's menu to the kitchen's CRM roster (F39)."""

    dish_ids: list[uuid.UUID] = Field(min_length=1, max_length=20, description="1-20 active dish IDs to feature; each must belong to and be active on this kitchen.")
    message: str | None = Field(default=None, max_length=500, description="Custom blast message; auto-generated from the dish list if omitted.")


class DailyMenuPushResponse(BaseModel):
    """Result of queuing a daily-menu WhatsApp blast."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen the blast was sent for.")
    dish_ids: list[uuid.UUID] = Field(..., description="Dish IDs included in the blast.")
    dish_names: list[str] = Field(..., description="Resolved dish names, in the same order as `dish_ids`.")
    recipient_count: int = Field(..., description="Number of CRM-known customers targeted.", examples=[42])
    message: str = Field(..., description="Final WhatsApp message text sent (custom or auto-generated).")
    status: str = Field(..., description="Always 'queued' — the notification service dispatches asynchronously.")


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

    from app.golden_day import GOLDEN_WINDOW_DAYS, build_golden_suggestion, detect_golden_days

    golden_window = min(GOLDEN_WINDOW_DAYS, days)
    for candidate in await detect_golden_days(session, kitchen_id, window_days=golden_window):
        row = build_golden_suggestion(kitchen_id, candidate)
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


async def accept_golden_recipe(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    publisher: EventPublisher,
) -> GoldenRecipePinResponse:
    from app.golden_day import pin_golden_recipe

    pin = await pin_golden_recipe(session, kitchen_id, suggestion_id)
    event = publisher.build(
        event_type="golden_recipe.pinned",
        aggregate_type="golden_recipe",
        aggregate_id=str(pin.id),
        producer="growth-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "dish_id": str(pin.dish_id),
            "performance_date": pin.performance_date.isoformat(),
            "suggestion_id": str(suggestion_id),
        },
    )
    await publisher.publish(stream_key("growth", "suggestion"), event, session=session)
    return _golden_pin_to_response(pin)


async def list_golden_recipe_pins(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID | None = None,
) -> GoldenRecipePinListResponse:
    from app.golden_day import list_golden_pins

    pins = await list_golden_pins(session, kitchen_id, dish_id=dish_id)
    return GoldenRecipePinListResponse(
        pins=[_golden_pin_to_response(p) for p in pins],
        total=len(pins),
    )


def _golden_pin_to_response(pin: GoldenRecipePin) -> GoldenRecipePinResponse:
    return GoldenRecipePinResponse(
        id=pin.id,
        kitchen_id=pin.kitchen_id,
        dish_id=pin.dish_id,
        suggestion_id=pin.suggestion_id,
        performance_date=pin.performance_date,
        dish_name=pin.dish_name,
        recipe_snapshot=pin.recipe_snapshot or {},
        metrics=pin.metrics or {},
        created_at=pin.created_at,
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
