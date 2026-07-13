"""Owner growth analytics — revenue, dishes, peak hours, customer retention.

Read model over the order aggregate (owned by this service). Answers the
business questions CKAC owners care about: revenue trends, best-selling dishes,
busiest hours, repeat-customer rate, and churn risk — so home kitchens can grow
without depending on aggregators.

All time bucketing uses Asia/Kolkata so "today" and "peak hour" match the
owner's local day, which is what matters for a single-region cloud-kitchen SaaS.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Local time zone for day/hour bucketing (target market: India).
LOCAL_TZ = "Asia/Kolkata"

# A customer with no non-cancelled order in this many days (but 2+ lifetime
# orders) is flagged as churn risk so owners can win them back.
CHURN_INACTIVE_DAYS = 21


class RevenueSummary(BaseModel):
    window_days: int
    total_orders: int
    completed_orders: int
    delivered_orders: int
    cancelled_orders: int
    active_orders: int
    gross_revenue: float
    avg_order_value: float
    cancellation_rate: float
    unique_customers: int
    repeat_customers: int
    repeat_rate: float


class RevenuePoint(BaseModel):
    date: date
    revenue: float
    orders: int


class RevenueTimeseries(BaseModel):
    window_days: int
    points: list[RevenuePoint]


class TopDish(BaseModel):
    dish_id: uuid.UUID
    dish_name: str
    quantity: int
    revenue: float
    order_count: int


class TopDishes(BaseModel):
    window_days: int
    dishes: list[TopDish]


class PeakHour(BaseModel):
    hour: int
    orders: int
    revenue: float


class PeakHours(BaseModel):
    window_days: int
    hours: list[PeakHour]


class CustomerRow(BaseModel):
    customer_phone: str
    customer_name: str | None
    orders: int
    total_spent: float
    last_order_at: datetime


class CustomerSegments(BaseModel):
    window_days: int
    new_customers: int
    repeat_customers: int
    vip_customers: int
    top_customers: list[CustomerRow]
    churn_risk: list[CustomerRow]


def _window_start(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


async def revenue_summary(session: AsyncSession, kitchen_id: uuid.UUID, days: int) -> RevenueSummary:
    since = _window_start(days)
    row = (
        await session.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_orders,
                    COUNT(*) FILTER (WHERE status <> 'cancelled') AS completed_orders,
                    COUNT(*) FILTER (WHERE status = 'delivered') AS delivered_orders,
                    COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_orders,
                    COUNT(*) FILTER (
                        WHERE status NOT IN ('delivered', 'cancelled')
                    ) AS active_orders,
                    COALESCE(SUM(total) FILTER (WHERE status <> 'cancelled'), 0) AS gross_revenue,
                    COUNT(DISTINCT customer_phone) FILTER (
                        WHERE status <> 'cancelled' AND customer_phone IS NOT NULL
                    ) AS unique_customers
                FROM ckac_orders.orders
                WHERE kitchen_id = :kid AND created_at >= :since
                """
            ),
            {"kid": kitchen_id, "since": since},
        )
    ).mappings().one()

    repeat = (
        await session.execute(
            text(
                """
                SELECT COUNT(*) AS repeat_customers FROM (
                    SELECT customer_phone
                    FROM ckac_orders.orders
                    WHERE kitchen_id = :kid
                      AND created_at >= :since
                      AND status <> 'cancelled'
                      AND customer_phone IS NOT NULL
                    GROUP BY customer_phone
                    HAVING COUNT(*) >= 2
                ) repeat_buyers
                """
            ),
            {"kid": kitchen_id, "since": since},
        )
    ).scalar_one()

    total_orders = int(row["total_orders"])
    completed = int(row["completed_orders"])
    cancelled = int(row["cancelled_orders"])
    gross = float(row["gross_revenue"])
    unique_customers = int(row["unique_customers"])

    return RevenueSummary(
        window_days=days,
        total_orders=total_orders,
        completed_orders=completed,
        delivered_orders=int(row["delivered_orders"]),
        cancelled_orders=cancelled,
        active_orders=int(row["active_orders"]),
        gross_revenue=round(gross, 2),
        avg_order_value=round(gross / completed, 2) if completed else 0.0,
        cancellation_rate=round(cancelled / total_orders, 4) if total_orders else 0.0,
        unique_customers=unique_customers,
        repeat_customers=int(repeat),
        repeat_rate=round(int(repeat) / unique_customers, 4) if unique_customers else 0.0,
    )


async def revenue_timeseries(
    session: AsyncSession, kitchen_id: uuid.UUID, days: int
) -> RevenueTimeseries:
    since = _window_start(days)
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    (created_at AT TIME ZONE :tz)::date AS day,
                    COALESCE(SUM(total), 0) AS revenue,
                    COUNT(*) AS orders
                FROM ckac_orders.orders
                WHERE kitchen_id = :kid
                  AND created_at >= :since
                  AND status <> 'cancelled'
                GROUP BY day
                ORDER BY day
                """
            ),
            {"kid": kitchen_id, "since": since, "tz": LOCAL_TZ},
        )
    ).mappings().all()

    by_day = {r["day"]: r for r in rows}
    today = datetime.now(ZoneInfo(LOCAL_TZ)).date()
    points: list[RevenuePoint] = []
    for offset in range(days - 1, -1, -1):
        d = today - timedelta(days=offset)
        r = by_day.get(d)
        points.append(
            RevenuePoint(
                date=d,
                revenue=round(float(r["revenue"]), 2) if r else 0.0,
                orders=int(r["orders"]) if r else 0,
            )
        )
    return RevenueTimeseries(window_days=days, points=points)


async def top_dishes(
    session: AsyncSession, kitchen_id: uuid.UUID, days: int, limit: int
) -> TopDishes:
    since = _window_start(days)
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    i.dish_id,
                    i.dish_name,
                    SUM(i.quantity) AS quantity,
                    SUM(i.quantity * i.unit_price) AS revenue,
                    COUNT(DISTINCT o.id) AS order_count
                FROM ckac_orders.order_items i
                JOIN ckac_orders.orders o ON o.id = i.order_id
                WHERE o.kitchen_id = :kid
                  AND o.created_at >= :since
                  AND o.status <> 'cancelled'
                GROUP BY i.dish_id, i.dish_name
                ORDER BY revenue DESC
                LIMIT :limit
                """
            ),
            {"kid": kitchen_id, "since": since, "limit": limit},
        )
    ).mappings().all()

    return TopDishes(
        window_days=days,
        dishes=[
            TopDish(
                dish_id=r["dish_id"],
                dish_name=r["dish_name"],
                quantity=int(r["quantity"]),
                revenue=round(float(r["revenue"]), 2),
                order_count=int(r["order_count"]),
            )
            for r in rows
        ],
    )


async def peak_hours(session: AsyncSession, kitchen_id: uuid.UUID, days: int) -> PeakHours:
    since = _window_start(days)
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    EXTRACT(HOUR FROM (created_at AT TIME ZONE :tz))::int AS hour,
                    COUNT(*) AS orders,
                    COALESCE(SUM(total), 0) AS revenue
                FROM ckac_orders.orders
                WHERE kitchen_id = :kid
                  AND created_at >= :since
                  AND status <> 'cancelled'
                GROUP BY hour
                ORDER BY hour
                """
            ),
            {"kid": kitchen_id, "since": since, "tz": LOCAL_TZ},
        )
    ).mappings().all()

    by_hour = {int(r["hour"]): r for r in rows}
    hours = [
        PeakHour(
            hour=h,
            orders=int(by_hour[h]["orders"]) if h in by_hour else 0,
            revenue=round(float(by_hour[h]["revenue"]), 2) if h in by_hour else 0.0,
        )
        for h in range(24)
    ]
    return PeakHours(window_days=days, hours=hours)


async def customer_segments(
    session: AsyncSession, kitchen_id: uuid.UUID, days: int, limit: int
) -> CustomerSegments:
    since = _window_start(days)
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    customer_phone,
                    MAX(customer_name) AS customer_name,
                    COUNT(*) AS orders,
                    COALESCE(SUM(total), 0) AS total_spent,
                    MAX(created_at) AS last_order_at
                FROM ckac_orders.orders
                WHERE kitchen_id = :kid
                  AND created_at >= :since
                  AND status <> 'cancelled'
                  AND customer_phone IS NOT NULL
                GROUP BY customer_phone
                ORDER BY total_spent DESC
                """
            ),
            {"kid": kitchen_id, "since": since},
        )
    ).mappings().all()

    new_customers = repeat_customers = vip_customers = 0
    for r in rows:
        n = int(r["orders"])
        if n >= 5:
            vip_customers += 1
        elif n >= 2:
            repeat_customers += 1
        else:
            new_customers += 1

    top_customers = [_customer_row(r) for r in rows[:limit]]

    # Churn risk uses lifetime history, not just the window.
    cutoff = datetime.now(UTC) - timedelta(days=CHURN_INACTIVE_DAYS)
    churn_rows = (
        await session.execute(
            text(
                """
                SELECT
                    customer_phone,
                    MAX(customer_name) AS customer_name,
                    COUNT(*) AS orders,
                    COALESCE(SUM(total), 0) AS total_spent,
                    MAX(created_at) AS last_order_at
                FROM ckac_orders.orders
                WHERE kitchen_id = :kid
                  AND status <> 'cancelled'
                  AND customer_phone IS NOT NULL
                GROUP BY customer_phone
                HAVING COUNT(*) >= 2 AND MAX(created_at) < :cutoff
                ORDER BY total_spent DESC
                LIMIT :limit
                """
            ),
            {"kid": kitchen_id, "cutoff": cutoff, "limit": limit},
        )
    ).mappings().all()

    return CustomerSegments(
        window_days=days,
        new_customers=new_customers,
        repeat_customers=repeat_customers,
        vip_customers=vip_customers,
        top_customers=top_customers,
        churn_risk=[_customer_row(r) for r in churn_rows],
    )


def _customer_row(r) -> CustomerRow:
    return CustomerRow(
        customer_phone=r["customer_phone"],
        customer_name=r["customer_name"],
        orders=int(r["orders"]),
        total_spent=round(float(r["total_spent"]), 2),
        last_order_at=r["last_order_at"],
    )
