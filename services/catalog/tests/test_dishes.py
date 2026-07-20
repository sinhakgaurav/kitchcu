import copy

import pytest
from httpx import AsyncClient

from tests.conftest import DISH_PAYLOAD_BASE, build_dish_payload


@pytest.mark.asyncio
async def test_create_dish_requires_auth(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    payload = await build_dish_payload(client, kitchen_id, token)
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_dish_success(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    payload = await build_dish_payload(client, kitchen_id, token)
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Paneer Tikka"
    assert data["price"] == 199.0
    assert data["kitchen_id"] == str(kitchen_id)
    assert len(data["media"]) == 1
    assert data["media"][0]["is_live_capture"] is True


@pytest.mark.asyncio
async def test_create_dish_rejects_non_live_hero(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    payload = copy.deepcopy(await build_dish_payload(client, kitchen_id, token))
    payload["media"]["is_live_capture"] = False
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "live capture" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_dish_price_name_active_and_hero(client: AsyncClient, kitchen_ctx):
    """Owner day-to-day ops: rename, reprice, hide, replace live hero."""
    _, kitchen_id, token = kitchen_ctx
    payload = await build_dish_payload(client, kitchen_id, token)
    created = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201
    dish_id = created.json()["id"]

    patched = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        json={
            "name": "Paneer Tikka Masala",
            "price": 249.0,
            "is_active": False,
            "media": {
                "url": "https://cdn.example/hero-retake.jpg",
                "is_hero": True,
                "is_live_capture": True,
                "captured_at": "2026-07-20T06:00:00+00:00",
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patched.status_code == 200
    data = patched.json()
    assert data["name"] == "Paneer Tikka Masala"
    assert data["price"] == 249.0
    assert data["is_active"] is False
    assert any(m["url"].endswith("hero-retake.jpg") and m["is_hero"] for m in data["media"])


@pytest.mark.asyncio
async def test_update_dish_rejects_non_live_hero_when_active(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    payload = await build_dish_payload(client, kitchen_id, token)
    created = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    dish_id = created.json()["id"]
    bad = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        json={
            "media": {
                "url": "https://cdn.example/stock.jpg",
                "is_hero": True,
                "is_live_capture": False,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad.status_code == 400
    assert "live capture" in bad.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_menu_returns_active_dishes(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    payload = await build_dish_payload(client, kitchen_id, token)
    await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    response = await client.get(f"/api/v1/kitchens/{kitchen_id}/menu")
    assert response.status_code == 200
    data = response.json()
    assert data["kitchen_id"] == str(kitchen_id)
    assert len(data["dishes"]) == 1
    assert data["dishes"][0]["name"] == "Paneer Tikka"
    assert len(data["grouped"]) >= 1


@pytest.mark.asyncio
async def test_get_menu_unknown_kitchen_returns_404(client: AsyncClient):
    import uuid

    missing = uuid.UUID("00000000-0000-0000-0000-000000000099")
    response = await client.get(f"/api/v1/kitchens/{missing}/menu")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_dish_forbidden_for_other_owner(client: AsyncClient, kitchen_ctx):
    import uuid

    import psycopg2

    from tests.conftest import SYNC_DB_URL, _make_token

    _, kitchen_id, token = kitchen_ctx
    owner2 = uuid.uuid4()
    token2 = _make_token(owner2)

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ckac_identity.owners (id, phone, name) VALUES (%s, %s, %s)",
            (str(owner2), "+919888777666", "Other Owner"),
        )
    conn.close()

    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=await build_dish_payload(client, kitchen_id, token),
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert response.status_code == 403
