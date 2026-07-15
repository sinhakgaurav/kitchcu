import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DEFAULT_CATEGORY_SLUGS, DEFAULT_CUISINES, Category, Cuisine, Dish, DishMedia
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher


def projected_ready_min(
    prep: int,
    delivery: int | None,
    max_time: int | None,
    *,
    for_delivery: bool = True,
) -> int:
    """Customer-facing readiness minutes.

    Prefer owner ``max_time`` (honest ceiling). Otherwise prep (+ delivery when applicable).
    Cart / order ETA uses ``max(...)`` across dishes — quality-first parallel prep, not race sums.
    """
    if max_time is not None:
        return max_time
    delivery_part = (delivery or 0) if for_delivery else 0
    return prep + delivery_part


def default_max_time_min(prep: int, delivery: int | None) -> int:
    return prep + (delivery or 0)


def validate_timing(prep: int, delivery: int | None, max_time: int) -> None:
    if max_time < prep:
        raise ValueError("max_time_min must be greater than or equal to prep_time_min")
    floor = default_max_time_min(prep, delivery)
    if max_time < floor:
        raise ValueError(
            f"max_time_min must cover prep + delivery ({floor} min); got {max_time}"
        )


class CategoryResponse(BaseModel):
    """A diet category (e.g. veg, non-veg, vegan) — used to filter and group the menu."""

    id: uuid.UUID = Field(..., description="Category ID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen (tenant scope).")
    name: str = Field(..., description="Display name.", examples=["Vegetarian"])
    slug: str = Field(..., description="Stable slug — one of the seed diet slugs.", examples=["veg"])
    sort_order: int = Field(..., description="Display order on the menu (ascending).", examples=[0])

    model_config = {"from_attributes": True}


class CuisineResponse(BaseModel):
    """A cuisine grouping (e.g. North Indian, Chinese) — used to organize the menu."""

    id: uuid.UUID = Field(..., description="Cuisine ID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen (tenant scope).")
    name: str = Field(..., description="Display name.", examples=["North Indian"])
    slug: str = Field(..., description="Stable slug.", examples=["north_indian"])
    sort_order: int = Field(..., description="Display order on the menu (ascending).", examples=[0])

    model_config = {"from_attributes": True}


class CuisineMenuGroup(BaseModel):
    """Menu dishes grouped by cuisine, then by diet category — the customer-facing menu tree."""

    cuisine: CuisineResponse = Field(..., description="The cuisine this group belongs to.")
    diets: list["DietMenuGroup"] = Field(..., description="Dishes under this cuisine, split by diet category.")


class DietMenuGroup(BaseModel):
    """Dishes of a single diet category within a cuisine group."""

    diet: CategoryResponse = Field(..., description="The diet category this bucket belongs to.")
    dishes: list["DishResponse"] = Field(..., description="Active dishes matching this cuisine + diet.")


class DishMediaInput(BaseModel):
    """Hero/gallery photo for a dish.

    Truth-in-media principle: dish hero images must be ``is_live_capture=true``
    (photographed by the kitchen, never a stock photo) — enforced server-side in
    ``create_dish`` for active dishes.
    """

    url: str = Field(..., description="Public media URL (from the media upload endpoint).")
    is_hero: bool = Field(
        default=True,
        description="Whether this is the primary dish image shown on the menu card.",
    )
    is_live_capture: bool = Field(
        default=False,
        description=(
            "True only if this photo was captured live by the kitchen (getUserMedia / camera capture), "
            "never a stock photo. Required to be true when is_hero=true and the dish is active."
        ),
    )
    captured_at: datetime | None = Field(
        default=None,
        description="Capture timestamp for live-capture photos (audit trail for truth-in-media).",
    )

    @model_validator(mode="after")
    def hero_requires_live_capture(self) -> "DishMediaInput":
        return self


class DishCreateRequest(BaseModel):
    """Create a new dish on the kitchen's menu.

    **Truth in media:** if ``media.is_hero`` is true and the dish is created active
    (``is_active=true``), ``media.is_live_capture`` must also be true — stock-photo
    hero images are rejected (400) to protect customer trust.
    """

    name: str = Field(..., min_length=2, max_length=255, description="Dish name.", examples=["Paneer Butter Masala"])
    cuisine_id: uuid.UUID = Field(..., description="Cuisine this dish belongs to (must exist for this kitchen).")
    category_id: uuid.UUID = Field(..., description="Diet category (must exist for this kitchen).")
    description: str | None = Field(default=None, description="Customer-facing dish description.")
    price: float = Field(..., gt=0, description="Price in INR.", examples=[220.0])
    prep_time_min: int = Field(default=30, gt=0, description="Owner-set preparation time in minutes.")
    delivery_time_min: int | None = Field(
        default=None, ge=0, description="Owner-set delivery time in minutes (never a fake speed guarantee)."
    )
    max_time_min: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Owner-set max readiness minutes shown to customers. "
            "Defaults to prep + delivery. Cart ETA uses the max across dishes."
        ),
    )
    ingredients_description: str | None = Field(default=None, description="Free-text ingredient list for customers.")
    quality_measures: str | None = Field(
        default=None, description="Free-text hygiene/quality notes shown to build customer trust."
    )
    is_active: bool = Field(default=True, description="Whether the dish is visible on the live menu.")
    media: DishMediaInput = Field(..., description="Hero image — see truth-in-media requirement above.")

    @model_validator(mode="after")
    def _timing(self):
        max_time = self.max_time_min
        if max_time is None:
            max_time = default_max_time_min(self.prep_time_min, self.delivery_time_min)
            object.__setattr__(self, "max_time_min", max_time)
        validate_timing(self.prep_time_min, self.delivery_time_min, max_time)
        return self


class DishMediaResponse(BaseModel):
    """A stored dish photo (hero or gallery)."""

    id: uuid.UUID = Field(..., description="Media row ID.")
    url: str = Field(..., description="Public media URL.")
    is_hero: bool = Field(..., description="Whether this is the primary menu-card image.")
    is_live_capture: bool = Field(..., description="Whether this photo was live-captured (truth in media).")
    captured_at: datetime | None = Field(default=None, description="Capture timestamp, if live-captured.")

    model_config = {"from_attributes": True}


class DishResponse(BaseModel):
    """A dish with resolved cuisine/category names and media, as shown to owners and customers."""

    id: uuid.UUID = Field(..., description="Dish ID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen (tenant scope).")
    cuisine_id: uuid.UUID | None = Field(default=None, description="Cuisine ID.")
    category_id: uuid.UUID | None = Field(default=None, description="Diet category ID.")
    cuisine_name: str | None = Field(default=None, description="Resolved cuisine display name.")
    cuisine_slug: str | None = Field(default=None, description="Resolved cuisine slug.")
    category_name: str | None = Field(default=None, description="Resolved diet category display name.")
    category_slug: str | None = Field(default=None, description="Resolved diet category slug.")
    name: str = Field(..., description="Dish name.")
    price: float = Field(..., description="Price in INR.")
    prep_time_min: int = Field(..., description="Owner-set preparation time in minutes.")
    delivery_time_min: int | None = Field(default=None, description="Owner-set delivery time in minutes.")
    max_time_min: int = Field(..., description="Owner-set max readiness minutes (customer projection).")
    projected_ready_min: int = Field(
        ...,
        description="Minutes customers should expect for this dish (max_time; quality-first SLA).",
    )
    description: str | None = Field(default=None, description="Customer-facing dish description.")
    ingredients_description: str | None = Field(default=None, description="Free-text ingredient list.")
    quality_measures: str | None = Field(default=None, description="Free-text hygiene/quality notes.")
    is_active: bool = Field(..., description="Whether the dish is visible on the live menu.")
    media: list[DishMediaResponse] = Field(default_factory=list, description="Hero + gallery photos.")

    model_config = {"from_attributes": True}


class MenuResponse(BaseModel):
    """The full active menu for a kitchen — flat list plus cuisine/diet grouping for the menu UI."""

    kitchen_id: uuid.UUID = Field(..., description="Kitchen this menu belongs to.")
    dishes: list[DishResponse] = Field(..., description="All active dishes, flat list.")
    grouped: list[CuisineMenuGroup] = Field(default_factory=list, description="Dishes grouped by cuisine → diet.")
    cuisines: list[CuisineResponse] = Field(default_factory=list, description="Cuisines with at least one dish.")
    diet_categories: list[CategoryResponse] = Field(
        default_factory=list, description="Diet categories available for this kitchen."
    )


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
        max_time_min=data.max_time_min or default_max_time_min(data.prep_time_min, data.delivery_time_min),
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
    """Partial update of a dish — only supplied fields are changed."""

    name: str | None = Field(default=None, min_length=2, max_length=255, description="New dish name.")
    price: float | None = Field(default=None, gt=0, description="New price in INR.")
    is_active: bool | None = Field(default=None, description="Toggle menu visibility.")
    prep_time_min: int | None = Field(default=None, gt=0, description="New preparation time in minutes.")
    delivery_time_min: int | None = Field(default=None, ge=0, description="New delivery time in minutes.")
    max_time_min: int | None = Field(default=None, gt=0, description="New max readiness minutes for customers.")
    description: str | None = Field(default=None, description="New customer-facing description.")

    @model_validator(mode="after")
    def _timing_pair(self):
        if self.prep_time_min is not None and self.max_time_min is not None:
            if self.max_time_min < self.prep_time_min:
                raise ValueError("max_time_min must be greater than or equal to prep_time_min")
        return self


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

    try:
        validate_timing(dish.prep_time_min, dish.delivery_time_min, dish.max_time_min)
    except ValueError:
        # Auto-lift max when owner raises prep/delivery without updating max.
        floor = default_max_time_min(dish.prep_time_min, dish.delivery_time_min)
        if dish.max_time_min < floor and "max_time_min" not in updates:
            dish.max_time_min = floor
        else:
            raise

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
        max_time_min=dish.max_time_min,
        projected_ready_min=projected_ready_min(
            dish.prep_time_min, dish.delivery_time_min, dish.max_time_min, for_delivery=True
        ),
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
