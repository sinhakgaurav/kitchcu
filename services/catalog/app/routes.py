import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_owner_id, verify_kitchen_owner
from app.schemas import (
    CategoryResponse,
    CuisineResponse,
    DishCreateRequest,
    DishResponse,
    DishUpdateRequest,
    MenuResponse,
    build_menu_grouped,
    create_dish,
    dish_with_media,
    list_categories,
    list_cuisines,
    get_menu,
    update_dish,
)
from app.ingredients import (
    DishRecipeRequest,
    DishRecipeResponse,
    IngredientAdjustStockRequest,
    IngredientCreateRequest,
    IngredientListResponse,
    IngredientResponse,
    IngredientUpdateRequest,
    adjust_ingredient_stock,
    create_ingredient,
    get_dish_recipe,
    list_ingredients,
    set_dish_recipe,
    update_ingredient,
)
from app.media import MediaUploadResponse, upload_kitchen_media
from ckac_common.cache import get_cached_menu, invalidate_menu_cache, set_cached_menu
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_422, auth_errors

router = APIRouter()

TAG_MENU = "Menu"
TAG_DISHES = "Dishes"
TAG_INGREDIENTS = "Ingredients"
TAG_MEDIA = "Media"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@router.get(
    "/kitchens/{kitchen_id}/cuisines",
    response_model=list[CuisineResponse],
    tags=[TAG_MENU],
    summary="List cuisines",
    description=(
        "Public — list cuisine groupings for a kitchen (e.g. North Indian, Chinese), seeded on first "
        "access with kitchCU's default cuisine set. Used to organize the customer-facing menu."
    ),
    responses={422: RESP_422},
)
async def cuisines_list(
    kitchen_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CuisineResponse]:
    items = await list_cuisines(session, kitchen_id)
    return [CuisineResponse.model_validate(c) for c in items]


@router.get(
    "/kitchens/{kitchen_id}/categories",
    response_model=list[CategoryResponse],
    tags=[TAG_MENU],
    summary="List diet categories (owner)",
    description=(
        "Owner-only — list diet categories (veg/non-veg/vegan/etc.) for this kitchen, seeded on first "
        "access. Requires the caller to own the kitchen."
    ),
    responses=auth_errors(include_403=True),
)
async def categories_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CategoryResponse]:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    cats = await list_categories(session, kitchen_id)
    return cats


@router.get(
    "/kitchens/{kitchen_id}/menu/diet-categories",
    response_model=list[CategoryResponse],
    tags=[TAG_MENU],
    summary="List diet categories (public)",
    description="Public — diet categories for customer-facing menu filters (veg/non-veg/vegan/etc.).",
    responses={422: RESP_422},
)
async def diet_categories_public(
    kitchen_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CategoryResponse]:
    cats = await list_categories(session, kitchen_id)
    return [CategoryResponse.model_validate(c) for c in cats]


@router.get(
    "/kitchens/{kitchen_id}/menu",
    response_model=MenuResponse,
    tags=[TAG_MENU],
    summary="Get the active menu",
    description=(
        "Public — the kitchen's active menu: flat dish list plus cuisine → diet grouping for the menu UI. "
        "Cached in Redis for 5 minutes (`menu:{kitchen_id}`); invalidated on dish create/update."
    ),
    responses={422: RESP_422},
)
async def menu_get(
    kitchen_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MenuResponse:
    from app.deps import require_kitchen_exists
    from app.main import redis_client

    await require_kitchen_exists(kitchen_id, session)

    cached = await get_cached_menu(redis_client, kitchen_id)
    if cached:
        return MenuResponse(**cached)

    dishes = await get_menu(session, kitchen_id)
    enriched = [await dish_with_media(session, d) for d in dishes]
    cuisines = await list_cuisines(session, kitchen_id)
    categories = await list_categories(session, kitchen_id)
    grouped = build_menu_grouped(cuisines, categories, enriched)
    response = MenuResponse(
        kitchen_id=kitchen_id,
        dishes=enriched,
        grouped=grouped,
        cuisines=[CuisineResponse.model_validate(c) for c in cuisines],
        diet_categories=[CategoryResponse.model_validate(c) for c in categories],
    )
    await set_cached_menu(redis_client, kitchen_id, response.model_dump(mode="json"))
    return response


@router.post(
    "/kitchens/{kitchen_id}/dishes",
    response_model=DishResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_DISHES],
    summary="Create a dish",
    description=(
        "Owner-only — add a dish to the kitchen's menu. **Truth in media:** if the hero image "
        "(`media.is_hero=true`) is not live-captured (`media.is_live_capture=true`) and the dish is "
        "created active, the request is rejected with 400 to protect customer trust. Invalidates the "
        "menu cache and publishes `dish.created`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def dish_create(
    kitchen_id: uuid.UUID,
    body: DishCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> DishResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        dish = await create_dish(session, kitchen_id, body, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    from app.main import redis_client

    await invalidate_menu_cache(redis_client, kitchen_id)
    return await dish_with_media(session, dish)


@router.patch(
    "/kitchens/{kitchen_id}/dishes/{dish_id}",
    response_model=DishResponse,
    tags=[TAG_DISHES],
    summary="Update a dish",
    description=(
        "Owner-only — partial update of a dish (price, name, active flag, prep/delivery time, "
        "description). Invalidates the menu cache and publishes `dish.updated`."
    ),
    responses={**auth_errors(include_403=True, include_404=True), 400: RESP_400},
)
async def dish_update(
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    body: DishUpdateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> DishResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        dish = await update_dish(session, kitchen_id, dish_id, body, publisher)
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    from app.main import redis_client

    await invalidate_menu_cache(redis_client, kitchen_id)
    return await dish_with_media(session, dish)


@router.get(
    "/kitchens/{kitchen_id}/ingredients",
    response_model=IngredientListResponse,
    tags=[TAG_INGREDIENTS],
    summary="List ingredients",
    description="Owner-only — list the kitchen's raw ingredient stock ledger (F19 ingredient balance mapper).",
    responses=auth_errors(include_403=True),
)
async def ingredients_list(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> IngredientListResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    return await list_ingredients(session, kitchen_id)


@router.post(
    "/kitchens/{kitchen_id}/ingredients",
    response_model=IngredientResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_INGREDIENTS],
    summary="Add an ingredient",
    description="Owner-only — add a raw ingredient with opening stock and low-stock threshold. Rejects duplicate names (400).",
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def ingredient_create(
    kitchen_id: uuid.UUID,
    body: IngredientCreateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> IngredientResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        row = await create_ingredient(session, kitchen_id, body, publisher)
        return row
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
    "/kitchens/{kitchen_id}/ingredients/{ingredient_id}",
    response_model=IngredientResponse,
    tags=[TAG_INGREDIENTS],
    summary="Update an ingredient",
    description="Owner-only — update an ingredient's name, low-stock threshold, or photo.",
    responses={**auth_errors(include_403=True, include_404=True), 400: RESP_400},
)
async def ingredient_update(
    kitchen_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    body: IngredientUpdateRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> IngredientResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        row = await update_ingredient(session, kitchen_id, ingredient_id, body, publisher)
        return row
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post(
    "/kitchens/{kitchen_id}/ingredients/{ingredient_id}/adjust-stock",
    response_model=IngredientResponse,
    tags=[TAG_INGREDIENTS],
    summary="Adjust ingredient stock",
    description=(
        "Owner-only — manually adjust ingredient stock (restock, wastage correction). Stock never goes "
        "negative; publishes `ingredient.stock.adjusted` and `ingredient.low_stock` if the threshold is crossed."
    ),
    responses={**auth_errors(include_403=True, include_404=True), 400: RESP_400},
)
async def ingredient_adjust_stock(
    kitchen_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    body: IngredientAdjustStockRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> IngredientResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        row = await adjust_ingredient_stock(session, kitchen_id, ingredient_id, body, publisher)
        return row
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post(
    "/kitchens/{kitchen_id}/media/upload",
    response_model=MediaUploadResponse,
    tags=[TAG_MEDIA],
    summary="Upload kitchen media",
    description=(
        "Owner-only — upload a dish/ingredient/prep-step photo (JPEG/PNG/WebP, max 10MB, content sniffed "
        "from magic bytes). Set `is_live_capture=true` when the photo was captured live via the camera "
        "(getUserMedia) — required for active dish hero images (truth in media). Returns the public URL "
        "to feed into `DishMediaInput.url`."
    ),
    responses={**auth_errors(include_403=True), 400: RESP_400},
)
async def kitchen_media_upload(
    kitchen_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(..., description="Image file — JPEG, PNG, or WebP, max 10MB.")],
    is_live_capture: Annotated[
        bool, Form(description="True only if captured live via camera (getUserMedia), never a stock photo.")
    ] = False,
    context: Annotated[
        str, Form(description="Upload context — one of: dish, ingredient, prep_step, general.")
    ] = "general",
    captured_at: Annotated[
        str | None, Form(description="ISO-8601 capture timestamp, required context for live-capture audit.")
    ] = None,
) -> MediaUploadResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        return await upload_kitchen_media(
            kitchen_id=kitchen_id,
            file=file,
            is_live_capture=is_live_capture,
            context=context,
            captured_at=captured_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
    response_model=DishRecipeResponse,
    tags=[TAG_DISHES, TAG_INGREDIENTS],
    summary="Get a dish's recipe",
    description="Owner-only — ingredient lines + prep steps for a dish (F19 ingredient balance mapper).",
    responses=auth_errors(include_403=True, include_404=True),
)
async def dish_recipe_get(
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DishRecipeResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        return await get_dish_recipe(session, kitchen_id, dish_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put(
    "/kitchens/{kitchen_id}/dishes/{dish_id}/recipe",
    response_model=DishRecipeResponse,
    tags=[TAG_DISHES, TAG_INGREDIENTS],
    summary="Set a dish's recipe",
    description=(
        "Owner-only — replace a dish's recipe (ingredient lines + prep steps) in full. Prep step HTML is "
        "sanitized server-side. Used by stock deduction on order acceptance and low-stock warnings."
    ),
    responses={**auth_errors(include_403=True, include_404=True), 400: RESP_400},
)
async def dish_recipe_set(
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    body: DishRecipeRequest,
    owner_id: Annotated[uuid.UUID, Depends(get_current_owner_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> DishRecipeResponse:
    await verify_kitchen_owner(kitchen_id, owner_id, session)
    try:
        recipe = await set_dish_recipe(session, kitchen_id, dish_id, body, publisher)
        return recipe
    except ValueError as exc:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
