"""HTTP client for catalog service — trial dish create/activate."""

from __future__ import annotations

import uuid

import httpx

from ckac_common.config import get_settings


async def _catalog_request(
    method: str,
    path: str,
    *,
    owner_token: str,
    json_body: dict | None = None,
) -> dict:
    settings = get_settings()
    url = f"{settings.catalog_service_url.rstrip('/')}{path}"
    headers = {"Authorization": f"Bearer {owner_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, headers=headers, json=json_body)
    if response.status_code >= 400:
        detail = response.json().get("detail", "Catalog request failed")
        raise ValueError(detail if isinstance(detail, str) else str(detail))
    return response.json()


async def _resolve_menu_defaults(kitchen_id: uuid.UUID, owner_token: str) -> tuple[uuid.UUID, uuid.UUID]:
    menu = await _catalog_request("GET", f"/api/v1/kitchens/{kitchen_id}/menu", owner_token=owner_token)
    grouped = menu.get("grouped") or []
    if not grouped:
        raise ValueError("Set up your kitchen menu (cuisine + category) before learning a dish")
    first_cuisine = grouped[0]
    diets = first_cuisine.get("diets") or []
    if not diets:
        raise ValueError("Add a diet category to your menu before learning a dish")
    first_diet = diets[0]
    cuisine_id = uuid.UUID(first_cuisine["cuisine"]["id"])
    category_id = uuid.UUID(first_diet["diet"]["id"])
    return cuisine_id, category_id


async def create_trial_dish(
    *,
    kitchen_id: uuid.UUID,
    owner_token: str,
    name: str,
    price: float,
    description: str | None,
    ingredients_description: str | None,
    image_url: str,
    cuisine_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    prep_time_min: int,
) -> uuid.UUID:
    if not cuisine_id or not category_id:
        cuisine_id, category_id = await _resolve_menu_defaults(kitchen_id, owner_token)

    body = {
        "name": name,
        "price": price,
        "prep_time_min": prep_time_min,
        "cuisine_id": str(cuisine_id),
        "category_id": str(category_id),
        "description": description,
        "ingredients_description": ingredients_description,
        "is_active": False,
        "media": {
            "url": image_url,
            "is_hero": True,
            "is_live_capture": False,
        },
    }
    dish = await _catalog_request(
        "POST",
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        owner_token=owner_token,
        json_body=body,
    )
    return uuid.UUID(dish["id"])


async def activate_dish(*, kitchen_id: uuid.UUID, dish_id: uuid.UUID, owner_token: str) -> None:
    await _catalog_request(
        "PATCH",
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        owner_token=owner_token,
        json_body={"is_active": True},
    )
