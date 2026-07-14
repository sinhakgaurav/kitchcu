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
from ckac_common.openapi import RESP_400, auth_errors

router = APIRouter()

TAG_COMBOS = "Combos"
TAG_PATTERNS = "Patterns"
TAG_SUGGESTIONS = "Suggestions"
TAG_DAILY_MENU = "Daily Menu"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get(
    "/kitchens/{kitchen_id}/growth/combos",
    response_model=DishCombosResponse,
    tags=[TAG_COMBOS],
    summary="List frequently-paired dishes (F09)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Query:** `days` (7-365, default 90) lookback window; `limit` (1-20, default 5) max "
        "pairs returned.\n\n"
        "**Behavior:** Mines delivered multi-item orders for dish pairs, ranked by co-occurrence "
        "count. `support_pct` = pair occurrences / total multi-item orders in the window — high "
        "support suggests a good combo/bundle candidate.\n\n"
        "**Response:** `DishCombosResponse`."
    ),
    responses=auth_errors(include_403=True),
)
async def growth_combos(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=90, ge=7, le=365, description="Lookback window in days (7-365)."),
    limit: int = Query(default=5, ge=1, le=20, description="Max combo pairs to return (1-20)."),
) -> DishCombosResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await dish_combinations(session, kitchen_id, days=days, limit=limit)


@router.get(
    "/kitchens/{kitchen_id}/growth/patterns",
    response_model=OrderPatternsResponse,
    tags=[TAG_PATTERNS],
    summary="Get day/hour order patterns + insight (F10)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Query:** `days` (7-365, default 90) lookback window.\n\n"
        "**Response:** `OrderPatternsResponse` — per-weekday orders/revenue, per-hour order "
        "counts (IST), and an auto-generated plain-language operational insight (e.g. busiest "
        "day + meal-time peak) to help with staffing/prep planning."
    ),
    responses=auth_errors(include_403=True),
)
async def growth_patterns(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(default=90, ge=7, le=365, description="Lookback window in days (7-365)."),
) -> OrderPatternsResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await order_patterns(session, kitchen_id, days=days)


@router.get(
    "/kitchens/{kitchen_id}/growth/suggestions",
    response_model=SuggestionListResponse,
    tags=[TAG_SUGGESTIONS],
    summary="List growth suggestions (F11)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Query:** `include_dismissed` (default `false`) — set true to also return previously "
        "dismissed suggestions.\n\n"
        "**Response:** `SuggestionListResponse` ordered by priority descending, then newest first."
    ),
    responses=auth_errors(include_403=True),
)
async def growth_suggestions_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    include_dismissed: bool = Query(default=False, description="Include previously dismissed suggestions."),
) -> SuggestionListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await list_suggestions(session, kitchen_id, include_dismissed=include_dismissed)


@router.post(
    "/kitchens/{kitchen_id}/growth/suggestions/generate",
    response_model=SuggestionListResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_SUGGESTIONS],
    summary="Generate fresh growth suggestions",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Query:** `days` (7-365, default 90) lookback window for the underlying analysis.\n\n"
        "**Behavior:** Runs the suggestion engine (churn win-back, combo bundling, peak-hour "
        "staffing, seasonal, under-performing dish promo) and persists any new suggestions found, "
        "publishing `suggestion.generated` per suggestion.\n\n"
        "**Response:** `SuggestionListResponse` — only the newly-created suggestions from this run."
    ),
    responses=auth_errors(include_403=True),
)
async def growth_suggestions_generate(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    days: int = Query(default=90, ge=7, le=365, description="Lookback window in days (7-365) for the analysis."),
) -> SuggestionListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    result = await generate_suggestions(session, kitchen_id, publisher, days=days)
    await session.commit()
    return result


@router.patch(
    "/kitchens/{kitchen_id}/growth/suggestions/{suggestion_id}",
    response_model=SuggestionResponse,
    tags=[TAG_SUGGESTIONS],
    summary="Dismiss or un-dismiss a suggestion",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `SuggestionUpdateRequest` — `dismissed` flag.\n\n"
        "**Response:** Updated `SuggestionResponse`. 404 if the suggestion does not exist for "
        "this kitchen."
    ),
    responses=auth_errors(include_403=True, include_404=True),
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


@router.get(
    "/growth/seasonal-patterns",
    response_model=SeasonalPatternListResponse,
    tags=[TAG_PATTERNS],
    summary="List seasonal demand reference patterns",
    description=(
        "**Auth:** Owner JWT — any owner (not kitchen-scoped; this is shared platform reference "
        "data, not per-kitchen data).\n\n"
        "**Query:** `region` (default `india`).\n\n"
        "**Response:** `SeasonalPatternListResponse` ranked by `demand_multiplier` descending — "
        "feeds the seasonal-opportunity suggestion type."
    ),
    responses=auth_errors(),
)
async def growth_seasonal_patterns(
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    region: str = Query(default="india", description="Region code to filter patterns by, e.g. 'india'."),
) -> SeasonalPatternListResponse:
    _ = owner_id
    return await list_seasonal_patterns(session, region=region)


@router.post(
    "/kitchens/{kitchen_id}/growth/daily-menu/push",
    response_model=DailyMenuPushResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=[TAG_DAILY_MENU],
    summary="Push today's menu via WhatsApp (F39)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `DailyMenuPushRequest` — 1-20 active dish IDs and an optional custom message. "
        "Rejects if any dish is missing/inactive/belongs to another kitchen (400).\n\n"
        "**Behavior:** Publishes `daily_menu.blast_requested` and asynchronously dispatches a "
        "WhatsApp blast via the notification service to every customer in the kitchen's CRM "
        "roster.\n\n"
        "**Response:** `202 Accepted` with `DailyMenuPushResponse` (`status='queued'`) — the "
        "blast itself is fire-and-forget."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
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
