import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_owner_id, verify_kitchen_owner
from app.schemas import (
    CuratedRecipeListResponse,
    CuratedRecipeResponse,
    DishTrialListResponse,
    DishTrialResponse,
    LearnRecipeRequest,
    TrialInvitesRequest,
    TrialRatingRequest,
    get_curated_recipe,
    get_kitchen_trial,
    learn_recipe,
    list_curated_recipes,
    list_kitchen_trials,
    promote_trial,
    record_trial_rating,
    send_trial_samples,
    set_trial_invites,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_404, auth_errors

router = APIRouter()

TAG_RECIPES = "Curated Recipes"
TAG_TRIALS = "Dish Trials"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


def _owner_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return auth.removeprefix("Bearer ").strip()


@router.get(
    "/learning/recipes",
    response_model=CuratedRecipeListResponse,
    tags=[TAG_RECIPES],
    summary="Browse the curated recipe portal (F21)",
    description=(
        "**Auth:** None — public portal, browsable by owners looking for menu inspiration.\n\n"
        "**Query:** `category` optional filter; `limit` (1-100, default 50).\n\n"
        "**Response:** `CuratedRecipeListResponse`, alphabetical by title."
    ),
    responses={422: {"description": "Validation error"}},
)
async def learning_recipes_list(
    session: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(default=None, description="Filter by recipe category."),
    limit: int = Query(default=50, ge=1, le=100, description="Max recipes to return (1-100)."),
) -> CuratedRecipeListResponse:
    return await list_curated_recipes(session, category=category, limit=limit)


@router.get(
    "/learning/recipes/{recipe_id}",
    response_model=CuratedRecipeResponse,
    tags=[TAG_RECIPES],
    summary="Get a curated recipe's full detail",
    description=(
        "**Auth:** None — public.\n\n"
        "**Response:** `CuratedRecipeResponse` with ingredients + prep steps. 404 if not found "
        "or inactive."
    ),
    responses={404: RESP_404},
)
async def learning_recipe_detail(
    recipe_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CuratedRecipeResponse:
    try:
        row = await get_curated_recipe(session, recipe_id)
        return CuratedRecipeResponse.model_validate(row)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/kitchens/{kitchen_id}/learning/learn",
    response_model=DishTrialResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_TRIALS],
    summary="Start a dish trial from a curated recipe (F22)",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`. The caller's Bearer token is "
        "forwarded to the catalog service to create the draft dish on the owner's behalf.\n\n"
        "**Body:** `LearnRecipeRequest` — source `recipe_id`, optional custom name/price/cuisine/"
        "category/prep time.\n\n"
        "**Behavior:** Creates a new **inactive** draft dish in the catalog service (never "
        "visible to customers until promoted) and a `DishTrial` row in `status='draft'`. "
        "Publishes `recipe.learned`.\n\n"
        "**Response:** Created `DishTrialResponse`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def learning_learn_recipe(
    kitchen_id: uuid.UUID,
    body: LearnRecipeRequest,
    request: Request,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> DishTrialResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await learn_recipe(
            session,
            kitchen_id,
            body,
            owner_token=_owner_bearer(request),
            publisher=publisher,
        )
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/kitchens/{kitchen_id}/learning/trials",
    response_model=DishTrialListResponse,
    tags=[TAG_TRIALS],
    summary="List a kitchen's dish trials",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Response:** `DishTrialListResponse` ordered newest first (invite lists omitted; use "
        "the detail endpoint for full invite/rating breakdown)."
    ),
    responses=auth_errors(include_403=True),
)
async def learning_trials_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DishTrialListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await list_kitchen_trials(session, kitchen_id)


@router.get(
    "/kitchens/{kitchen_id}/learning/trials/{trial_id}",
    response_model=DishTrialResponse,
    tags=[TAG_TRIALS],
    summary="Get a dish trial's full detail",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Response:** `DishTrialResponse` including the full invite list with per-invite "
        "status and ratings. 404 if the trial does not exist for this kitchen."
    ),
    responses=auth_errors(include_403=True, include_404=True),
)
async def learning_trial_detail(
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DishTrialResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        return await get_kitchen_trial(session, kitchen_id, trial_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/kitchens/{kitchen_id}/learning/trials/{trial_id}/invites",
    response_model=DishTrialResponse,
    tags=[TAG_TRIALS],
    summary="Set the customer invite list for a trial",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Body:** `TrialInvitesRequest` — 5-20 customer UUIDs (must all be known CRM customers "
        "of this kitchen), promo type, and sample price if paid. Replaces any existing invite "
        "list. Rejects if the trial has already moved past `draft`/`sampling` (400).\n\n"
        "**Response:** Updated `DishTrialResponse` with the full invite list."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def learning_trial_invites(
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    body: TrialInvitesRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DishTrialResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await set_trial_invites(session, kitchen_id, trial_id, body)
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/kitchens/{kitchen_id}/learning/trials/{trial_id}/send-samples",
    response_model=DishTrialResponse,
    tags=[TAG_TRIALS],
    summary="Send the sample-offer WhatsApp blast to invitees",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`.\n\n"
        "**Behavior:** Requires at least 5 invites already set (400 otherwise). Dispatches a "
        "WhatsApp blast via the notification service, marks all invites `sent`, moves the trial "
        "to `status='collecting_ratings'`, and publishes `trial.sample_sent`. Rejects if already "
        "promoted (400).\n\n"
        "**Response:** Updated `DishTrialResponse`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def learning_trial_send(
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> DishTrialResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await send_trial_samples(session, kitchen_id, trial_id, publisher=publisher)
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/kitchens/{kitchen_id}/learning/trials/{trial_id}/ratings",
    response_model=DishTrialResponse,
    tags=[TAG_TRIALS],
    summary="Record an invitee's trial-sample rating",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id` (owner records ratings gathered "
        "from the invitee, e.g. via WhatsApp reply).\n\n"
        "**Body:** `TrialRatingRequest` — `invite_id`, home-taste/quality scores, optional "
        "feedback. Rejects an unknown invite, an already-rated invite, or a duplicate rating "
        "(400).\n\n"
        "**Behavior:** Recomputes `avg_rating` (60% home-taste + 40% quality, averaged across "
        "all ratings so far).\n\n"
        "**Response:** Updated `DishTrialResponse`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def learning_trial_rating(
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    body: TrialRatingRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DishTrialResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await record_trial_rating(session, kitchen_id, trial_id, body)
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/kitchens/{kitchen_id}/learning/trials/{trial_id}/promote",
    response_model=DishTrialResponse,
    tags=[TAG_TRIALS],
    summary="Promote a trial dish to the live menu",
    description=(
        "**Auth:** Owner JWT — caller must own `kitchen_id`. The caller's Bearer token is "
        "forwarded to the catalog service to activate the dish.\n\n"
        "**Query:** `force` (default `false`) — set true to promote below `rating_threshold` "
        "(owner's explicit judgment call).\n\n"
        "**Behavior:** Rejects if already promoted, if no ratings collected yet, or if "
        "`avg_rating` is below `rating_threshold` and `force` is not set (400). On success, "
        "activates the draft dish in the catalog service (now visible to customers), sets "
        "`status='promoted'`, and publishes `trial.promoted`.\n\n"
        "**Response:** Updated `DishTrialResponse`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def learning_trial_promote(
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    request: Request,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    force: bool = Query(default=False, description="Force promotion even if below the rating threshold."),
) -> DishTrialResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        result = await promote_trial(
            session,
            kitchen_id,
            trial_id,
            owner_token=_owner_bearer(request),
            publisher=publisher,
            force=force,
        )
        await session.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
