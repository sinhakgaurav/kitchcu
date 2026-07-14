import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import (
    get_current_customer_id,
    get_current_owner_id,
    load_customer_phone,
    verify_kitchen_owner,
)
from app.schemas import (
    AnonymousReviewsListResponse,
    DishRatingSummaryResponse,
    DishSuggestionCreateRequest,
    DishSuggestionListResponse,
    DishSuggestionResponse,
    DishSuggestionUpdateRequest,
    KitchenRatingSummariesResponse,
    OrderRatingsCreateRequest,
    OrderRatingsCreateResponse,
    create_suggestion,
    get_dish_summary,
    list_anonymous_reviews,
    list_kitchen_summaries,
    list_suggestions,
    submit_order_ratings,
    update_suggestion,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, auth_errors

router = APIRouter()

TAG_RATINGS = "Ratings"
TAG_SUGGESTIONS = "Suggestions"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.post(
    "/customers/me/orders/{order_id}/ratings",
    response_model=OrderRatingsCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_RATINGS],
    summary="Rate dishes from a delivered order (F16)",
    description=(
        "**Auth:** Customer JWT — the order must belong to the caller's phone.\n\n"
        "**Body:** `OrderRatingsCreateRequest` — 1-20 `RatingItemInput` entries, each with a "
        "home-taste score, quality score, and optional anonymous A/V review.\n\n"
        "**Integrity checks (400 on failure):** order exists and belongs to the caller; order "
        "`status == 'delivered'` (only verified, completed purchases can rate — no drive-by "
        "reviews); each `dish_id` was actually in the order; no duplicate rating for the same "
        "dish/order/customer.\n\n"
        "**Behavior:** Updates the dish's live rating aggregate and publishes `rating.created` + "
        "`rating.aggregate.updated` per dish.\n\n"
        "**Response:** `OrderRatingsCreateResponse` with the created rating rows."
    ),
    responses={**auth_errors(), 400: RESP_400},
)
async def create_order_ratings(
    order_id: uuid.UUID,
    body: OrderRatingsCreateRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> OrderRatingsCreateResponse:
    phone = await load_customer_phone(customer_id, session)
    try:
        result = await submit_order_ratings(
            session, order_id, customer_id, phone, body, publisher
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return result


@router.get(
    "/kitchens/{kitchen_id}/ratings/summaries",
    response_model=KitchenRatingSummariesResponse,
    tags=[TAG_RATINGS],
    summary="List rating summaries for every rated dish in a kitchen",
    description=(
        "**Auth:** None — public, used on kitchen/menu pages to show star ratings.\n\n"
        "**Response:** `KitchenRatingSummariesResponse` — one live-aggregated summary per dish "
        "that has at least one verified rating."
    ),
)
async def kitchen_rating_summaries(
    kitchen_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KitchenRatingSummariesResponse:
    return await list_kitchen_summaries(session, kitchen_id)


@router.get(
    "/kitchens/{kitchen_id}/dishes/{dish_id}/ratings/summary",
    response_model=DishRatingSummaryResponse,
    tags=[TAG_RATINGS],
    summary="Get a single dish's rating summary",
    description=(
        "**Auth:** None — public.\n\n"
        "**Response:** `DishRatingSummaryResponse` with `rating_count=0` and zeroed averages if "
        "the dish has no ratings yet."
    ),
)
async def dish_rating_summary(
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DishRatingSummaryResponse:
    return await get_dish_summary(session, kitchen_id, dish_id)


@router.get(
    "/kitchens/{kitchen_id}/dishes/{dish_id}/ratings/reviews",
    response_model=AnonymousReviewsListResponse,
    tags=[TAG_RATINGS],
    summary="List approved A/V reviews for a dish",
    description=(
        "**Auth:** None — public.\n\n"
        "**Query:** `limit` (1-50, default 20).\n\n"
        "**Response:** `AnonymousReviewsListResponse` — approved reviews (moderated), most "
        "recent first. Never exposes the reviewing customer's identity."
    ),
)
async def dish_anonymous_reviews(
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=50, description="Max reviews to return (1-50)."),
) -> AnonymousReviewsListResponse:
    return await list_anonymous_reviews(session, kitchen_id, dish_id, limit=limit)


@router.post(
    "/kitchens/{kitchen_id}/dishes/{dish_id}/suggestions",
    response_model=DishSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_SUGGESTIONS],
    summary="Submit a dish suggestion",
    description=(
        "**Auth:** Customer JWT.\n\n"
        "**Body:** `DishSuggestionCreateRequest` — freeform text, optionally tied to an order. "
        "Unlike ratings, this is not restricted to delivered orders.\n\n"
        "**Response:** Created `DishSuggestionResponse` with `status='pending'`, awaiting owner review."
    ),
    responses={**auth_errors(), 400: RESP_400},
)
async def dish_suggestion_create(
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    body: DishSuggestionCreateRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DishSuggestionResponse:
    try:
        row = await create_suggestion(session, kitchen_id, dish_id, customer_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return DishSuggestionResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        dish_id=row.dish_id,
        customer_id=row.customer_id,
        order_id=row.order_id,
        suggestion_text=row.suggestion_text,
        status=row.status,
        owner_response=row.owner_response,
        created_at=row.created_at,
    )


@router.get(
    "/kitchens/{kitchen_id}/suggestions",
    response_model=DishSuggestionListResponse,
    tags=[TAG_SUGGESTIONS],
    summary="List a kitchen's dish suggestions (owner)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Query:** `status` — optional filter, one of `pending`/`accepted`/`rejected`.\n\n"
        "**Response:** `DishSuggestionListResponse` ordered newest first."
    ),
    responses=auth_errors(include_403=True),
)
async def kitchen_suggestions_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status", description="Optional status filter: 'pending', 'accepted', or 'rejected'."),
) -> DishSuggestionListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await list_suggestions(session, kitchen_id, status=status_filter)


@router.patch(
    "/kitchens/{kitchen_id}/suggestions/{suggestion_id}",
    response_model=DishSuggestionResponse,
    tags=[TAG_SUGGESTIONS],
    summary="Accept or reject a dish suggestion",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `DishSuggestionUpdateRequest` — `status` decision plus an optional reply "
        "shown back to the customer.\n\n"
        "**Response:** Updated `DishSuggestionResponse`. 404 if the suggestion does not exist "
        "for this kitchen."
    ),
    responses=auth_errors(include_403=True, include_404=True),
)
async def kitchen_suggestion_update(
    kitchen_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    body: DishSuggestionUpdateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DishSuggestionResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        row = await update_suggestion(session, kitchen_id, suggestion_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await session.commit()
    return row
