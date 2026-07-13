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

router = APIRouter()


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


def _owner_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return auth.removeprefix("Bearer ").strip()


@router.get("/learning/recipes", response_model=CuratedRecipeListResponse)
async def learning_recipes_list(
    session: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> CuratedRecipeListResponse:
    return await list_curated_recipes(session, category=category, limit=limit)


@router.get("/learning/recipes/{recipe_id}", response_model=CuratedRecipeResponse)
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


@router.get("/kitchens/{kitchen_id}/learning/trials", response_model=DishTrialListResponse)
async def learning_trials_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DishTrialListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await list_kitchen_trials(session, kitchen_id)


@router.get("/kitchens/{kitchen_id}/learning/trials/{trial_id}", response_model=DishTrialResponse)
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
)
async def learning_trial_promote(
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    request: Request,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
    force: bool = Query(default=False),
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
