"""Community domain — recipe sharing rewards (F23) and chef rankings (F24)."""

from __future__ import annotations

import os
import re
import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    FEATURED_LISTING_COST,
    POINTS_PER_APPRECIATION,
    SUBSCRIPTION_DISCOUNT_COST,
    ChefRanking,
    KitchenRewardBalance,
    RecipeAppreciation,
    RewardPointLedger,
    RewardRedemption,
    SharedRecipe,
)
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

ALLOWED_TAGS = {"p", "br", "strong", "em", "ul", "ol", "li", "h3"}
MIN_ORDERS_FOR_RANKING = int(os.environ.get("COMMUNITY_MIN_ORDERS_RANKING", "3"))


class ShareRecipeRequest(BaseModel):
    """Owner request to publish a recipe to the public community feed (F23)."""

    title: str = Field(min_length=3, max_length=255, description="Recipe title.", examples=["My Grandmother's Dal Makhani"])
    summary: str | None = Field(default=None, max_length=500, description="Short teaser shown in recipe lists.")
    recipe_html: str = Field(min_length=10, max_length=20000, description="Full recipe body HTML (script tags and inline event handlers are stripped server-side).")
    cover_url: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional cover photo URL from kitchen media upload (live-capture preferred).",
    )
    dish_id: uuid.UUID | None = Field(default=None, description="Optional linked catalog dish this recipe is based on.")

    @field_validator("recipe_html")
    @classmethod
    def strip_unsafe_html(cls, value: str) -> str:
        cleaned = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.I | re.S)
        cleaned = re.sub(r"on\w+\s*=\s*\"[^\"]*\"", "", cleaned, flags=re.I)
        cleaned = re.sub(r"on\w+\s*=\s*'[^']*'", "", cleaned, flags=re.I)
        return cleaned.strip()


class SharedRecipeResponse(BaseModel):
    """A published community recipe."""

    id: uuid.UUID = Field(..., description="Recipe UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Publishing kitchen UUID.")
    title: str = Field(..., description="Recipe title.")
    summary: str | None = Field(default=None, description="Short teaser text.")
    recipe_html: str = Field(..., description="Sanitized recipe body HTML.")
    cover_url: str | None = Field(default=None, description="Cover photo URL, if uploaded.")
    dish_id: uuid.UUID | None = Field(default=None, description="Linked catalog dish, if any.")
    appreciation_count: int = Field(..., description="Number of unique customers who appreciated this recipe.")
    points_earned: int = Field(..., description=f"Total reward points this recipe has earned its kitchen ({POINTS_PER_APPRECIATION} per appreciation).")
    kitchen_name: str | None = Field(default=None, description="Publishing kitchen's display name.")
    kitchen_code: str | None = Field(default=None, description="Publishing kitchen's code.", examples=["CKPNQ001"])
    created_at: datetime = Field(..., description="Publish timestamp, UTC.")

    model_config = {"from_attributes": True}


class SharedRecipeListResponse(BaseModel):
    """Public feed of shared recipes."""

    recipes: list[SharedRecipeResponse] = Field(..., description="Published recipes, newest first.")
    total: int = Field(..., description="Number of recipes returned.")


class RewardLedgerEntry(BaseModel):
    """One entry in a kitchen's reward point ledger (audit trail of every earn/spend)."""

    id: uuid.UUID = Field(..., description="Ledger entry UUID.")
    delta: int = Field(..., description="Points change — positive for earns, negative for redemptions.", examples=[10, -100])
    reason: str = Field(..., description="Reason code, e.g. 'recipe_appreciation', 'redeem_subscription_discount'.")
    balance_after: int = Field(..., description="Running point balance immediately after this entry.")
    created_at: datetime = Field(..., description="Timestamp, UTC.")

    model_config = {"from_attributes": True}


class RewardBalanceResponse(BaseModel):
    """A kitchen's current reward point balance + recent ledger history."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen UUID.")
    points_balance: int = Field(..., description="Current spendable point balance.")
    ledger: list[RewardLedgerEntry] = Field(..., description="Most recent 20 ledger entries, newest first.")


class RedeemRewardsRequest(BaseModel):
    """Owner request to redeem reward points for a growth perk."""

    redemption_type: Literal["subscription_discount", "featured_listing"] = Field(
        ..., description=f"'subscription_discount' costs {SUBSCRIPTION_DISCOUNT_COST} points; 'featured_listing' costs {FEATURED_LISTING_COST} points."
    )


class RedeemRewardsResponse(BaseModel):
    """Result of a reward redemption."""

    redemption_id: uuid.UUID = Field(..., description="Redemption UUID.")
    redemption_type: str = Field(..., description="Type redeemed.")
    points_spent: int = Field(..., description="Points deducted for this redemption.")
    points_balance: int = Field(..., description="Remaining point balance after redemption.")
    status: str = Field(..., description="Redemption status, e.g. 'approved'.")


class ChefRankingEntry(BaseModel):
    """One kitchen's position on the chef leaderboard for a given period/scope/region."""

    rank: int = Field(..., description="1-based rank within the scope/region for this period.")
    kitchen_id: uuid.UUID = Field(..., description="Kitchen UUID.")
    kitchen_code: str = Field(..., description="Kitchen code.")
    kitchen_name: str = Field(..., description="Kitchen display name.")
    score: float = Field(..., description="Composite score (0-100), weighted from ratings, review volume, order volume, repeat rate, and community engagement.")
    metrics: dict = Field(..., description="Raw underlying metrics used to compute the score (avg_dish_rating, review_volume, monthly_orders, repeat_order_rate, recipe_appreciations, community_votes).")

    model_config = {"from_attributes": True}


class ChefRankingListResponse(BaseModel):
    """Leaderboard for a period/scope/region."""

    period: str = Field(..., description="Ranking period, 'YYYY-MM'.", examples=["2026-07"])
    scope: str = Field(..., description="'city', 'state', or 'national'.")
    region_key: str = Field(..., description="Region value for the scope (city/state name, 'india' for national, or 'all').")
    rankings: list[ChefRankingEntry] = Field(..., description="Top kitchens by score, up to 50, ordered by rank.")
    total: int = Field(..., description="Number of ranking entries returned.")


async def _kitchen_meta(session: AsyncSession, kitchen_id: uuid.UUID) -> tuple[str, str, str | None, str | None]:
    row = (
        await session.execute(
            text(
                "SELECT code, name, city, state FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"
            ),
            {"kid": kitchen_id},
        )
    ).one_or_none()
    if not row:
        raise ValueError("Kitchen not found")
    return row[0], row[1], row[2], row[3]


async def _credit_points(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    delta: int,
    reason: str,
    reference_id: uuid.UUID | None,
) -> int:
    bal = (
        await session.execute(
            select(KitchenRewardBalance).where(KitchenRewardBalance.kitchen_id == kitchen_id)
        )
    ).scalar_one_or_none()
    if not bal:
        bal = KitchenRewardBalance(kitchen_id=kitchen_id, points_balance=0)
        session.add(bal)
        await session.flush()
    bal.points_balance += delta
    entry = RewardPointLedger(
        kitchen_id=kitchen_id,
        delta=delta,
        reason=reason,
        reference_id=reference_id,
        balance_after=bal.points_balance,
    )
    session.add(entry)
    await session.flush()
    return bal.points_balance


async def share_recipe(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: ShareRecipeRequest,
    publisher: EventPublisher,
) -> SharedRecipeResponse:
    row = SharedRecipe(
        kitchen_id=kitchen_id,
        owner_id=owner_id,
        title=data.title.strip(),
        summary=data.summary,
        recipe_html=data.recipe_html,
        cover_url=data.cover_url,
        dish_id=data.dish_id,
        status="published",
    )
    session.add(row)
    await session.flush()

    event = EventPublisher.build(
        event_type="recipe.shared",
        aggregate_type="shared_recipe",
        aggregate_id=str(row.id),
        producer="community-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "recipe_id": str(row.id),
            "title": row.title,
            "cover_url": row.cover_url,
        },
    )
    await publisher.publish(stream_key("community", "recipe"), event, session=session)
    code, name, _, _ = await _kitchen_meta(session, kitchen_id)
    return SharedRecipeResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        title=row.title,
        summary=row.summary,
        recipe_html=row.recipe_html,
        cover_url=row.cover_url,
        dish_id=row.dish_id,
        appreciation_count=row.appreciation_count,
        points_earned=row.points_earned,
        kitchen_name=name,
        kitchen_code=code,
        created_at=row.created_at,
    )


async def list_shared_recipes(
    session: AsyncSession,
    *,
    kitchen_id: uuid.UUID | None = None,
    limit: int = 50,
) -> SharedRecipeListResponse:
    q = select(SharedRecipe).where(SharedRecipe.status == "published")
    if kitchen_id:
        q = q.where(SharedRecipe.kitchen_id == kitchen_id)
    q = q.order_by(SharedRecipe.created_at.desc()).limit(limit)
    rows = list((await session.execute(q)).scalars().all())
    recipes: list[SharedRecipeResponse] = []
    for row in rows:
        code, name, _, _ = await _kitchen_meta(session, row.kitchen_id)
        recipes.append(
            SharedRecipeResponse(
                id=row.id,
                kitchen_id=row.kitchen_id,
                title=row.title,
                summary=row.summary,
                recipe_html=row.recipe_html,
                cover_url=getattr(row, "cover_url", None),
                dish_id=row.dish_id,
                appreciation_count=row.appreciation_count,
                points_earned=row.points_earned,
                kitchen_name=name,
                kitchen_code=code,
                created_at=row.created_at,
            )
        )
    return SharedRecipeListResponse(recipes=recipes, total=len(recipes))


async def appreciate_recipe(
    session: AsyncSession,
    recipe_id: uuid.UUID,
    customer_id: uuid.UUID,
    publisher: EventPublisher,
) -> SharedRecipeResponse:
    recipe = (
        await session.execute(
            select(SharedRecipe).where(SharedRecipe.id == recipe_id, SharedRecipe.status == "published")
        )
    ).scalar_one_or_none()
    if not recipe:
        raise ValueError("Recipe not found")

    existing = (
        await session.execute(
            select(RecipeAppreciation).where(
                RecipeAppreciation.recipe_id == recipe_id,
                RecipeAppreciation.customer_id == customer_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("You already appreciated this recipe")

    session.add(RecipeAppreciation(recipe_id=recipe_id, customer_id=customer_id))
    recipe.appreciation_count += 1
    recipe.points_earned += POINTS_PER_APPRECIATION
    await _credit_points(
        session,
        recipe.kitchen_id,
        POINTS_PER_APPRECIATION,
        "recipe_appreciation",
        recipe_id,
    )
    await session.flush()

    event = EventPublisher.build(
        event_type="recipe.appreciated",
        aggregate_type="shared_recipe",
        aggregate_id=str(recipe.id),
        producer="community-service",
        payload={
            "kitchen_id": str(recipe.kitchen_id),
            "recipe_id": str(recipe.id),
            "customer_id": str(customer_id),
            "points": POINTS_PER_APPRECIATION,
        },
    )
    await publisher.publish(stream_key("community", "recipe"), event, session=session)

    code, name, _, _ = await _kitchen_meta(session, recipe.kitchen_id)
    return SharedRecipeResponse(
        id=recipe.id,
        kitchen_id=recipe.kitchen_id,
        title=recipe.title,
        summary=recipe.summary,
        recipe_html=recipe.recipe_html,
        cover_url=getattr(recipe, "cover_url", None),
        dish_id=recipe.dish_id,
        appreciation_count=recipe.appreciation_count,
        points_earned=recipe.points_earned,
        kitchen_name=name,
        kitchen_code=code,
        created_at=recipe.created_at,
    )


async def get_reward_balance(session: AsyncSession, kitchen_id: uuid.UUID) -> RewardBalanceResponse:
    bal = (
        await session.execute(
            select(KitchenRewardBalance).where(KitchenRewardBalance.kitchen_id == kitchen_id)
        )
    ).scalar_one_or_none()
    ledger_rows = list(
        (
            await session.execute(
                select(RewardPointLedger)
                .where(RewardPointLedger.kitchen_id == kitchen_id)
                .order_by(RewardPointLedger.created_at.desc())
                .limit(20)
            )
        ).scalars().all()
    )
    return RewardBalanceResponse(
        kitchen_id=kitchen_id,
        points_balance=bal.points_balance if bal else 0,
        ledger=[RewardLedgerEntry.model_validate(e) for e in ledger_rows],
    )


async def redeem_rewards(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: RedeemRewardsRequest,
    publisher: EventPublisher,
) -> RedeemRewardsResponse:
    cost = (
        SUBSCRIPTION_DISCOUNT_COST
        if data.redemption_type == "subscription_discount"
        else FEATURED_LISTING_COST
    )
    bal = (
        await session.execute(
            select(KitchenRewardBalance).where(KitchenRewardBalance.kitchen_id == kitchen_id)
        )
    ).scalar_one_or_none()
    balance = bal.points_balance if bal else 0
    if balance < cost:
        raise ValueError(f"Need {cost} points, have {balance}")

    redemption = RewardRedemption(
        kitchen_id=kitchen_id,
        redemption_type=data.redemption_type,
        points_spent=cost,
        status="approved",
    )
    session.add(redemption)
    await session.flush()

    new_balance = await _credit_points(
        session, kitchen_id, -cost, f"redeem_{data.redemption_type}", redemption.id
    )

    event = EventPublisher.build(
        event_type="reward.redeemed",
        aggregate_type="reward",
        aggregate_id=str(redemption.id),
        producer="community-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "redemption_type": data.redemption_type,
            "points_spent": cost,
        },
    )
    await publisher.publish(stream_key("community", "reward"), event, session=session)

    return RedeemRewardsResponse(
        redemption_id=redemption.id,
        redemption_type=data.redemption_type,
        points_spent=cost,
        points_balance=new_balance,
        status=redemption.status,
    )


def _norm(value: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    return min(1.0, value / cap)


async def _kitchen_metrics(session: AsyncSession, kitchen_id: uuid.UUID) -> dict:
    rating_row = (
        await session.execute(
            text(
                """
                SELECT COALESCE(AVG(overall_rating), 0), COALESCE(SUM(rating_count), 0)
                FROM ckac_ratings.dish_rating_aggregates
                WHERE kitchen_id = :kid
                """
            ),
            {"kid": kitchen_id},
        )
    ).one()
    avg_rating = float(rating_row[0] or 0)
    review_volume = int(rating_row[1] or 0)

    order_row = (
        await session.execute(
            text(
                """
                SELECT COUNT(*)::int,
                       COUNT(DISTINCT customer_phone) FILTER (WHERE customer_phone IS NOT NULL)::int
                FROM ckac_orders.orders
                WHERE kitchen_id = :kid AND status = 'delivered'
                  AND created_at >= date_trunc('month', now())
                """
            ),
            {"kid": kitchen_id},
        )
    ).one()
    monthly_orders = int(order_row[0] or 0)
    unique_customers = int(order_row[1] or 0)
    repeat_rate = 0.0
    if unique_customers > 0 and monthly_orders > unique_customers:
        repeat_rate = min(1.0, (monthly_orders - unique_customers) / monthly_orders)

    shares_row = (
        await session.execute(
            text(
                "SELECT COALESCE(SUM(appreciation_count), 0)::int "
                "FROM ckac_community.shared_recipes WHERE kitchen_id = :kid"
            ),
            {"kid": kitchen_id},
        )
    ).scalar_one()
    recipe_shares = int(shares_row or 0)

    return {
        "avg_dish_rating": avg_rating,
        "review_volume": review_volume,
        "monthly_orders": monthly_orders,
        "repeat_order_rate": repeat_rate,
        "recipe_appreciations": recipe_shares,
        "community_votes": recipe_shares,
    }


def _compute_score(metrics: dict) -> float:
    return round(
        0.30 * _norm(metrics["avg_dish_rating"], 5.0)
        + 0.20 * _norm(metrics["recipe_appreciations"], 50.0)
        + 0.25 * _norm(metrics["review_volume"] * (metrics["avg_dish_rating"] / 5.0), 100.0)
        + 0.15 * metrics["repeat_order_rate"]
        + 0.10 * _norm(metrics["community_votes"], 30.0),
        3,
    ) * 100


async def compute_rankings(
    session: AsyncSession,
    *,
    scope: Literal["city", "state", "national"],
    region_key: str | None,
    publisher: EventPublisher,
) -> ChefRankingListResponse:
    period = datetime.now(UTC).strftime("%Y-%m")
    kitchens = (
        await session.execute(
            text(
                """
                SELECT id, code, name, city, state
                FROM ckac_identity.kitchens
                WHERE status = 'active'
                """
            )
        )
    ).fetchall()

    candidates: list[tuple[uuid.UUID, str, str, str, dict, float]] = []
    for kid, code, name, city, state in kitchens:
        metrics = await _kitchen_metrics(session, uuid.UUID(str(kid)))
        if metrics["monthly_orders"] < MIN_ORDERS_FOR_RANKING:
            continue
        if scope == "city" and region_key and (city or "").lower() != region_key.lower():
            continue
        if scope == "state" and region_key and (state or "").lower() != region_key.lower():
            continue
        score = _compute_score(metrics)
        candidates.append((uuid.UUID(str(kid)), code, name, city or "unknown", metrics, score))

    candidates.sort(key=lambda x: x[5], reverse=True)
    resolved_region = region_key or ("india" if scope == "national" else "all")

    await session.execute(
        delete(ChefRanking).where(
            ChefRanking.period == period,
            ChefRanking.scope == scope,
            ChefRanking.region_key == resolved_region,
        )
    )

    entries: list[ChefRankingEntry] = []
    for idx, (kid, code, name, _, metrics, score) in enumerate(candidates[:50], start=1):
        row = ChefRanking(
            period=period,
            scope=scope,
            region_key=resolved_region,
            kitchen_id=kid,
            kitchen_code=code,
            kitchen_name=name,
            score=score,
            rank=idx,
            metrics=metrics,
        )
        session.add(row)
        entries.append(
            ChefRankingEntry(
                rank=idx,
                kitchen_id=kid,
                kitchen_code=code,
                kitchen_name=name,
                score=score,
                metrics=metrics,
            )
        )
    await session.flush()

    if entries:
        event = EventPublisher.build(
            event_type="ranking.published",
            aggregate_type="ranking",
            aggregate_id=f"{period}:{scope}:{resolved_region}",
            producer="community-service",
            payload={
                "period": period,
                "scope": scope,
                "region_key": resolved_region,
                "count": len(entries),
            },
        )
        await publisher.publish(stream_key("community", "ranking"), event, session=session)

    return ChefRankingListResponse(
        period=period,
        scope=scope,
        region_key=resolved_region,
        rankings=entries,
        total=len(entries),
    )


async def list_rankings(
    session: AsyncSession,
    *,
    scope: str,
    region_key: str | None,
    period: str | None,
) -> ChefRankingListResponse:
    resolved_period = period or datetime.now(UTC).strftime("%Y-%m")
    resolved_region = region_key or ("india" if scope == "national" else "all")
    rows = list(
        (
            await session.execute(
                select(ChefRanking)
                .where(
                    ChefRanking.period == resolved_period,
                    ChefRanking.scope == scope,
                    ChefRanking.region_key == resolved_region,
                )
                .order_by(ChefRanking.rank)
            )
        ).scalars().all()
    )
    return ChefRankingListResponse(
        period=resolved_period,
        scope=scope,
        region_key=resolved_region,
        rankings=[
            ChefRankingEntry(
                rank=r.rank,
                kitchen_id=r.kitchen_id,
                kitchen_code=r.kitchen_code,
                kitchen_name=r.kitchen_name,
                score=float(r.score),
                metrics=r.metrics or {},
            )
            for r in rows
        ],
        total=len(rows),
    )
