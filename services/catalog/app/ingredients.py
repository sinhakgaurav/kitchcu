"""Ingredient balance mapper — F19 domain logic."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dish, DishIngredient, DishPrepStep, Ingredient
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

ALLOWED_UNITS = frozenset({"g", "ml", "pcs"})
ALLOWED_HTML_TAGS = frozenset({"p", "strong", "em", "b", "i", "ul", "ol", "li", "br", "h3", "a"})


def sanitize_html(value: str) -> str:
    """Strip dangerous markup; allow basic formatting for prep steps."""
    if not value or not value.strip():
        return ""
    cleaned = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", value)
    cleaned = re.sub(r'(?is)\s(on\w+|style)\s*=\s*"[^"]*"', "", cleaned)
    cleaned = re.sub(r"(?is)\s(on\w+|style)\s*=\s*'[^']*'", "", cleaned)

    def _strip_tag(match: re.Match[str]) -> str:
        tag = match.group(1).lower().split()[0]
        if tag in ALLOWED_HTML_TAGS:
            return match.group(0)
        return ""

    cleaned = re.sub(r"(?is)<\/?([a-z0-9]+)([^>]*)>", _strip_tag, cleaned)
    return cleaned.strip()


class IngredientCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    unit: str = Field(..., min_length=1, max_length=20)
    current_stock: float = Field(default=0, ge=0)
    low_stock_threshold: float = Field(default=0, ge=0)
    photo_url: str | None = None

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_UNITS:
            raise ValueError(f"unit must be one of: {', '.join(sorted(ALLOWED_UNITS))}")
        return normalized


class IngredientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    low_stock_threshold: float | None = Field(default=None, ge=0)
    photo_url: str | None = None


class IngredientAdjustStockRequest(BaseModel):
    delta: float
    reason: str = Field(default="manual adjustment", max_length=255)


class IngredientResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    name: str
    unit: str
    current_stock: float
    low_stock_threshold: float
    photo_url: str | None = None
    is_low: bool

    model_config = {"from_attributes": True}


class IngredientListResponse(BaseModel):
    ingredients: list[IngredientResponse]
    total: int


class RecipeLineInput(BaseModel):
    ingredient_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)
    photo_url: str | None = None
    sort_order: int = Field(default=0, ge=0)

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_UNITS:
            raise ValueError(f"unit must be one of: {', '.join(sorted(ALLOWED_UNITS))}")
        return normalized


class RecipeLineResponse(BaseModel):
    ingredient_id: uuid.UUID
    ingredient_name: str
    quantity: float
    unit: str
    photo_url: str | None = None
    sort_order: int = 0


class PrepStepInput(BaseModel):
    step_order: int = Field(..., ge=1)
    title: str | None = Field(default=None, max_length=255)
    body_html: str = Field(default="")
    photo_url: str | None = None
    duration_min: int | None = Field(default=None, ge=0)


class PrepStepResponse(BaseModel):
    id: uuid.UUID
    step_order: int
    title: str | None
    body_html: str
    photo_url: str | None = None
    duration_min: int | None = None


class DishRecipeRequest(BaseModel):
    lines: list[RecipeLineInput]
    prep_steps: list[PrepStepInput] = Field(default_factory=list)


class DishRecipeResponse(BaseModel):
    dish_id: uuid.UUID
    dish_name: str
    lines: list[RecipeLineResponse]
    prep_steps: list[PrepStepResponse] = Field(default_factory=list)


class OrderItemStockInput(BaseModel):
    dish_id: uuid.UUID
    quantity: int = Field(..., ge=1)


class LowStockWarning(BaseModel):
    ingredient_id: uuid.UUID
    ingredient_name: str
    unit: str
    required: float
    available: float
    shortfall: float
    is_low: bool


class LowStockCheckRequest(BaseModel):
    order_id: uuid.UUID | None = None
    items: list[OrderItemStockInput]


class LowStockCheckResponse(BaseModel):
    warnings: list[LowStockWarning]
    has_shortfall: bool


class StockDeductRequest(BaseModel):
    order_id: uuid.UUID
    items: list[OrderItemStockInput]


class StockDeductResponse(BaseModel):
    deducted: list[dict]
    low_stock_alerts: list[LowStockWarning]


def _ingredient_response(row: Ingredient) -> IngredientResponse:
    stock = float(row.current_stock)
    threshold = float(row.low_stock_threshold)
    return IngredientResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        name=row.name,
        unit=row.unit,
        current_stock=stock,
        low_stock_threshold=threshold,
        photo_url=row.photo_url,
        is_low=stock <= threshold,
    )


async def _publish_ingredient_event(
    publisher: EventPublisher,
    session: AsyncSession,
    *,
    event_type: str,
    ingredient_id: uuid.UUID,
    kitchen_id: uuid.UUID,
    payload: dict,
) -> None:
    event = publisher.build(
        event_type=event_type,
        aggregate_type="ingredient",
        aggregate_id=str(ingredient_id),
        producer="catalog-service",
        payload={"kitchen_id": str(kitchen_id), **payload},
    )
    await publisher.publish(stream_key("catalog", "ingredient"), event, session=session)


async def list_ingredients(session: AsyncSession, kitchen_id: uuid.UUID) -> IngredientListResponse:
    rows = (
        await session.execute(
            select(Ingredient)
            .where(Ingredient.kitchen_id == kitchen_id)
            .order_by(Ingredient.name)
        )
    ).scalars().all()
    items = [_ingredient_response(r) for r in rows]
    return IngredientListResponse(ingredients=items, total=len(items))


async def create_ingredient(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: IngredientCreateRequest,
    publisher: EventPublisher,
) -> IngredientResponse:
    name = data.name.strip()
    existing = (
        await session.execute(
            select(Ingredient).where(
                Ingredient.kitchen_id == kitchen_id,
                Ingredient.name.ilike(name),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Ingredient '{name}' already exists")

    row = Ingredient(
        kitchen_id=kitchen_id,
        name=name,
        unit=data.unit,
        current_stock=data.current_stock,
        low_stock_threshold=data.low_stock_threshold,
        photo_url=data.photo_url,
    )
    session.add(row)
    await session.flush()

    await _publish_ingredient_event(
        publisher,
        session,
        event_type="ingredient.created",
        ingredient_id=row.id,
        kitchen_id=kitchen_id,
        payload={"name": row.name, "unit": row.unit},
    )
    return _ingredient_response(row)


async def update_ingredient(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    data: IngredientUpdateRequest,
    publisher: EventPublisher,
) -> IngredientResponse:
    row = (
        await session.execute(
            select(Ingredient).where(
                Ingredient.id == ingredient_id,
                Ingredient.kitchen_id == kitchen_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise ValueError("Ingredient not found")

    if data.name is not None:
        row.name = data.name.strip()
    if data.low_stock_threshold is not None:
        row.low_stock_threshold = data.low_stock_threshold
    if data.photo_url is not None:
        row.photo_url = data.photo_url
    await session.flush()

    await _publish_ingredient_event(
        publisher,
        session,
        event_type="ingredient.updated",
        ingredient_id=row.id,
        kitchen_id=kitchen_id,
        payload={"name": row.name},
    )
    return _ingredient_response(row)


async def adjust_ingredient_stock(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    data: IngredientAdjustStockRequest,
    publisher: EventPublisher,
) -> IngredientResponse:
    row = (
        await session.execute(
            select(Ingredient).where(
                Ingredient.id == ingredient_id,
                Ingredient.kitchen_id == kitchen_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise ValueError("Ingredient not found")

    previous = float(row.current_stock)
    new_stock = max(0.0, previous + data.delta)
    row.current_stock = new_stock
    await session.flush()

    await _publish_ingredient_event(
        publisher,
        session,
        event_type="ingredient.stock.adjusted",
        ingredient_id=row.id,
        kitchen_id=kitchen_id,
        payload={
            "previous_stock": previous,
            "new_stock": new_stock,
            "delta": data.delta,
            "reason": data.reason,
        },
    )

    response = _ingredient_response(row)
    if response.is_low:
        await _publish_ingredient_event(
            publisher,
            session,
            event_type="ingredient.low_stock",
            ingredient_id=row.id,
            kitchen_id=kitchen_id,
            payload={"current_stock": new_stock, "threshold": float(row.low_stock_threshold)},
        )
    return response


async def get_dish_recipe(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
) -> DishRecipeResponse:
    dish = (
        await session.execute(
            select(Dish).where(Dish.id == dish_id, Dish.kitchen_id == kitchen_id)
        )
    ).scalar_one_or_none()
    if not dish:
        raise ValueError("Dish not found")

    rows = (
        await session.execute(
            select(DishIngredient, Ingredient)
            .join(Ingredient, Ingredient.id == DishIngredient.ingredient_id)
            .where(DishIngredient.dish_id == dish_id, Ingredient.kitchen_id == kitchen_id)
            .order_by(DishIngredient.sort_order, Ingredient.name)
        )
    ).all()

    lines = [
        RecipeLineResponse(
            ingredient_id=ingredient.id,
            ingredient_name=ingredient.name,
            quantity=float(line.quantity),
            unit=line.unit,
            photo_url=line.photo_url,
            sort_order=int(line.sort_order or 0),
        )
        for line, ingredient in rows
    ]

    step_rows = (
        await session.execute(
            select(DishPrepStep)
            .where(DishPrepStep.dish_id == dish_id)
            .order_by(DishPrepStep.step_order)
        )
    ).scalars().all()

    prep_steps = [
        PrepStepResponse(
            id=step.id,
            step_order=step.step_order,
            title=step.title,
            body_html=step.body_html,
            photo_url=step.photo_url,
            duration_min=step.duration_min,
        )
        for step in step_rows
    ]

    return DishRecipeResponse(
        dish_id=dish.id,
        dish_name=dish.name,
        lines=lines,
        prep_steps=prep_steps,
    )


async def set_dish_recipe(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    data: DishRecipeRequest,
    publisher: EventPublisher,
) -> DishRecipeResponse:
    dish = (
        await session.execute(
            select(Dish).where(Dish.id == dish_id, Dish.kitchen_id == kitchen_id)
        )
    ).scalar_one_or_none()
    if not dish:
        raise ValueError("Dish not found")

    ingredient_ids = {line.ingredient_id for line in data.lines}
    if ingredient_ids:
        valid = (
            await session.execute(
                select(Ingredient.id).where(
                    Ingredient.kitchen_id == kitchen_id,
                    Ingredient.id.in_(ingredient_ids),
                )
            )
        ).scalars().all()
        if len(valid) != len(ingredient_ids):
            raise ValueError("One or more ingredients not found for this kitchen")

    await session.execute(delete(DishIngredient).where(DishIngredient.dish_id == dish_id))
    await session.execute(delete(DishPrepStep).where(DishPrepStep.dish_id == dish_id))

    for index, line in enumerate(data.lines):
        session.add(
            DishIngredient(
                dish_id=dish_id,
                ingredient_id=line.ingredient_id,
                quantity=line.quantity,
                unit=line.unit,
                photo_url=line.photo_url,
                sort_order=line.sort_order if line.sort_order else index,
            )
        )

    for step in sorted(data.prep_steps, key=lambda s: s.step_order):
        body = sanitize_html(step.body_html)
        if not body and not step.title:
            continue
        session.add(
            DishPrepStep(
                dish_id=dish_id,
                step_order=step.step_order,
                title=step.title,
                body_html=body or f"<p>{step.title}</p>",
                photo_url=step.photo_url,
                duration_min=step.duration_min,
            )
        )
    await session.flush()

    await _publish_ingredient_event(
        publisher,
        session,
        event_type="ingredient.recipe.updated",
        ingredient_id=dish_id,
        kitchen_id=kitchen_id,
        payload={
            "dish_id": str(dish_id),
            "line_count": len(data.lines),
            "prep_step_count": len(data.prep_steps),
        },
    )
    return await get_dish_recipe(session, kitchen_id, dish_id)


async def _aggregate_requirements(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    items: list[OrderItemStockInput],
) -> dict[uuid.UUID, dict]:
    """Sum ingredient qty needed across order line items."""
    requirements: dict[uuid.UUID, dict] = {}
    for item in items:
        recipe_rows = (
            await session.execute(
                select(DishIngredient, Ingredient)
                .join(Ingredient, Ingredient.id == DishIngredient.ingredient_id)
                .join(Dish, Dish.id == DishIngredient.dish_id)
                .where(
                    DishIngredient.dish_id == item.dish_id,
                    Dish.kitchen_id == kitchen_id,
                )
            )
        ).all()
        for line, ingredient in recipe_rows:
            needed = float(line.quantity) * item.quantity
            bucket = requirements.setdefault(
                ingredient.id,
                {
                    "ingredient_id": ingredient.id,
                    "ingredient_name": ingredient.name,
                    "unit": ingredient.unit,
                    "required": 0.0,
                    "available": float(ingredient.current_stock),
                    "threshold": float(ingredient.low_stock_threshold),
                },
            )
            bucket["required"] += needed
            bucket["available"] = float(ingredient.current_stock)
    return requirements


async def check_low_stock_for_order(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: LowStockCheckRequest,
) -> LowStockCheckResponse:
    requirements = await _aggregate_requirements(session, kitchen_id, data.items)
    warnings: list[LowStockWarning] = []
    for bucket in requirements.values():
        required = bucket["required"]
        available = bucket["available"]
        shortfall = max(0.0, required - available)
        projected = available - required
        is_low = projected <= bucket["threshold"]
        if shortfall > 0 or is_low:
            warnings.append(
                LowStockWarning(
                    ingredient_id=bucket["ingredient_id"],
                    ingredient_name=bucket["ingredient_name"],
                    unit=bucket["unit"],
                    required=round(required, 3),
                    available=round(available, 3),
                    shortfall=round(shortfall, 3),
                    is_low=is_low or shortfall > 0,
                )
            )
    return LowStockCheckResponse(
        warnings=warnings,
        has_shortfall=any(w.shortfall > 0 for w in warnings),
    )


async def deduct_stock_for_order(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: StockDeductRequest,
    publisher: EventPublisher,
) -> StockDeductResponse:
    requirements = await _aggregate_requirements(session, kitchen_id, data.items)
    if not requirements:
        return StockDeductResponse(deducted=[], low_stock_alerts=[])

    deducted: list[dict] = []
    low_alerts: list[LowStockWarning] = []

    for ingredient_id, bucket in requirements.items():
        row = (
            await session.execute(
                select(Ingredient).where(
                    Ingredient.id == ingredient_id,
                    Ingredient.kitchen_id == kitchen_id,
                )
            )
        ).scalar_one()
        previous = float(row.current_stock)
        required = bucket["required"]
        new_stock = max(0.0, previous - required)
        row.current_stock = Decimal(str(round(new_stock, 3)))
        deducted.append(
            {
                "ingredient_id": str(ingredient_id),
                "ingredient_name": row.name,
                "deducted": round(required, 3),
                "previous_stock": previous,
                "new_stock": new_stock,
            }
        )

        await _publish_ingredient_event(
            publisher,
            session,
            event_type="ingredient.stock.deducted",
            ingredient_id=row.id,
            kitchen_id=kitchen_id,
            payload={
                "order_id": str(data.order_id),
                "deducted": required,
                "previous_stock": previous,
                "new_stock": new_stock,
            },
        )

        if new_stock <= float(row.low_stock_threshold):
            low_alerts.append(
                LowStockWarning(
                    ingredient_id=row.id,
                    ingredient_name=row.name,
                    unit=row.unit,
                    required=round(required, 3),
                    available=round(new_stock, 3),
                    shortfall=0.0,
                    is_low=True,
                )
            )
            await _publish_ingredient_event(
                publisher,
                session,
                event_type="ingredient.low_stock",
                ingredient_id=row.id,
                kitchen_id=kitchen_id,
                payload={
                    "current_stock": new_stock,
                    "threshold": float(row.low_stock_threshold),
                    "order_id": str(data.order_id),
                },
            )

    await session.flush()
    return StockDeductResponse(deducted=deducted, low_stock_alerts=low_alerts)
