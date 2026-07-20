"""F19b — bulk prep batches + kitchen stock deduct mode."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingredients import ALLOWED_UNITS, _publish_ingredient_event
from app.models import (
    Dish,
    DishIngredient,
    Ingredient,
    KitchenStockSettings,
    PrepBatch,
    PrepBatchDish,
    PrepBatchIngredient,
)
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

DeductMode = Literal["order_ready", "prep_batch_only"]
BatchType = Literal["single_dish", "combo"]
BatchStatus = Literal["draft", "preparing", "prepared", "cancelled"]


class StockSettingsResponse(BaseModel):
    kitchen_id: uuid.UUID
    deduct_mode: DeductMode
    updated_at: datetime | None = None


class StockSettingsUpdateRequest(BaseModel):
    deduct_mode: DeductMode


class PrepBatchDishInput(BaseModel):
    dish_id: uuid.UUID
    quantity_per_portion: float = Field(default=1.0, gt=0, le=100)


class PrepBatchIngredientLine(BaseModel):
    ingredient_id: uuid.UUID
    quantity: float = Field(..., gt=0, le=1_000_000)
    unit: str = Field(..., min_length=1, max_length=20)
    sort_order: int = Field(default=0, ge=0)

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_UNITS:
            raise ValueError(f"unit must be one of: {', '.join(sorted(ALLOWED_UNITS))}")
        return normalized


class PrepBatchCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, examples=["Morning veg thali cook"])
    batch_type: BatchType = "single_dish"
    portions: float = Field(..., gt=0, le=10000, examples=[40])
    dishes: list[PrepBatchDishInput] = Field(..., min_length=1, max_length=20)
    notes: str | None = Field(default=None, max_length=2000)
    status: Literal["draft", "preparing"] = "draft"

    @model_validator(mode="after")
    def validate_dish_count(self) -> PrepBatchCreateRequest:
        n = len(self.dishes)
        if self.batch_type == "single_dish" and n != 1:
            raise ValueError("single_dish batch requires exactly one dish")
        if self.batch_type == "combo" and n < 2:
            raise ValueError("combo batch requires at least two dishes")
        return self


class PrepBatchUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    status: Literal["draft", "preparing", "cancelled"] | None = None
    portions: float | None = Field(default=None, gt=0, le=10000)
    ingredient_lines: list[PrepBatchIngredientLine] | None = Field(default=None, max_length=80)


class PrepBatchDishResponse(BaseModel):
    dish_id: uuid.UUID
    dish_name: str | None = None
    quantity_per_portion: float


class PrepBatchIngredientResponse(BaseModel):
    ingredient_id: uuid.UUID
    ingredient_name: str | None = None
    quantity: float
    unit: str
    sort_order: int


class PrepBatchResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    name: str
    batch_type: str
    portions: float
    status: str
    notes: str | None
    prepared_at: datetime | None
    created_at: datetime
    dishes: list[PrepBatchDishResponse]
    ingredient_lines: list[PrepBatchIngredientResponse]


class PrepBatchListResponse(BaseModel):
    batches: list[PrepBatchResponse]
    total: int


async def get_stock_settings(session: AsyncSession, kitchen_id: uuid.UUID) -> KitchenStockSettings:
    row = await session.get(KitchenStockSettings, kitchen_id)
    if row is None:
        row = KitchenStockSettings(kitchen_id=kitchen_id, deduct_mode="order_ready")
        session.add(row)
        await session.flush()
    return row


async def get_stock_settings_response(
    session: AsyncSession, kitchen_id: uuid.UUID
) -> StockSettingsResponse:
    row = await get_stock_settings(session, kitchen_id)
    return StockSettingsResponse(
        kitchen_id=row.kitchen_id,
        deduct_mode=row.deduct_mode,  # type: ignore[arg-type]
        updated_at=row.updated_at,
    )


async def update_stock_settings(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: StockSettingsUpdateRequest,
) -> StockSettingsResponse:
    row = await get_stock_settings(session, kitchen_id)
    row.deduct_mode = data.deduct_mode
    row.updated_at = datetime.now(UTC)
    await session.flush()
    return await get_stock_settings_response(session, kitchen_id)


async def kitchen_uses_prep_batch_only(session: AsyncSession, kitchen_id: uuid.UUID) -> bool:
    row = await session.get(KitchenStockSettings, kitchen_id)
    return bool(row and row.deduct_mode == "prep_batch_only")


async def _expand_recipe_totals(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dishes: list[PrepBatchDishInput],
    portions: float,
) -> list[PrepBatchIngredientLine]:
    totals: dict[uuid.UUID, dict[str, Any]] = {}
    for d in dishes:
        dish = (
            await session.execute(
                select(Dish).where(Dish.id == d.dish_id, Dish.kitchen_id == kitchen_id)
            )
        ).scalar_one_or_none()
        if dish is None:
            raise ValueError(f"Dish {d.dish_id} not found in this kitchen")
        rows = (
            await session.execute(
                select(DishIngredient, Ingredient)
                .join(Ingredient, Ingredient.id == DishIngredient.ingredient_id)
                .where(
                    DishIngredient.dish_id == d.dish_id,
                    Ingredient.kitchen_id == kitchen_id,
                )
            )
        ).all()
        for line, ingredient in rows:
            qty = float(line.quantity) * float(d.quantity_per_portion) * float(portions)
            bucket = totals.setdefault(
                ingredient.id,
                {"unit": ingredient.unit, "quantity": 0.0, "sort_order": line.sort_order or 0},
            )
            bucket["quantity"] += qty
    return [
        PrepBatchIngredientLine(
            ingredient_id=iid,
            quantity=round(float(meta["quantity"]), 3),
            unit=str(meta["unit"]),
            sort_order=int(meta["sort_order"]),
        )
        for iid, meta in totals.items()
        if meta["quantity"] > 0
    ]


async def _batch_to_response(session: AsyncSession, batch: PrepBatch) -> PrepBatchResponse:
    dish_rows = (
        await session.execute(
            select(PrepBatchDish, Dish)
            .join(Dish, Dish.id == PrepBatchDish.dish_id)
            .where(PrepBatchDish.batch_id == batch.id)
        )
    ).all()
    ing_rows = (
        await session.execute(
            select(PrepBatchIngredient, Ingredient)
            .join(Ingredient, Ingredient.id == PrepBatchIngredient.ingredient_id)
            .where(PrepBatchIngredient.batch_id == batch.id)
            .order_by(PrepBatchIngredient.sort_order)
        )
    ).all()
    return PrepBatchResponse(
        id=batch.id,
        kitchen_id=batch.kitchen_id,
        name=batch.name,
        batch_type=batch.batch_type,
        portions=float(batch.portions),
        status=batch.status,
        notes=batch.notes,
        prepared_at=batch.prepared_at,
        created_at=batch.created_at,
        dishes=[
            PrepBatchDishResponse(
                dish_id=link.dish_id,
                dish_name=dish.name,
                quantity_per_portion=float(link.quantity_per_portion),
            )
            for link, dish in dish_rows
        ],
        ingredient_lines=[
            PrepBatchIngredientResponse(
                ingredient_id=line.ingredient_id,
                ingredient_name=ing.name,
                quantity=float(line.quantity),
                unit=line.unit,
                sort_order=line.sort_order,
            )
            for line, ing in ing_rows
        ],
    )


async def create_prep_batch(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: PrepBatchCreateRequest,
    publisher: EventPublisher,
) -> PrepBatchResponse:
    lines = await _expand_recipe_totals(session, kitchen_id, data.dishes, data.portions)
    if not lines:
        raise ValueError(
            "No recipe ingredient lines found for selected dishes — set recipes before bulk prep"
        )

    batch = PrepBatch(
        kitchen_id=kitchen_id,
        name=data.name.strip(),
        batch_type=data.batch_type,
        portions=Decimal(str(data.portions)),
        status=data.status,
        notes=data.notes,
    )
    session.add(batch)
    await session.flush()

    for d in data.dishes:
        session.add(
            PrepBatchDish(
                batch_id=batch.id,
                dish_id=d.dish_id,
                quantity_per_portion=Decimal(str(d.quantity_per_portion)),
            )
        )
    for idx, line in enumerate(lines):
        session.add(
            PrepBatchIngredient(
                batch_id=batch.id,
                ingredient_id=line.ingredient_id,
                quantity=Decimal(str(line.quantity)),
                unit=line.unit,
                sort_order=line.sort_order if line.sort_order else idx,
            )
        )
    await session.flush()

    event = EventPublisher.build(
        event_type="prep_batch.created",
        aggregate_type="prep_batch",
        aggregate_id=str(batch.id),
        producer="catalog-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "batch_type": batch.batch_type,
            "portions": float(batch.portions),
            "line_count": len(lines),
        },
    )
    await publisher.publish(stream_key("catalog", "ingredient"), event, session=session)
    return await _batch_to_response(session, batch)


async def list_prep_batches(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    *,
    status: str | None = None,
) -> PrepBatchListResponse:
    stmt = select(PrepBatch).where(PrepBatch.kitchen_id == kitchen_id)
    if status:
        stmt = stmt.where(PrepBatch.status == status)
    stmt = stmt.order_by(PrepBatch.created_at.desc()).limit(100)
    rows = (await session.execute(stmt)).scalars().all()
    batches = [await _batch_to_response(session, b) for b in rows]
    return PrepBatchListResponse(batches=batches, total=len(batches))


async def get_prep_batch(
    session: AsyncSession, kitchen_id: uuid.UUID, batch_id: uuid.UUID
) -> PrepBatch:
    batch = (
        await session.execute(
            select(PrepBatch).where(PrepBatch.id == batch_id, PrepBatch.kitchen_id == kitchen_id)
        )
    ).scalar_one_or_none()
    if batch is None:
        raise LookupError("Prep batch not found")
    return batch


async def get_prep_batch_response(
    session: AsyncSession, kitchen_id: uuid.UUID, batch_id: uuid.UUID
) -> PrepBatchResponse:
    batch = await get_prep_batch(session, kitchen_id, batch_id)
    return await _batch_to_response(session, batch)


async def update_prep_batch(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    batch_id: uuid.UUID,
    data: PrepBatchUpdateRequest,
) -> PrepBatchResponse:
    batch = await get_prep_batch(session, kitchen_id, batch_id)
    if batch.status == "prepared":
        raise ValueError("Prepared batches are immutable")
    if batch.status == "cancelled":
        raise ValueError("Cancelled batches are immutable")

    if data.name is not None:
        batch.name = data.name.strip()
    if data.notes is not None:
        batch.notes = data.notes
    if data.status is not None:
        batch.status = data.status
    if data.portions is not None:
        batch.portions = Decimal(str(data.portions))

    if data.ingredient_lines is not None:
        if not data.ingredient_lines:
            raise ValueError("At least one ingredient line is required")
        await session.execute(
            delete(PrepBatchIngredient).where(PrepBatchIngredient.batch_id == batch.id)
        )
        for idx, line in enumerate(data.ingredient_lines):
            ing = (
                await session.execute(
                    select(Ingredient).where(
                        Ingredient.id == line.ingredient_id,
                        Ingredient.kitchen_id == kitchen_id,
                    )
                )
            ).scalar_one_or_none()
            if ing is None:
                raise ValueError(f"Ingredient {line.ingredient_id} not in this kitchen")
            session.add(
                PrepBatchIngredient(
                    batch_id=batch.id,
                    ingredient_id=line.ingredient_id,
                    quantity=Decimal(str(line.quantity)),
                    unit=line.unit,
                    sort_order=line.sort_order if line.sort_order else idx,
                )
            )
    await session.flush()
    return await _batch_to_response(session, batch)


async def mark_prep_batch_prepared(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    batch_id: uuid.UUID,
    publisher: EventPublisher,
) -> PrepBatchResponse:
    batch = await get_prep_batch(session, kitchen_id, batch_id)
    if batch.status == "prepared":
        return await _batch_to_response(session, batch)
    if batch.status == "cancelled":
        raise ValueError("Cannot prepare a cancelled batch")

    lines = (
        await session.execute(
            select(PrepBatchIngredient).where(PrepBatchIngredient.batch_id == batch.id)
        )
    ).scalars().all()
    if not lines:
        raise ValueError("Batch has no ingredient lines to deduct")

    for line in lines:
        row = (
            await session.execute(
                select(Ingredient).where(
                    Ingredient.id == line.ingredient_id,
                    Ingredient.kitchen_id == kitchen_id,
                )
            )
        ).scalar_one()
        previous = float(row.current_stock)
        required = float(line.quantity)
        new_stock = max(0.0, previous - required)
        row.current_stock = Decimal(str(round(new_stock, 3)))

        await _publish_ingredient_event(
            publisher,
            session,
            event_type="ingredient.stock.deducted",
            ingredient_id=row.id,
            kitchen_id=kitchen_id,
            payload={
                "prep_batch_id": str(batch.id),
                "deducted": required,
                "previous_stock": previous,
                "new_stock": new_stock,
            },
        )
        if new_stock <= float(row.low_stock_threshold):
            await _publish_ingredient_event(
                publisher,
                session,
                event_type="ingredient.low_stock",
                ingredient_id=row.id,
                kitchen_id=kitchen_id,
                payload={
                    "current_stock": new_stock,
                    "threshold": float(row.low_stock_threshold),
                    "prep_batch_id": str(batch.id),
                },
            )

    batch.status = "prepared"
    batch.prepared_at = datetime.now(UTC)
    await session.flush()

    event = EventPublisher.build(
        event_type="prep_batch.prepared",
        aggregate_type="prep_batch",
        aggregate_id=str(batch.id),
        producer="catalog-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "portions": float(batch.portions),
            "line_count": len(lines),
        },
    )
    await publisher.publish(stream_key("catalog", "ingredient"), event, session=session)
    return await _batch_to_response(session, batch)
