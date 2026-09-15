"""Ingredient balance mapper — F19 domain logic."""

from __future__ import annotations

import re
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredient_health import lookup_health_profile
from app.models import Dish, DishIngredient, DishPrepStep, Ingredient
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

ALLOWED_UNITS = frozenset({"g", "ml", "pcs"})
ALLOWED_HTML_TAGS = frozenset({"p", "strong", "em", "b", "i", "ul", "ol", "li", "br", "h3", "a"})


def _optional_text(value: str | None, *, max_len: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned[:max_len]


def _packs_on_hand(stock: float, pack_size: float | None) -> float | None:
    if pack_size is None or pack_size <= 0:
        return None
    return round(stock / pack_size, 3)


def _float_or_none(value) -> float | None:
    if value is None:
        return None
    return float(value)


def sanitize_html(value: str) -> str:
    """Strip dangerous markup; allow basic formatting for prep steps / dish copy."""
    if not value or not value.strip():
        return ""
    cleaned = re.sub(r"(?is)<(script|style|iframe|object|embed)[^>]*>.*?</\1>", "", value)
    cleaned = re.sub(r"(?is)<(script|style|iframe|object|embed)[^>]*/?>", "", cleaned)
    cleaned = re.sub(r'(?is)\s(on\w+|style)\s*=\s*"[^"]*"', "", cleaned)
    cleaned = re.sub(r"(?is)\s(on\w+|style)\s*=\s*'[^']*'", "", cleaned)
    cleaned = re.sub(r"(?is)\s(on\w+|style)\s*=\s*[^\s>]+", "", cleaned)

    def _rewrite_tag(match: re.Match[str]) -> str:
        raw = match.group(0)
        closing = raw.startswith("</")
        tag = match.group(1).lower().split()[0]
        if tag not in ALLOWED_HTML_TAGS:
            return ""
        if closing or tag != "a":
            return f"</{tag}>" if closing else f"<{tag}>" if tag == "br" else f"<{tag}>"
        href_m = re.search(r'''href\s*=\s*["']([^"']+)["']''', raw, flags=re.I)
        href = (href_m.group(1) if href_m else "").strip()
        if not re.match(r"^https?://", href, flags=re.I):
            return "<a>"
        safe = href.replace('"', "")
        return f'<a href="{safe}" rel="noopener noreferrer" target="_blank">'

    cleaned = re.sub(r"(?is)<\/?([a-z0-9]+)([^>]*)>", _rewrite_tag, cleaned)
    return cleaned.strip()


class IngredientCreateRequest(BaseModel):
    """Add a raw ingredient to the kitchen's stock ledger (F19 ingredient balance mapper)."""

    name: str = Field(..., min_length=1, max_length=255, description="Ingredient name.", examples=["Paneer"])
    unit: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description=f"Unit of measure — one of: {', '.join(sorted(ALLOWED_UNITS))}.",
        examples=["g"],
    )
    current_stock: float = Field(default=0, ge=0, description="Opening stock quantity, in `unit`.")
    low_stock_threshold: float = Field(
        default=0, ge=0, description="Stock level at or below which a low-stock warning is raised."
    )
    brand: str | None = Field(default=None, max_length=120, description="Retail brand on the pantry SKU.")
    pack_size: float | None = Field(
        default=None,
        gt=0,
        description="Retail pack weight/volume in the same `unit` as stock (e.g. 200 for a 200 g pouch).",
    )
    pack_label: str | None = Field(
        default=None, max_length=80, description="Human pack label, e.g. '200 g pouch' or '12 pcs tray'."
    )
    photo_url: str | None = Field(default=None, description="Optional pack/reference photo URL.")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_UNITS:
            raise ValueError(f"unit must be one of: {', '.join(sorted(ALLOWED_UNITS))}")
        return normalized


class IngredientUpdateRequest(BaseModel):
    """Partial update of an ingredient's name/threshold/photo (stock adjusts via a dedicated endpoint)."""

    name: str | None = Field(default=None, min_length=1, max_length=255, description="New ingredient name.")
    low_stock_threshold: float | None = Field(
        default=None, ge=0, description="New low-stock warning threshold."
    )
    brand: str | None = Field(default=None, max_length=120, description="Retail brand on the pantry SKU.")
    pack_size: float | None = Field(
        default=None, gt=0, description="Retail pack size in the same `unit` as stock."
    )
    pack_label: str | None = Field(default=None, max_length=80, description="Human pack label.")
    photo_url: str | None = Field(default=None, description="New reference photo URL.")


class IngredientAdjustStockRequest(BaseModel):
    """Manually adjust ingredient stock (restock, wastage correction, etc.)."""

    delta: float = Field(
        ..., description="Signed quantity change — positive to add stock, negative to remove.", examples=[5.0]
    )
    reason: str = Field(
        default="manual adjustment", max_length=255, description="Audit reason for the adjustment."
    )


class IngredientResponse(BaseModel):
    """Current ingredient stock state."""

    id: uuid.UUID = Field(..., description="Ingredient ID.")
    kitchen_id: uuid.UUID = Field(..., description="Owning kitchen (tenant scope).")
    name: str = Field(..., description="Ingredient name.")
    unit: str = Field(..., description="Unit of measure.")
    current_stock: float = Field(..., description="Current stock quantity, in `unit`.")
    low_stock_threshold: float = Field(..., description="Low-stock warning threshold.")
    brand: str | None = Field(default=None, description="Retail brand on the pantry SKU.")
    pack_size: float | None = Field(default=None, description="Retail pack size in `unit`.")
    pack_label: str | None = Field(default=None, description="Human pack label.")
    packs_on_hand: float | None = Field(
        default=None, description="current_stock / pack_size when a pack size is set."
    )
    photo_url: str | None = Field(default=None, description="Pack/reference photo URL.")
    is_low: bool = Field(..., description="True if current_stock <= low_stock_threshold.")
    health_score: int | None = Field(default=None, description="Library score 0–100 when the name matches.")
    health_benefits: str | None = Field(default=None, description="Typical home-kitchen benefits.")
    health_disadvantages: str | None = Field(default=None, description="Typical cautions for this ingredient.")

    model_config = {"from_attributes": True}


class IngredientListResponse(BaseModel):
    ingredients: list[IngredientResponse] = Field(..., description="Ingredients for this kitchen, alphabetical.")
    total: int = Field(..., description="Total ingredient count.")


class RecipeLineInput(BaseModel):
    """One ingredient line in a dish recipe (quantity required per dish unit)."""

    ingredient_id: uuid.UUID = Field(..., description="Ingredient (must exist for this kitchen).")
    quantity: float = Field(..., gt=0, description="Quantity of this ingredient required per dish unit.")
    unit: str = Field(
        ..., min_length=1, max_length=20, description=f"Unit — one of: {', '.join(sorted(ALLOWED_UNITS))}."
    )
    photo_url: str | None = Field(default=None, description="Optional step/ingredient photo.")
    sort_order: int = Field(default=0, ge=0, description="Display order within the recipe.")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_UNITS:
            raise ValueError(f"unit must be one of: {', '.join(sorted(ALLOWED_UNITS))}")
        return normalized


class RecipeLineResponse(BaseModel):
    ingredient_id: uuid.UUID = Field(..., description="Ingredient ID.")
    ingredient_name: str = Field(..., description="Resolved ingredient name.")
    ingredient_brand: str | None = Field(default=None, description="Brand on the pantry SKU.")
    ingredient_photo_url: str | None = Field(default=None, description="Pack photo on the pantry SKU.")
    pack_size: float | None = Field(default=None, description="Retail pack size on the pantry SKU.")
    pack_label: str | None = Field(default=None, description="Retail pack label on the pantry SKU.")
    quantity: float = Field(..., description="Quantity required per dish unit.")
    unit: str = Field(..., description="Unit of measure.")
    photo_url: str | None = Field(default=None, description="Optional reference photo.")
    sort_order: int = Field(default=0, description="Display order within the recipe.")


class PrepStepInput(BaseModel):
    """One step of a dish's preparation method (sanitized HTML body)."""

    step_order: int = Field(..., ge=1, description="1-indexed step order.")
    title: str | None = Field(default=None, max_length=255, description="Short step title.")
    body_html: str = Field(
        default="", description="Step instructions as sanitized HTML (script/style/inline-handlers stripped)."
    )
    photo_url: str | None = Field(default=None, description="Optional step photo.")
    duration_min: int | None = Field(default=None, ge=0, description="Estimated duration for this step, in minutes.")


class PrepStepResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Prep step ID.")
    step_order: int = Field(..., description="1-indexed step order.")
    title: str | None = Field(default=None, description="Short step title.")
    body_html: str = Field(..., description="Sanitized step instructions (HTML).")
    photo_url: str | None = Field(default=None, description="Optional step photo.")
    duration_min: int | None = Field(default=None, description="Estimated duration, in minutes.")


class DishRecipeRequest(BaseModel):
    """Set (replace) a dish's recipe — ingredient lines + prep steps."""

    lines: list[RecipeLineInput] = Field(..., description="Ingredient lines that make up this dish.")
    prep_steps: list[PrepStepInput] = Field(
        default_factory=list, description="Ordered preparation steps for the kitchen."
    )


class DishRecipeResponse(BaseModel):
    dish_id: uuid.UUID = Field(..., description="Dish ID.")
    dish_name: str = Field(..., description="Resolved dish name.")
    lines: list[RecipeLineResponse] = Field(..., description="Ingredient lines, in sort order.")
    prep_steps: list[PrepStepResponse] = Field(default_factory=list, description="Preparation steps, in order.")


class OrderItemStockInput(BaseModel):
    dish_id: uuid.UUID = Field(..., description="Dish being ordered.")
    quantity: int = Field(..., ge=1, description="Quantity of this dish in the order.")


class LowStockWarning(BaseModel):
    """A projected or actual ingredient shortage for a given order."""

    ingredient_id: uuid.UUID = Field(..., description="Ingredient ID.")
    ingredient_name: str = Field(..., description="Resolved ingredient name.")
    unit: str = Field(..., description="Unit of measure.")
    required: float = Field(..., description="Quantity required to fulfil the order line(s).")
    available: float = Field(..., description="Current stock available.")
    shortfall: float = Field(..., description="Amount short (0 if sufficient stock, but projected as low).")
    is_low: bool = Field(..., description="True if stock is at/below threshold after this order.")


class LowStockCheckRequest(BaseModel):
    """Pre-flight check for ingredient availability before accepting an order (does not deduct stock)."""

    order_id: uuid.UUID | None = Field(default=None, description="Order being checked, if already created.")
    items: list[OrderItemStockInput] = Field(..., description="Dish/quantity lines to check.")


class LowStockCheckResponse(BaseModel):
    warnings: list[LowStockWarning] = Field(..., description="Ingredients projected to run short or low.")
    has_shortfall: bool = Field(..., description="True if any ingredient has an actual shortfall (required > available).")


class StockDeductRequest(BaseModel):
    """Deduct ingredient stock for an accepted order (called on order acceptance)."""

    order_id: uuid.UUID = Field(..., description="Order whose ingredients are being deducted.")
    items: list[OrderItemStockInput] = Field(..., description="Dish/quantity lines to deduct.")


class StockDeductResponse(BaseModel):
    deducted: list[dict] = Field(..., description="Per-ingredient deduction detail (previous/new stock).")
    low_stock_alerts: list[LowStockWarning] = Field(
        ..., description="Ingredients that fell to/below their low-stock threshold after deduction."
    )


def _ingredient_response(row: Ingredient) -> IngredientResponse:
    stock = float(row.current_stock)
    threshold = float(row.low_stock_threshold)
    pack_size = _float_or_none(row.pack_size)
    profile = lookup_health_profile(row.name)
    return IngredientResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        name=row.name,
        unit=row.unit,
        current_stock=stock,
        low_stock_threshold=threshold,
        brand=row.brand,
        pack_size=pack_size,
        pack_label=row.pack_label,
        packs_on_hand=_packs_on_hand(stock, pack_size),
        photo_url=row.photo_url,
        is_low=stock <= threshold,
        health_score=profile.score if profile else None,
        health_benefits=profile.benefits if profile else None,
        health_disadvantages=profile.disadvantages if profile else None,
    )


def _recipe_line_response(line: DishIngredient, ingredient: Ingredient) -> RecipeLineResponse:
    pack_size = _float_or_none(ingredient.pack_size)
    photo = line.photo_url or ingredient.photo_url
    return RecipeLineResponse(
        ingredient_id=ingredient.id,
        ingredient_name=ingredient.name,
        ingredient_brand=ingredient.brand,
        ingredient_photo_url=ingredient.photo_url,
        pack_size=pack_size,
        pack_label=ingredient.pack_label,
        quantity=float(line.quantity),
        unit=line.unit,
        photo_url=photo,
        sort_order=int(line.sort_order or 0),
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
        brand=_optional_text(data.brand, max_len=120),
        pack_size=data.pack_size,
        pack_label=_optional_text(data.pack_label, max_len=80),
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
        payload={"name": row.name, "unit": row.unit, "brand": row.brand},
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
    if data.brand is not None:
        row.brand = _optional_text(data.brand, max_len=120)
    if data.pack_size is not None:
        row.pack_size = data.pack_size
    if data.pack_label is not None:
        row.pack_label = _optional_text(data.pack_label, max_len=80)
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

    lines = [_recipe_line_response(line, ingredient) for line, ingredient in rows]

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
    pantry_rows: dict[uuid.UUID, Ingredient] = {}
    if ingredient_ids:
        found = (
            await session.execute(
                select(Ingredient).where(
                    Ingredient.kitchen_id == kitchen_id,
                    Ingredient.id.in_(ingredient_ids),
                )
            )
        ).scalars().all()
        pantry_rows = {row.id: row for row in found}
        if len(pantry_rows) != len(ingredient_ids):
            raise ValueError("One or more ingredients not found for this kitchen")

    await session.execute(delete(DishIngredient).where(DishIngredient.dish_id == dish_id))
    await session.execute(delete(DishPrepStep).where(DishPrepStep.dish_id == dish_id))

    for index, line in enumerate(data.lines):
        pantry = pantry_rows[line.ingredient_id]
        session.add(
            DishIngredient(
                dish_id=dish_id,
                ingredient_id=line.ingredient_id,
                quantity=line.quantity,
                unit=line.unit,
                photo_url=line.photo_url or pantry.photo_url,
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
    from app.prep_batches import kitchen_uses_prep_batch_only

    # F19b — thali/bulk kitchens deduct via prep batches only (avoid double-count).
    if await kitchen_uses_prep_batch_only(session, kitchen_id):
        return StockDeductResponse(deducted=[], low_stock_alerts=[])

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


class AdminDishRecipeGap(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool


class AdminRecipeCoverage(BaseModel):
    dishes_total: int
    dishes_mapped: int
    dishes_unmapped: list[AdminDishRecipeGap]


class AdminKitchenPantryResponse(BaseModel):
    kitchen_id: uuid.UUID
    ingredients: list[IngredientResponse]
    total: int
    coverage: AdminRecipeCoverage


async def admin_kitchen_pantry(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
) -> AdminKitchenPantryResponse:
    pantry = await list_ingredients(session, kitchen_id)
    dishes = list(
        (
            await session.execute(
                select(Dish).where(Dish.kitchen_id == kitchen_id).order_by(Dish.name)
            )
        ).scalars().all()
    )
    mapped_ids = set(
        (
            await session.execute(
                select(DishIngredient.dish_id)
                .join(Dish, Dish.id == DishIngredient.dish_id)
                .where(Dish.kitchen_id == kitchen_id)
                .distinct()
            )
        ).scalars().all()
    )
    unmapped = [
        AdminDishRecipeGap(id=dish.id, name=dish.name, is_active=bool(dish.is_active))
        for dish in dishes
        if dish.id not in mapped_ids
    ]
    return AdminKitchenPantryResponse(
        kitchen_id=kitchen_id,
        ingredients=pantry.ingredients,
        total=pantry.total,
        coverage=AdminRecipeCoverage(
            dishes_total=len(dishes),
            dishes_mapped=len(dishes) - len(unmapped),
            dishes_unmapped=unmapped,
        ),
    )
