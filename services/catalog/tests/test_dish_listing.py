"""Owner dish listing — the only view that includes dishes hidden from customers.

The public menu is active-only, so without this endpoint a dish created inactive
(bulk Excel import with no live-capture photo yet) is invisible to the owner and
can never be published. These tests pin that recovery path.
"""

import copy
import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import build_dish_payload


async def _create_dish(
    client: AsyncClient,
    kitchen_id: uuid.UUID,
    token: str,
    *,
    name: str,
    active: bool,
) -> str:
    payload = copy.deepcopy(await build_dish_payload(client, kitchen_id, token))
    payload["name"] = name
    if not active:
        payload["is_active"] = False
        payload.pop("media", None)
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_list_dishes_requires_auth(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, _ = kitchen_ctx
    response = await client.get(f"/api/v1/kitchens/{kitchen_id}/dishes")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_dishes_includes_inactive(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    await _create_dish(client, kitchen_id, token, name="Paneer Tikka", active=True)
    await _create_dish(client, kitchen_id, token, name="Masala Chai", active=False)

    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    by_name = {d["name"]: d for d in body["dishes"]}
    assert by_name["Paneer Tikka"]["is_active"] is True
    assert by_name["Masala Chai"]["is_active"] is False
    assert body["total"] == 2

    menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert [d["name"] for d in menu.json()["dishes"]] == ["Paneer Tikka"]


@pytest.mark.asyncio
async def test_list_dishes_can_filter_to_hidden_only(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    await _create_dish(client, kitchen_id, token, name="Paneer Tikka", active=True)
    await _create_dish(client, kitchen_id, token, name="Masala Chai", active=False)

    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/dishes?is_active=false",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert [d["name"] for d in response.json()["dishes"]] == ["Masala Chai"]


@pytest.mark.asyncio
async def test_list_dishes_carries_media_so_owner_can_see_missing_hero(
    client: AsyncClient, kitchen_ctx
):
    _, kitchen_id, token = kitchen_ctx
    await _create_dish(client, kitchen_id, token, name="Masala Chai", active=False)

    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        headers={"Authorization": f"Bearer {token}"},
    )
    dish = response.json()["dishes"][0]
    assert dish["media"] == []


@pytest.mark.asyncio
async def test_list_dishes_is_tenant_scoped(client: AsyncClient, kitchen_ctx, kitchen_ctx_other):
    """Another owner's token must never see this kitchen's hidden dishes."""
    _, kitchen_id, token = kitchen_ctx
    _, _, other_token = kitchen_ctx_other
    await _create_dish(client, kitchen_id, token, name="Masala Chai", active=False)

    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_hidden_dish_can_be_published_once_a_live_hero_is_added(
    client: AsyncClient, kitchen_ctx
):
    """The whole point of listing hidden dishes: the owner can recover them."""
    _, kitchen_id, token = kitchen_ctx
    dish_id = await _create_dish(client, kitchen_id, token, name="Masala Chai", active=False)

    patched = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        json={
            "is_active": True,
            "media": {
                "url": "https://minio/chai.jpg",
                "is_hero": True,
                "is_live_capture": True,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patched.status_code == 200
    assert patched.json()["is_active"] is True

    menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert "Masala Chai" in [d["name"] for d in menu.json()["dishes"]]
