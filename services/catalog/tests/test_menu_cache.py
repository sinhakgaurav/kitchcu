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
    from ckac_common.cache import menu_cache_key

    assert redis_client is not None
    cached_before = await redis_client.get(menu_cache_key(kitchen_id))
    assert cached_before is None

    first = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert first.status_code == 200
    cached_after = await redis_client.get(menu_cache_key(kitchen_id))
    assert cached_after is not None

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
    from ckac_common.cache import menu_cache_key

    assert await redis_client.get(menu_cache_key(kitchen_id)) is not None

    patch = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert patch.status_code == 200
    assert await redis_client.get(menu_cache_key(kitchen_id)) is None

    menu = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert menu.status_code == 200
    assert menu.json()["dishes"] == []
