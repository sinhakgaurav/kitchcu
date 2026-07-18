"""Dish merchandising flags + menu filter/sort (TDD)."""

import copy

import pytest
from httpx import AsyncClient

from app.schemas import (
    DishResponse,
    MenuHighlightSections,
    apply_menu_list_options,
    build_highlight_sections,
)
from tests.conftest import build_dish_payload


def _dish(**kwargs) -> DishResponse:
    base = dict(
        id="00000000-0000-0000-0000-000000000001",
        kitchen_id="00000000-0000-0000-0000-000000000010",
        cuisine_id=None,
        category_id=None,
        cuisine_name=None,
        cuisine_slug=None,
        category_name="Veg",
        category_slug="veg",
        name="Aloo",
        price=100.0,
        prep_time_min=20,
        delivery_time_min=10,
        max_time_min=30,
        projected_ready_min=30,
        description=None,
        ingredients_description=None,
        quality_measures=None,
        is_active=True,
        is_featured=False,
        is_chefs_special=False,
        is_unique_recipe=False,
        media=[],
    )
    base.update(kwargs)
    return DishResponse.model_validate(base)


def test_apply_menu_filter_highlight_and_sort():
    dishes = [
        _dish(id="00000000-0000-0000-0000-000000000001", name="Zest", price=300, is_featured=True),
        _dish(id="00000000-0000-0000-0000-000000000002", name="Alpha", price=100, is_chefs_special=True),
        _dish(id="00000000-0000-0000-0000-000000000003", name="Mid", price=200, is_unique_recipe=True),
    ]
    featured = apply_menu_list_options(dishes, highlight="featured", sort="price_asc")
    assert len(featured) == 1
    assert featured[0].name == "Zest"

    by_price = apply_menu_list_options(dishes, sort="price_asc")
    assert [d.name for d in by_price] == ["Alpha", "Mid", "Zest"]

    by_name = apply_menu_list_options(dishes, sort="name_desc")
    assert [d.name for d in by_name] == ["Zest", "Mid", "Alpha"]


def test_build_highlight_sections():
    dishes = [
        _dish(id="00000000-0000-0000-0000-000000000001", name="F", is_featured=True),
        _dish(id="00000000-0000-0000-0000-000000000002", name="C", is_chefs_special=True),
        _dish(id="00000000-0000-0000-0000-000000000003", name="U", is_unique_recipe=True),
        _dish(id="00000000-0000-0000-0000-000000000004", name="Plain"),
    ]
    sections = build_highlight_sections(dishes)
    assert isinstance(sections, MenuHighlightSections)
    assert [d.name for d in sections.featured] == ["F"]
    assert [d.name for d in sections.chefs_special] == ["C"]
    assert [d.name for d in sections.unique_recipe] == ["U"]


@pytest.mark.asyncio
async def test_create_and_patch_highlight_flags(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    payload = copy.deepcopy(await build_dish_payload(client, kitchen_id, token))
    payload["name"] = "Chef Special Curry"
    payload["is_featured"] = True
    payload["is_chefs_special"] = True
    payload["is_unique_recipe"] = False

    created = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201, created.text
    data = created.json()
    assert data["is_featured"] is True
    assert data["is_chefs_special"] is True
    assert data["is_unique_recipe"] is False
    dish_id = data["id"]

    patched = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        json={"is_unique_recipe": True, "is_featured": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["is_featured"] is False
    assert body["is_chefs_special"] is True
    assert body["is_unique_recipe"] is True


@pytest.mark.asyncio
async def test_menu_filter_sort_and_highlight_sections(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    base = await build_dish_payload(client, kitchen_id, token)

    async def add(name: str, price: float, **flags):
        p = copy.deepcopy(base)
        p["name"] = name
        p["price"] = price
        p.update(flags)
        r = await client.post(
            f"/api/v1/kitchens/{kitchen_id}/dishes",
            json=p,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201, r.text

    await add("Featured Bowl", 150, is_featured=True)
    await add("Chef Plate", 250, is_chefs_special=True)
    await add("Unique Stew", 180, is_unique_recipe=True)
    await add("Plain Rice", 80)

    menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert menu.status_code == 200
    full = menu.json()
    assert len(full["dishes"]) == 4
    assert len(full["highlight_sections"]["featured"]) == 1
    assert full["highlight_sections"]["featured"][0]["name"] == "Featured Bowl"
    assert len(full["highlight_sections"]["chefs_special"]) == 1
    assert len(full["highlight_sections"]["unique_recipe"]) == 1

    filtered = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/menu",
        params={"highlight": "featured", "sort": "price_asc"},
    )
    assert filtered.status_code == 200
    data = filtered.json()
    assert len(data["dishes"]) == 1
    assert data["dishes"][0]["name"] == "Featured Bowl"

    sorted_menu = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/menu",
        params={"sort": "price_desc"},
    )
    assert sorted_menu.status_code == 200
    names = [d["name"] for d in sorted_menu.json()["dishes"]]
    assert names[0] == "Chef Plate"
    assert names[-1] == "Plain Rice"
