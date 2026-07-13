import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_enable_settings_and_go_live(client: AsyncClient, stream_ctx):
    kid = stream_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {stream_ctx['owner_token']}"}

    settings = await client.get(f"/api/v1/kitchens/{kid}/stream/settings", headers=owner_headers)
    assert settings.status_code == 200
    assert settings.json()["live_sharing_enabled"] is False

    patched = await client.patch(
        f"/api/v1/kitchens/{kid}/stream/settings",
        json={"live_sharing_enabled": True, "q_and_a_enabled": True},
        headers=owner_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["live_sharing_enabled"] is True

    blocked = await client.post(
        f"/api/v1/kitchens/{kid}/stream/go-live",
        json={"title": "Paneer prep live"},
        headers=owner_headers,
    )
    assert blocked.status_code == 200
    body = blocked.json()
    assert body["status"] == "live"
    assert body["title"] == "Paneer prep live"
    assert body["room_name"].startswith("kitchcu-")


@pytest.mark.asyncio
async def test_go_live_requires_opt_in(client: AsyncClient, stream_ctx):
    kid = stream_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {stream_ctx['owner_token']}"}

    resp = await client.post(
        f"/api/v1/kitchens/{kid}/stream/go-live",
        json={"title": "Too early"},
        headers=owner_headers,
    )
    assert resp.status_code == 400
    assert "live sharing" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_end_live_and_list_public(client: AsyncClient, stream_ctx):
    kid = stream_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {stream_ctx['owner_token']}"}

    await client.patch(
        f"/api/v1/kitchens/{kid}/stream/settings",
        json={"live_sharing_enabled": True},
        headers=owner_headers,
    )
    live = await client.post(
        f"/api/v1/kitchens/{kid}/stream/go-live",
        json={"title": "Dinner rush"},
        headers=owner_headers,
    )
    session_id = live.json()["id"]

    listed = await client.get("/api/v1/stream/live-kitchens")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["kitchens"][0]["kitchen_id"] == str(kid)

    ended = await client.post(f"/api/v1/kitchens/{kid}/stream/end", headers=owner_headers)
    assert ended.status_code == 200
    assert ended.json()["status"] == "ended"

    empty = await client.get("/api/v1/stream/live-kitchens")
    assert empty.json()["total"] == 0

    viewer = await client.post(
        f"/api/v1/stream/sessions/{session_id}/viewer-token",
        headers={"Authorization": f"Bearer {stream_ctx['customer_token']}"},
    )
    assert viewer.status_code == 404


@pytest.mark.asyncio
async def test_viewer_token_increments_count(client: AsyncClient, stream_ctx):
    kid = stream_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {stream_ctx['owner_token']}"}
    customer_headers = {"Authorization": f"Bearer {stream_ctx['customer_token']}"}

    await client.patch(
        f"/api/v1/kitchens/{kid}/stream/settings",
        json={"live_sharing_enabled": True},
        headers=owner_headers,
    )
    live = await client.post(
        f"/api/v1/kitchens/{kid}/stream/go-live",
        json={"title": "Lunch prep"},
        headers=owner_headers,
    )
    session_id = live.json()["id"]

    token_resp = await client.post(
        f"/api/v1/stream/sessions/{session_id}/viewer-token",
        headers=customer_headers,
    )
    assert token_resp.status_code == 200
    body = token_resp.json()
    assert body["room_name"] == live.json()["room_name"]
    assert body["kitchen_name"] == "Stream Kitchen"

    session = await client.get(f"/api/v1/kitchens/{kid}/stream/session", headers=owner_headers)
    assert session.json()["viewer_count"] == 1
