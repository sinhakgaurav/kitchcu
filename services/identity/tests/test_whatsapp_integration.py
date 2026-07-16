"""Owner WhatsApp kitchen integration (F01 connect) — TDD."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_whatsapp_integration_get_default(client: AsyncClient, auth_headers: dict):
    create = await client.post(
        "/api/v1/kitchens",
        json={
            "name": "WA Kitchen",
            "address_line": "Lane 1",
            "city": "Pune",
            "state": "Maharashtra",
            "latitude": 18.5362,
            "longitude": 73.8958,
        },
        headers=auth_headers,
    )
    kitchen_id = create.json()["id"]

    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/whatsapp-integration",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kitchen_id"] == kitchen_id
    assert body["connected"] is False
    assert body["whatsapp_phone_id"] is None


@pytest.mark.asyncio
async def test_whatsapp_integration_upsert_and_unique(client: AsyncClient, auth_headers: dict):
    k1 = (
        await client.post(
            "/api/v1/kitchens",
            json={
                "name": "WA One",
                "address_line": "A",
                "city": "Pune",
                "state": "Maharashtra",
                "latitude": 18.5362,
                "longitude": 73.8958,
            },
            headers=auth_headers,
        )
    ).json()["id"]
    k2 = (
        await client.post(
            "/api/v1/kitchens",
            json={
                "name": "WA Two",
                "address_line": "B",
                "city": "Pune",
                "state": "Maharashtra",
                "latitude": 18.54,
                "longitude": 73.9,
            },
            headers=auth_headers,
        )
    ).json()["id"]

    put = await client.put(
        f"/api/v1/kitchens/{k1}/whatsapp-integration",
        json={
            "whatsapp_phone_id": "PHONE_META_1001",
            "whatsapp_display_phone": "+919876543210",
        },
        headers=auth_headers,
    )
    assert put.status_code == 200
    assert put.json()["connected"] is True
    assert put.json()["whatsapp_phone_id"] == "PHONE_META_1001"
    assert put.json()["whatsapp_display_phone"] == "+919876543210"

    conflict = await client.put(
        f"/api/v1/kitchens/{k2}/whatsapp-integration",
        json={"whatsapp_phone_id": "PHONE_META_1001"},
        headers=auth_headers,
    )
    assert conflict.status_code == 400
    assert "already linked" in conflict.json()["detail"].lower()


@pytest.mark.asyncio
async def test_whatsapp_integration_clear(client: AsyncClient, auth_headers: dict):
    kitchen_id = (
        await client.post(
            "/api/v1/kitchens",
            json={
                "name": "WA Clear",
                "address_line": "C",
                "city": "Pune",
                "state": "Maharashtra",
                "latitude": 18.53,
                "longitude": 73.89,
            },
            headers=auth_headers,
        )
    ).json()["id"]
    await client.put(
        f"/api/v1/kitchens/{kitchen_id}/whatsapp-integration",
        json={"whatsapp_phone_id": "PHONE_CLEAR_1", "whatsapp_display_phone": "+919111111111"},
        headers=auth_headers,
    )
    cleared = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/whatsapp-integration",
        json={"whatsapp_phone_id": None, "whatsapp_display_phone": None, "clear": True},
        headers=auth_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["connected"] is False
