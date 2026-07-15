"""F30 — per-dish prep, delivery, and max time projection for customers."""

from __future__ import annotations

import copy

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.schemas import DishCreateRequest, DishUpdateRequest, projected_ready_min
from tests.conftest import build_dish_payload


def test_projected_ready_min_defaults_to_prep_plus_delivery():
    assert projected_ready_min(prep=25, delivery=15, max_time=None, for_delivery=True) == 40
    assert projected_ready_min(prep=25, delivery=15, max_time=None, for_delivery=False) == 25
    assert projected_ready_min(prep=25, delivery=None, max_time=None, for_delivery=True) == 25


def test_projected_ready_min_uses_owner_max_time():
    assert projected_ready_min(prep=25, delivery=15, max_time=50, for_delivery=True) == 50
    assert projected_ready_min(prep=25, delivery=15, max_time=45, for_delivery=False) == 45


def test_dish_create_rejects_max_time_below_prep():
    with pytest.raises(ValidationError):
        DishCreateRequest(
            name="Paneer Tikka",
            cuisine_id="00000000-0000-4000-8000-000000000001",
            category_id="00000000-0000-4000-8000-000000000002",
            price=199,
            prep_time_min=30,
            delivery_time_min=20,
            max_time_min=25,
            media={
                "url": "https://example.com/a.jpg",
                "is_hero": True,
                "is_live_capture": True,
            },
        )


def test_dish_create_defaults_max_time_to_prep_plus_delivery():
    body = DishCreateRequest(
        name="Paneer Tikka",
        cuisine_id="00000000-0000-4000-8000-000000000001",
        category_id="00000000-0000-4000-8000-000000000002",
        price=199,
        prep_time_min=30,
        delivery_time_min=20,
        media={
            "url": "https://example.com/a.jpg",
            "is_hero": True,
            "is_live_capture": True,
        },
    )
    assert body.max_time_min == 50


def test_cart_projection_uses_max_across_dishes():
    """Quality-first: parallel cook → customers see max dish max_time, not sum."""
    lines = [
        projected_ready_min(20, 10, 35, for_delivery=True),
        projected_ready_min(40, 15, 60, for_delivery=True),
        projected_ready_min(15, 10, 30, for_delivery=True),
    ]
    assert max(lines) == 60


@pytest.mark.asyncio
async def test_create_dish_persists_timing_fields(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    payload = copy.deepcopy(await build_dish_payload(client, kitchen_id, token))
    payload["prep_time_min"] = 25
    payload["delivery_time_min"] = 20
    payload["max_time_min"] = 55

    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["prep_time_min"] == 25
    assert data["delivery_time_min"] == 20
    assert data["max_time_min"] == 55

    menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert menu.status_code == 200
    dish = menu.json()["dishes"][0]
    assert dish["prep_time_min"] == 25
    assert dish["delivery_time_min"] == 20
    assert dish["max_time_min"] == 55
    assert dish["projected_ready_min"] == 55


@pytest.mark.asyncio
async def test_patch_dish_timing(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    created = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=await build_dish_payload(client, kitchen_id, token),
        headers={"Authorization": f"Bearer {token}"},
    )
    dish_id = created.json()["id"]
    response = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        json={"prep_time_min": 35, "delivery_time_min": 15, "max_time_min": 60},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["prep_time_min"] == 35
    assert data["delivery_time_min"] == 15
    assert data["max_time_min"] == 60


def test_dish_update_rejects_max_below_prep():
    with pytest.raises(ValidationError):
        DishUpdateRequest(prep_time_min=40, max_time_min=30)
