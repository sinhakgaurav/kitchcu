import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_customer_id, get_current_owner_id, verify_kitchen_owner
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

router = APIRouter()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get("/community/recipes", response_model=SharedRecipeListResponse)
async def community_recipes_public(
    session: Annotated[AsyncSession, Depends(get_db)],
    kitchen_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> SharedRecipeListResponse:
    return await list_shared_recipes(session, kitchen_id=kitchen_id, limit=limit)


@router.post(
    "/kitchens/{kitchen_id}/community/recipes",
    response_model=SharedRecipeResponse,
    status_code=status.HTTP_201_CREATED,
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


@router.post("/community/recipes/{recipe_id}/appreciate", response_model=SharedRecipeResponse)
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


@router.get("/kitchens/{kitchen_id}/community/rewards", response_model=RewardBalanceResponse)
async def community_rewards_balance(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RewardBalanceResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await get_reward_balance(session, kitchen_id)


@router.post("/kitchens/{kitchen_id}/community/rewards/redeem", response_model=RedeemRewardsResponse)
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


@router.get("/community/rankings", response_model=ChefRankingListResponse)
async def community_rankings_list(
    session: Annotated[AsyncSession, Depends(get_db)],
    scope: str = Query(default="city"),
    region_key: str | None = Query(default=None),
    period: str | None = Query(default=None),
) -> ChefRankingListResponse:
    return await list_rankings(session, scope=scope, region_key=region_key, period=period)


@router.post("/kitchens/{kitchen_id}/community/rankings/compute", response_model=ChefRankingListResponse)
async def community_rankings_compute(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    scope: Literal["city", "state", "national"] = Query(default="city"),
    region_key: str | None = Query(default=None),
) -> ChefRankingListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    result = await compute_rankings(session, scope=scope, region_key=region_key, publisher=publisher)
    await session.commit()
    return result
