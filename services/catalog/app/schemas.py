import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DEFAULT_CATEGORY_SLUGS, DEFAULT_CUISINES, Category, Cuisine, Dish, DishMedia
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher


class CategoryResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    name: str
    slug: str
    sort_order: int

    model_config = {"from_attributes": True}


class CuisineResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    name: str
    slug: str
    sort_order: int

    model_config = {"from_attributes": True}


class CuisineMenuGroup(BaseModel):
    cuisine: CuisineResponse
    diets: list["DietMenuGroup"]


class DietMenuGroup(BaseModel):
    diet: CategoryResponse
    dishes: list["DishResponse"]


class DishMediaInput(BaseModel):
    url: str
    is_hero: bool = True
    is_live_capture: bool = False
    captured_at: datetime | None = None

    @model_validator(mode="after")
    def hero_requires_live_capture(self) -> "DishMediaInput":
        return self


class DishCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    cuisine_id: uuid.UUID
    category_id: uuid.UUID
    description: str | None = None
    price: float = Field(..., gt=0)
    prep_time_min: int = Field(default=30, gt=0)
    delivery_time_min: int | None = Field(default=None, ge=0)
    ingredients_description: str | None = None
    quality_measures: str | None = None
    is_active: bool = True
    media: DishMediaInput


class DishMediaResponse(BaseModel):
    id: uuid.UUID
    url: str
    is_hero: bool
    is_live_capture: bool
    captured_at: datetime | None

    model_config = {"from_attributes": True}


class DishResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    cuisine_id: uuid.UUID | None
    category_id: uuid.UUID | None
    cuisine_name: str | None = None
    cuisine_slug: str | None = None
    category_name: str | None = None
    category_slug: str | None = None
    name: str
    price: float
    prep_time_min: int
    delivery_time_min: int | None = None
    description: str | None
    ingredients_description: str | None
    quality_measures: str | None
    is_active: bool
    media: list[DishMediaResponse] = []

    model_config = {"from_attributes": True}


class MenuResponse(BaseModel):
    kitchen_id: uuid.UUID
    dishes: list[DishResponse]
    grouped: list[CuisineMenuGroup] = []
    cuisines: list[CuisineResponse] = []
    diet_categories: list[CategoryResponse] = []


async def ensure_default_cuisines(session: AsyncSession, kitchen_id: uuid.UUID) -> None:
    result = await session.execute(
        select(Cuisine.id).where(Cuisine.kitchen_id == kitchen_id).limit(1)
    )
    if result.scalar_one_or_none():
        return
    rows = [
        {"id": uuid.uuid4(), "kitchen_id": kitchen_id, "name": name, "slug": slug, "sort_order": idx}
        for idx, (name, slug) in enumerate(DEFAULT_CUISINES)
    ]
    stmt = pg_insert(Cuisine).values(rows).on_conflict_do_nothing(
        constraint="uq_cuisine_kitchen_slug"
    )
    await session.execute(stmt)
    await session.flush()


async def ensure_default_categories(session: AsyncSession, kitchen_id: uuid.UUID) -> None:
    await ensure_default_cuisines(session, kitchen_id)
    result = await session.execute(
        select(Category.id).where(Category.kitchen_id == kitchen_id).limit(1)
    )
    if result.scalar_one_or_none():
        return
    rows = [
        {"id": uuid.uuid4(), "kitchen_id": kitchen_id, "name": name, "slug": slug, "sort_order": idx}
        for idx, (name, slug) in enumerate(DEFAULT_CATEGORY_SLUGS)
    ]
    stmt = pg_insert(Category).values(rows).on_conflict_do_nothing(
        constraint="uq_category_kitchen_slug"
    )
    await session.execute(stmt)
    await session.flush()


async def list_cuisines(session: AsyncSession, kitchen_id: uuid.UUID) -> list[Cuisine]:
    await ensure_default_cuisines(session, kitchen_id)
    result = await session.execute(
        select(Cuisine).where(Cuisine.kitchen_id == kitchen_id).order_by(Cuisine.sort_order)
    )
    return list(result.scalars().all())


async def list_categories(session: AsyncSession, kitchen_id: uuid.UUID) -> list[Category]:
    await ensure_default_categories(session, kitchen_id)
    result = await session.execute(
        select(Category)
        .where(Category.kitchen_id == kitchen_id)
        .order_by(Category.sort_order)
    )
    return list(result.scalars().all())


async def create_dish(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: DishCreateRequest,
    publisher: EventPublisher | None,
) -> Dish:
    if data.media.is_hero and not data.media.is_live_capture and data.is_active:
        raise ValueError("Hero image must be live capture for active menu dishes")

    cr = await session.execute(
        select(Cuisine.id).where(Cuisine.id == data.cuisine_id, Cuisine.kitchen_id == kitchen_id)
    )
    if not cr.scalar_one_or_none():
        raise ValueError("Cuisine not found for this kitchen")

    catr = await session.execute(
        select(Category.id).where(Category.id == data.category_id, Category.kitchen_id == kitchen_id)
    )
    if not catr.scalar_one_or_none():
        raise ValueError("Diet category not found for this kitchen")

    dish = Dish(
        kitchen_id=kitchen_id,
        cuisine_id=data.cuisine_id,
        category_id=data.category_id,
        name=data.name,
        description=data.description,
        price=data.price,
        prep_time_min=data.prep_time_min,
        delivery_time_min=data.delivery_time_min,
        ingredients_description=data.ingredients_description,
        quality_measures=data.quality_measures,
        is_active=data.is_active,
    )
    session.add(dish)
    await session.flush()

    media = DishMedia(
        dish_id=dish.id,
        url=data.media.url,
        is_hero=data.media.is_hero,
        is_live_capture=data.media.is_live_capture,
        captured_at=data.media.captured_at or datetime.now(UTC),
    )
    session.add(media)
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="dish.created",
            aggregate_type="dish",
            aggregate_id=str(dish.id),
            producer="catalog-service",
            payload={"kitchen_id": str(kitchen_id), "dish_id": str(dish.id), "name": dish.name},
        )
        await publisher.publish(stream_key("catalog", "dish"), event, session=session)

    return dish


class DishUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    price: float | None = Field(default=None, gt=0)
    is_active: bool | None = None
    prep_time_min: int | None = Field(default=None, gt=0)
    delivery_time_min: int | None = Field(default=None, ge=0)
    description: str | None = None


async def update_dish(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    data: DishUpdateRequest,
    publisher: EventPublisher | None,
) -> Dish:
    result = await session.execute(
        select(Dish).where(Dish.id == dish_id, Dish.kitchen_id == kitchen_id)
    )
    dish = result.scalar_one_or_none()
    if not dish:
        raise ValueError("Dish not found")

    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise ValueError("No fields to update")

    for field, value in updates.items():
        setattr(dish, field, value)
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="dish.updated",
            aggregate_type="dish",
            aggregate_id=str(dish.id),
            producer="catalog-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "dish_id": str(dish.id),
                "changes": list(updates.keys()),
            },
        )
        await publisher.publish(stream_key("catalog", "dish"), event, session=session)

    return dish


async def get_menu(session: AsyncSession, kitchen_id: uuid.UUID) -> list[Dish]:
    result = await session.execute(
        select(Dish).where(Dish.kitchen_id == kitchen_id, Dish.is_active.is_(True))
    )
    return list(result.scalars().all())


async def dish_with_media(session: AsyncSession, dish: Dish) -> DishResponse:
    result = await session.execute(select(DishMedia).where(DishMedia.dish_id == dish.id))
    media = list(result.scalars().all())
    cuisine_name = cuisine_slug = category_name = category_slug = None
    if dish.cuisine_id:
        cr = await session.execute(select(Cuisine).where(Cuisine.id == dish.cuisine_id))
        if c := cr.scalar_one_or_none():
            cuisine_name, cuisine_slug = c.name, c.slug
    if dish.category_id:
        catr = await session.execute(select(Category).where(Category.id == dish.category_id))
        if cat := catr.scalar_one_or_none():
            category_name, category_slug = cat.name, cat.slug
    return DishResponse(
        id=dish.id,
        kitchen_id=dish.kitchen_id,
        cuisine_id=dish.cuisine_id,
        category_id=dish.category_id,
        cuisine_name=cuisine_name,
        cuisine_slug=cuisine_slug,
        category_name=category_name,
        category_slug=category_slug,
        name=dish.name,
        price=float(dish.price),
        prep_time_min=dish.prep_time_min,
        delivery_time_min=dish.delivery_time_min,
        description=dish.description,
        ingredients_description=dish.ingredients_description,
        quality_measures=dish.quality_measures,
        is_active=dish.is_active,
        media=[DishMediaResponse.model_validate(m) for m in media],
    )


def build_menu_grouped(
    cuisines: list[Cuisine],
    categories: list[Category],
    dishes: list[DishResponse],
) -> list[CuisineMenuGroup]:
    cuisine_map = {c.id: c for c in cuisines}
    cat_map = {c.id: c for c in categories}
    groups: dict[tuple[uuid.UUID, uuid.UUID], list[DishResponse]] = {}
    for d in dishes:
        if not d.cuisine_id or not d.category_id:
            continue
        key = (d.cuisine_id, d.category_id)
        groups.setdefault(key, []).append(d)

    result: list[CuisineMenuGroup] = []
    for cuisine in cuisines:
        diet_groups: list[DietMenuGroup] = []
        for cat in categories:
            key = (cuisine.id, cat.id)
            bucket = groups.get(key, [])
            if bucket:
                diet_groups.append(DietMenuGroup(diet=CategoryResponse.model_validate(cat), dishes=bucket))
        if diet_groups:
            result.append(
                CuisineMenuGroup(
                    cuisine=CuisineResponse.model_validate(cuisine),
                    diets=diet_groups,
                )
            )
    return result
