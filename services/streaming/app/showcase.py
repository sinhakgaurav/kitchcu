"""Per-dish live showcase — load catalog recipe snapshot for streaming sessions."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SHOWCASE_PHASES

SHOWCASE_PHASE_SET = frozenset(SHOWCASE_PHASES)


async def load_dish_showcase_snapshot(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
) -> dict:
    """Cross-schema read of active dish + recipe for viewer showcase (ownership via kitchen_id)."""
    dish = (
        await session.execute(
            text(
                """
                SELECT id, name
                FROM ckac_catalog.dishes
                WHERE id = :did AND kitchen_id = :kid AND is_active = true
                LIMIT 1
                """
            ),
            {"did": dish_id, "kid": kitchen_id},
        )
    ).mappings().first()
    if not dish:
        raise ValueError("Dish not found or inactive for this kitchen")

    lines = (
        await session.execute(
            text(
                """
                SELECT
                    i.name AS ingredient_name,
                    di.quantity,
                    di.unit,
                    di.photo_url,
                    di.sort_order
                FROM ckac_catalog.dish_ingredients di
                JOIN ckac_catalog.ingredients i ON i.id = di.ingredient_id
                WHERE di.dish_id = :did AND i.kitchen_id = :kid
                ORDER BY di.sort_order, i.name
                """
            ),
            {"did": dish_id, "kid": kitchen_id},
        )
    ).mappings().all()

    steps = (
        await session.execute(
            text(
                """
                SELECT step_order, title, body_html, photo_url, duration_min
                FROM ckac_catalog.dish_prep_steps
                WHERE dish_id = :did
                ORDER BY step_order
                """
            ),
            {"did": dish_id},
        )
    ).mappings().all()

    return {
        "dish_id": str(dish["id"]),
        "dish_name": dish["name"],
        "ingredients": [
            {
                "ingredient_name": r["ingredient_name"],
                "quantity": float(r["quantity"]),
                "unit": r["unit"],
                "photo_url": r["photo_url"],
                "sort_order": int(r["sort_order"] or 0),
            }
            for r in lines
        ],
        "prep_steps": [
            {
                "step_order": int(r["step_order"]),
                "title": r["title"],
                "body_html": r["body_html"],
                "photo_url": r["photo_url"],
                "duration_min": int(r["duration_min"]) if r["duration_min"] is not None else None,
            }
            for r in steps
        ],
    }
