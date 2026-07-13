import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_owner_id, verify_kitchen_owner
from app.notify_client import notify_daily_menu_blast
from app.schemas import (
    DailyMenuPushRequest,
    DailyMenuPushResponse,
    DishCombosResponse,
    OrderPatternsResponse,
    SeasonalPatternListResponse,
    SuggestionListResponse,
    SuggestionResponse,
    SuggestionUpdateRequest,
    dish_combinations,
    generate_suggestions,
    list_seasonal_patterns,
    list_suggestions,
    order_patterns,
    push_daily_menu,
    update_suggestion,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher

router = APIRouter()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get(
    "/kitchens/{kitchen_id}/growth/combos",
    response_model=DishCombosResponse,
)
async def growth_combos(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=90, ge=7, le=365),
    limit: int = Query(default=5, ge=1, le=20),
) -> DishCombosResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await dish_combinations(session, kitchen_id, days=days, limit=limit)


@router.get(
    "/kitchens/{kitchen_id}/growth/patterns",
    response_model=OrderPatternsResponse,
)
async def growth_patterns(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=90, ge=7, le=365),
) -> OrderPatternsResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await order_patterns(session, kitchen_id, days=days)


@router.get(
    "/kitchens/{kitchen_id}/growth/suggestions",
    response_model=SuggestionListResponse,
)
async def growth_suggestions_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    include_dismissed: bool = Query(default=False),
) -> SuggestionListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await list_suggestions(session, kitchen_id, include_dismissed=include_dismissed)


@router.post(
    "/kitchens/{kitchen_id}/growth/suggestions/generate",
    response_model=SuggestionListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def growth_suggestions_generate(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    days: int = Query(default=90, ge=7, le=365),
) -> SuggestionListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    result = await generate_suggestions(session, kitchen_id, publisher, days=days)
    await session.commit()
    return result


@router.patch(
    "/kitchens/{kitchen_id}/growth/suggestions/{suggestion_id}",
    response_model=SuggestionResponse,
)
async def growth_suggestion_update(
    kitchen_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    body: SuggestionUpdateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SuggestionResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        row = await update_suggestion(session, kitchen_id, suggestion_id, body.dismissed)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return row


@router.get("/growth/seasonal-patterns", response_model=SeasonalPatternListResponse)
async def growth_seasonal_patterns(
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    region: str = Query(default="india"),
) -> SeasonalPatternListResponse:
    _ = owner_id
    return await list_seasonal_patterns(session, region=region)


@router.post(
    "/kitchens/{kitchen_id}/growth/daily-menu/push",
    response_model=DailyMenuPushResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def growth_daily_menu_push(
    kitchen_id: uuid.UUID,
    body: DailyMenuPushRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> DailyMenuPushResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await push_daily_menu(session, kitchen_id, body, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    await notify_daily_menu_blast(
        kitchen_id=kitchen_id,
        message=result.message,
        recipient_count=result.recipient_count,
    )
    return result
