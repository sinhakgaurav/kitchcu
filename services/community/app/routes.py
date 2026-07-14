import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_customer_id, get_current_owner_id, verify_kitchen_owner
from app.models import FEATURED_LISTING_COST, POINTS_PER_APPRECIATION, SUBSCRIPTION_DISCOUNT_COST
from app.schemas import (
    ChefRankingListResponse,
    RedeemRewardsRequest,
    RedeemRewardsResponse,
    RewardBalanceResponse,
    ShareRecipeRequest,
    SharedRecipeListResponse,
    SharedRecipeResponse,
    appreciate_recipe,
    compute_rankings,
    get_reward_balance,
    list_rankings,
    list_shared_recipes,
    redeem_rewards,
    share_recipe,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, auth_errors

router = APIRouter()

TAG_RECIPES = "Community Recipes"
TAG_REWARDS = "Rewards"
TAG_RANKINGS = "Chef Rankings"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get(
    "/community/recipes",
    response_model=SharedRecipeListResponse,
    tags=[TAG_RECIPES],
    summary="Browse published community recipes (F23)",
    description=(
        "**Auth:** None — public feed.\n\n"
        "**Query:** `kitchen_id` optional filter; `limit` (1-100, default 50).\n\n"
        "**Response:** `SharedRecipeListResponse` ordered newest first."
    ),
)
async def community_recipes_public(
    session: Annotated[AsyncSession, Depends(get_db)],
    kitchen_id: uuid.UUID | None = Query(default=None, description="Filter to a single kitchen's shared recipes."),
    limit: int = Query(default=50, ge=1, le=100, description="Max recipes to return (1-100)."),
) -> SharedRecipeListResponse:
    return await list_shared_recipes(session, kitchen_id=kitchen_id, limit=limit)


@router.post(
    "/kitchens/{kitchen_id}/community/recipes",
    response_model=SharedRecipeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_RECIPES],
    summary="Publish a recipe to the community feed",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `ShareRecipeRequest` — title, optional summary, sanitized recipe HTML, "
        "optional linked dish.\n\n"
        "**Behavior:** Publishes immediately (`status='published'`) and emits `recipe.shared`. "
        "Earns points only later, per customer appreciation (see the appreciate endpoint).\n\n"
        "**Response:** Created `SharedRecipeResponse`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def community_share_recipe(
    kitchen_id: uuid.UUID,
    body: ShareRecipeRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> SharedRecipeResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await share_recipe(session, kitchen_id, owner_id, body, publisher)
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/community/recipes/{recipe_id}/appreciate",
    response_model=SharedRecipeResponse,
    tags=[TAG_RECIPES],
    summary="Appreciate a shared recipe",
    description=(
        "**Auth:** Customer JWT.\n\n"
        f"**Behavior:** Each customer may appreciate a given recipe once. Credits "
        f"{POINTS_PER_APPRECIATION} reward points to the publishing kitchen and publishes "
        "`recipe.appreciated`. 404 if the recipe doesn't exist/isn't published; 400 on a "
        "duplicate appreciation.\n\n"
        "**Response:** Updated `SharedRecipeResponse` with the incremented `appreciation_count`."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400},
)
async def community_appreciate_recipe(
    recipe_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> SharedRecipeResponse:
    try:
        result = await appreciate_recipe(session, recipe_id, customer_id, publisher)
        await session.commit()
        return result
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get(
    "/kitchens/{kitchen_id}/community/rewards",
    response_model=RewardBalanceResponse,
    tags=[TAG_REWARDS],
    summary="Get a kitchen's reward point balance + ledger",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Response:** `RewardBalanceResponse` — current balance plus the most recent 20 ledger "
        "entries (earns and redemptions)."
    ),
    responses=auth_errors(include_403=True),
)
async def community_rewards_balance(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RewardBalanceResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await get_reward_balance(session, kitchen_id)


@router.post(
    "/kitchens/{kitchen_id}/community/rewards/redeem",
    response_model=RedeemRewardsResponse,
    tags=[TAG_REWARDS],
    summary="Redeem reward points for a growth perk",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `RedeemRewardsRequest` — `redemption_type`: "
        f"`subscription_discount` ({SUBSCRIPTION_DISCOUNT_COST} pts) or "
        f"`featured_listing` ({FEATURED_LISTING_COST} pts). Rejects if the balance is "
        "insufficient (400).\n\n"
        "**Behavior:** Deducts points, records the redemption `status='approved'`, and "
        "publishes `reward.redeemed`.\n\n"
        "**Response:** `RedeemRewardsResponse` with the new balance."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def community_rewards_redeem(
    kitchen_id: uuid.UUID,
    body: RedeemRewardsRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> RedeemRewardsResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await redeem_rewards(session, kitchen_id, body, publisher)
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/community/rankings",
    response_model=ChefRankingListResponse,
    tags=[TAG_RANKINGS],
    summary="Get the chef leaderboard for a period/scope/region",
    description=(
        "**Auth:** None — public leaderboard.\n\n"
        "**Query:** `scope` ('city'/'state'/'national', default 'city'), `region_key` "
        "(city/state name; ignored for national), `period` ('YYYY-MM', defaults to current month).\n\n"
        "**Response:** `ChefRankingListResponse` — reads the last computed snapshot for this "
        "period/scope/region; returns empty if it has not been computed yet (see the compute "
        "endpoint)."
    ),
)
async def community_rankings_list(
    session: Annotated[AsyncSession, Depends(get_db)],
    scope: str = Query(default="city", description="'city', 'state', or 'national'."),
    region_key: str | None = Query(default=None, description="City/state name to scope by; ignored for 'national'."),
    period: str | None = Query(default=None, description="Period 'YYYY-MM'; defaults to the current month."),
) -> ChefRankingListResponse:
    return await list_rankings(session, scope=scope, region_key=region_key, period=period)


@router.post(
    "/kitchens/{kitchen_id}/community/rankings/compute",
    response_model=ChefRankingListResponse,
    tags=[TAG_RANKINGS],
    summary="Recompute the chef leaderboard for a scope/region",
    description=(
        "**Auth:** Owner JWT — any owner (this recomputes a shared, platform-wide leaderboard "
        "snapshot, not kitchen-private data; `kitchen_id` in the path is only used to identify "
        "the calling owner, not to scope the computation).\n\n"
        "**Query:** `scope` ('city'/'state'/'national', default 'city'), `region_key`.\n\n"
        "**Behavior:** Scores every active kitchen with at least 3 delivered orders this month "
        "(0-100 composite of avg dish rating, review volume, order volume, repeat rate, and "
        "recipe-appreciation/community votes), replaces the prior snapshot for this period/"
        "scope/region with the top 50, and publishes `ranking.published`.\n\n"
        "**Response:** `ChefRankingListResponse` — the freshly computed leaderboard."
    ),
    responses=auth_errors(include_403=True),
)
async def community_rankings_compute(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    scope: Literal["city", "state", "national"] = Query(default="city", description="'city', 'state', or 'national'."),
    region_key: str | None = Query(default=None, description="City/state name to scope by; ignored for 'national'."),
) -> ChefRankingListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    result = await compute_rankings(session, scope=scope, region_key=region_key, publisher=publisher)
    await session.commit()
    return result
