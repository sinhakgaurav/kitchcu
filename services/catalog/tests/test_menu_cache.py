import pytest
from httpx import AsyncClient

from tests.conftest import build_dish_payload


@pytest.mark.asyncio
async def test_menu_uses_redis_cache(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    payload = await build_dish_payload(client, kitchen_id, token)
    await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    from app.main import redis_client

    assert redis_client is not None
    match = f"menu:{kitchen_id}*"
    cached_before = [k async for k in redis_client.scan_iter(match=match)]
    assert cached_before == []

    first = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert first.status_code == 200
    cached_after = [k async for k in redis_client.scan_iter(match=match)]
    assert cached_after

    second = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert second.status_code == 200
    assert second.json() == first.json()


@pytest.mark.asyncio
async def test_dish_update_invalidates_menu_cache(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    payload = await build_dish_payload(client, kitchen_id, token)
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers=headers,
    )
    dish_id = create.json()["id"]

    await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")

    from app.main import redis_client

    match = f"menu:{kitchen_id}*"
    assert [k async for k in redis_client.scan_iter(match=match)]

    patch = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert patch.status_code == 200
    assert [k async for k in redis_client.scan_iter(match=match)] == []

    menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert menu.status_code == 200
    assert menu.json()["dishes"] == []
