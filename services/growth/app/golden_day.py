"""Golden performance day detection — orders × ratings × ML comment sentiment."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.comment_sentiment import get_sentiment_model
from app.models import GoldenRecipePin, Suggestion

LOCAL_TZ = ZoneInfo("Asia/Kolkata")

GOLDEN_WINDOW_DAYS = 10
MIN_DAYS_WITH_ORDERS = 3
MIN_GOLDEN_QTY = 3
MIN_AVG_RATING = 4.3
MIN_SENTIMENT = 0.55
QTY_VS_MEDIAN_MULT = 1.8
SUGGESTION_TYPE = "golden_performance_day"


@dataclass(frozen=True)
class DishDayMetrics:
    dish_id: uuid.UUID
    dish_name: str
    day: date
    order_qty: int
    order_count: int
    avg_rating: float | None
    rating_count: int
    sentiment_score: float
    sentiment_label: str
    comment_count: int
    sample_comments: list[str]


@dataclass(frozen=True)
class GoldenDayCandidate:
    metrics: DishDayMetrics
    median_qty: float
    window_days: int
    recipe_snapshot: dict


async def _load_order_days(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    since: datetime,
) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    oi.dish_id,
                    oi.dish_name,
                    (o.created_at AT TIME ZONE 'Asia/Kolkata')::date AS day,
                    SUM(oi.quantity)::int AS order_qty,
                    COUNT(DISTINCT o.id)::int AS order_count
                FROM ckac_orders.order_items oi
                JOIN ckac_orders.orders o ON o.id = oi.order_id
                WHERE o.kitchen_id = :kid
                  AND o.status NOT IN ('cancelled')
                  AND o.created_at >= :since
                GROUP BY oi.dish_id, oi.dish_name, day
                """
            ),
            {"kid": kitchen_id, "since": since},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def _load_rating_days(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    since: datetime,
) -> dict[tuple[uuid.UUID, date], tuple[float, int]]:
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    dish_id,
                    (created_at AT TIME ZONE 'Asia/Kolkata')::date AS day,
                    AVG((home_taste_score + quality_score) / 2.0)::float AS avg_rating,
                    COUNT(*)::int AS rating_count
                FROM ckac_ratings.dish_ratings
                WHERE kitchen_id = :kid
                  AND moderation_status = 'approved'
                  AND created_at >= :since
                GROUP BY dish_id, day
                """
            ),
            {"kid": kitchen_id, "since": since},
        )
    ).mappings().all()
    out: dict[tuple[uuid.UUID, date], tuple[float, int]] = {}
    for r in rows:
        out[(r["dish_id"], r["day"])] = (float(r["avg_rating"]), int(r["rating_count"]))
    return out


async def _load_comments(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    since: datetime,
) -> dict[tuple[uuid.UUID, date], list[str]]:
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    dish_id,
                    (created_at AT TIME ZONE 'Asia/Kolkata')::date AS day,
                    suggestion_text
                FROM ckac_ratings.dish_suggestions
                WHERE kitchen_id = :kid
                  AND created_at >= :since
                """
            ),
            {"kid": kitchen_id, "since": since},
        )
    ).mappings().all()
    out: dict[tuple[uuid.UUID, date], list[str]] = {}
    for r in rows:
        key = (r["dish_id"], r["day"])
        out.setdefault(key, []).append(str(r["suggestion_text"]))
    return out


async def load_recipe_snapshot(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
) -> dict:
    """Cross-schema read of current recipe — ownership via kitchen_id."""
    dish = (
        await session.execute(
            text(
                """
                SELECT id, name FROM ckac_catalog.dishes
                WHERE id = :did AND kitchen_id = :kid
                """
            ),
            {"did": dish_id, "kid": kitchen_id},
        )
    ).mappings().first()
    if not dish:
        return {"dish_id": str(dish_id), "lines": [], "prep_steps": []}

    lines = (
        await session.execute(
            text(
                """
                SELECT
                    di.ingredient_id,
                    i.name AS ingredient_name,
                    di.quantity,
                    di.unit,
                    di.photo_url,
                    di.sort_order
                FROM ckac_catalog.dish_ingredients di
                JOIN ckac_catalog.ingredients i ON i.id = di.ingredient_id
                WHERE di.dish_id = :did AND i.kitchen_id = :kid
                ORDER BY di.sort_order, i.name
                """
            ),
            {"did": dish_id, "kid": kitchen_id},
        )
    ).mappings().all()

    steps = (
        await session.execute(
            text(
                """
                SELECT id, step_order, title, body_html
                FROM ckac_catalog.dish_prep_steps
                WHERE dish_id = :did
                ORDER BY step_order
                """
            ),
            {"did": dish_id},
        )
    ).mappings().all()

    return {
        "dish_id": str(dish["id"]),
        "dish_name": dish["name"],
        "lines": [
            {
                "ingredient_id": str(r["ingredient_id"]),
                "ingredient_name": r["ingredient_name"],
                "quantity": float(r["quantity"]),
                "unit": r["unit"],
                "photo_url": r["photo_url"],
                "sort_order": int(r["sort_order"] or 0),
            }
            for r in lines
        ],
        "prep_steps": [
            {
                "id": str(r["id"]),
                "step_order": int(r["step_order"]),
                "title": r["title"],
                "body_html": r["body_html"],
            }
            for r in steps
        ],
    }


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _build_day_metrics(
    order_rows: list[dict],
    ratings: dict[tuple[uuid.UUID, date], tuple[float, int]],
    comments: dict[tuple[uuid.UUID, date], list[str]],
) -> list[DishDayMetrics]:
    model = get_sentiment_model()
    out: list[DishDayMetrics] = []
    for row in order_rows:
        dish_id = row["dish_id"]
        day = row["day"]
        key = (dish_id, day)
        avg_rating, rating_count = ratings.get(key, (None, 0))
        texts = comments.get(key, [])
        sentiment = model.score_comments(texts)
        # Soft signal when no free-text: map rating into [0,1]
        sentiment_score = sentiment.score
        if sentiment.comment_count == 0 and avg_rating is not None:
            sentiment_score = max(0.0, min(1.0, (float(avg_rating) - 3.0) / 2.0))
            label = "positive" if sentiment_score >= 0.62 else "neutral" if sentiment_score >= 0.38 else "negative"
        else:
            label = sentiment.label
        out.append(
            DishDayMetrics(
                dish_id=dish_id,
                dish_name=row["dish_name"],
                day=day,
                order_qty=int(row["order_qty"]),
                order_count=int(row["order_count"]),
                avg_rating=float(avg_rating) if avg_rating is not None else None,
                rating_count=int(rating_count),
                sentiment_score=round(float(sentiment_score), 4),
                sentiment_label=label,
                comment_count=sentiment.comment_count,
                sample_comments=texts[:3],
            )
        )
    return out


def select_golden_candidates(
    day_metrics: list[DishDayMetrics],
    *,
    window_days: int = GOLDEN_WINDOW_DAYS,
) -> list[tuple[DishDayMetrics, float]]:
    """Return (metrics, median_qty) for dishes that clear golden-day gates."""
    by_dish: dict[uuid.UUID, list[DishDayMetrics]] = {}
    for m in day_metrics:
        by_dish.setdefault(m.dish_id, []).append(m)

    winners: list[tuple[DishDayMetrics, float]] = []
    for _dish_id, days in by_dish.items():
        if len(days) < MIN_DAYS_WITH_ORDERS:
            continue
        qtys = [d.order_qty for d in days]
        median_qty = _median(qtys)
        best = max(days, key=lambda d: (d.order_qty, d.avg_rating or 0.0, d.sentiment_score))
        # Must be unique max (or tied only with inferior rating/sentiment — already sorted)
        max_qty = best.order_qty
        if sum(1 for d in days if d.order_qty == max_qty) > 1:
            # Prefer the day with best rating+sentiment among ties
            tied = [d for d in days if d.order_qty == max_qty]
            best = max(tied, key=lambda d: ((d.avg_rating or 0.0), d.sentiment_score))

        if best.order_qty < MIN_GOLDEN_QTY:
            continue
        if median_qty > 0 and best.order_qty < median_qty * QTY_VS_MEDIAN_MULT:
            continue
        if best.avg_rating is None or best.avg_rating < MIN_AVG_RATING:
            continue
        if best.rating_count < 1:
            continue
        if best.sentiment_score < MIN_SENTIMENT:
            continue
        winners.append((best, median_qty))
    return winners


async def existing_golden_keys(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
) -> set[tuple[uuid.UUID, str]]:
    rows = (
        await session.execute(
            select(Suggestion).where(
                Suggestion.kitchen_id == kitchen_id,
                Suggestion.suggestion_type == SUGGESTION_TYPE,
                Suggestion.dismissed.is_(False),
            )
        )
    ).scalars().all()
    keys: set[tuple[uuid.UUID, str]] = set()
    for row in rows:
        payload = row.action_payload or {}
        dish = payload.get("dish_id")
        day = payload.get("performance_date")
        if dish and day:
            keys.add((uuid.UUID(str(dish)), str(day)))
    return keys


async def detect_golden_days(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    *,
    window_days: int = GOLDEN_WINDOW_DAYS,
) -> list[GoldenDayCandidate]:
    since = datetime.now(UTC) - timedelta(days=window_days)
    order_rows = await _load_order_days(session, kitchen_id, since)
    if not order_rows:
        return []
    ratings = await _load_rating_days(session, kitchen_id, since)
    comments = await _load_comments(session, kitchen_id, since)
    metrics = _build_day_metrics(order_rows, ratings, comments)
    selected = select_golden_candidates(metrics, window_days=window_days)
    already = await existing_golden_keys(session, kitchen_id)

    candidates: list[GoldenDayCandidate] = []
    for m, median_qty in selected:
        day_key = m.day.isoformat()
        if (m.dish_id, day_key) in already:
            continue
        snapshot = await load_recipe_snapshot(session, kitchen_id, m.dish_id)
        candidates.append(
            GoldenDayCandidate(
                metrics=m,
                median_qty=median_qty,
                window_days=window_days,
                recipe_snapshot=snapshot,
            )
        )
    return candidates


def build_golden_suggestion(kitchen_id: uuid.UUID, candidate: GoldenDayCandidate) -> Suggestion:
    m = candidate.metrics
    day_label = m.day.strftime("%d %b %Y")
    rating_txt = f"{m.avg_rating:.1f}" if m.avg_rating is not None else "n/a"
    title = f"Golden day for {m.dish_name}"
    description = (
        f"{day_label} was a standout for {m.dish_name}: {m.order_qty} portions "
        f"({m.order_count} orders), avg rating {rating_txt}/5, "
        f"comment sentiment {m.sentiment_label} ({m.sentiment_score:.0%}). "
        f"That beat your ~{candidate.median_qty:.0f} median daily portions over "
        f"{candidate.window_days} days. Save today's recipe & ingredient mix as a "
        "golden baseline for future prep."
    )
    return Suggestion(
        kitchen_id=kitchen_id,
        suggestion_type=SUGGESTION_TYPE,
        title=title,
        description=description,
        action_payload={
            "dish_id": str(m.dish_id),
            "dish_name": m.dish_name,
            "performance_date": m.day.isoformat(),
            "order_qty": m.order_qty,
            "order_count": m.order_count,
            "avg_rating": m.avg_rating,
            "rating_count": m.rating_count,
            "sentiment_score": m.sentiment_score,
            "sentiment_label": m.sentiment_label,
            "comment_count": m.comment_count,
            "sample_comments": m.sample_comments,
            "median_qty": candidate.median_qty,
            "window_days": candidate.window_days,
            "recipe_snapshot": candidate.recipe_snapshot,
            "recipe_saved": False,
        },
        priority=95,
    )


async def pin_golden_recipe(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    suggestion_id: uuid.UUID,
) -> GoldenRecipePin:
    row = (
        await session.execute(
            select(Suggestion).where(
                Suggestion.id == suggestion_id,
                Suggestion.kitchen_id == kitchen_id,
                Suggestion.suggestion_type == SUGGESTION_TYPE,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise ValueError("Golden-day suggestion not found")

    payload = dict(row.action_payload or {})
    dish_id = uuid.UUID(str(payload["dish_id"]))
    performance_date = date.fromisoformat(str(payload["performance_date"]))
    snapshot = payload.get("recipe_snapshot") or await load_recipe_snapshot(
        session, kitchen_id, dish_id
    )

    existing = (
        await session.execute(
            select(GoldenRecipePin).where(
                GoldenRecipePin.kitchen_id == kitchen_id,
                GoldenRecipePin.dish_id == dish_id,
                GoldenRecipePin.performance_date == performance_date,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.recipe_snapshot = snapshot
        existing.metrics = {
            "order_qty": payload.get("order_qty"),
            "avg_rating": payload.get("avg_rating"),
            "sentiment_score": payload.get("sentiment_score"),
            "sentiment_label": payload.get("sentiment_label"),
        }
        existing.suggestion_id = suggestion_id
        pin = existing
    else:
        pin = GoldenRecipePin(
            kitchen_id=kitchen_id,
            dish_id=dish_id,
            suggestion_id=suggestion_id,
            performance_date=performance_date,
            dish_name=str(payload.get("dish_name") or snapshot.get("dish_name") or "Dish"),
            recipe_snapshot=snapshot,
            metrics={
                "order_qty": payload.get("order_qty"),
                "avg_rating": payload.get("avg_rating"),
                "sentiment_score": payload.get("sentiment_score"),
                "sentiment_label": payload.get("sentiment_label"),
            },
        )
        session.add(pin)

    payload["recipe_saved"] = True
    row.action_payload = payload
    await session.flush()
    return pin


async def list_golden_pins(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID | None = None,
) -> list[GoldenRecipePin]:
    q = select(GoldenRecipePin).where(GoldenRecipePin.kitchen_id == kitchen_id)
    if dish_id is not None:
        q = q.where(GoldenRecipePin.dish_id == dish_id)
    q = q.order_by(GoldenRecipePin.performance_date.desc(), GoldenRecipePin.created_at.desc())
    return list((await session.execute(q)).scalars().all())
