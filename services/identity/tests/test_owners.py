from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from ckac_common.config import get_settings


@pytest.mark.asyncio
async def test_register_owner_success(client: AsyncClient, unique_phone: str):
    response = await client.post(
        "/api/v1/owners/register",
        json={"phone": unique_phone, "name": "Raj Kitchen", "email": "raj@example.com"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["phone"] == f"+91{unique_phone}"
    assert data["name"] == "Raj Kitchen"
    assert data["email"] == "raj@example.com"
    assert data["subscription_tier"] == "starter"
    assert data["subscription_status"] == "trial"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_owner_duplicate_phone(client: AsyncClient, unique_phone: str):
    payload = {"phone": unique_phone, "name": "Owner One"}
    assert (await client.post("/api/v1/owners/register", json=payload)).status_code == 201
    response = await client.post("/api/v1/owners/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_owner_invalid_phone(client: AsyncClient):
    response = await client.post(
        "/api/v1/owners/register",
        json={"phone": "123", "name": "Bad Phone"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_owner_me_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/owners/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_me_rejects_customer_typed_token(
    client: AsyncClient, registered_owner: dict
):
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": registered_owner["id"],
            "type": "customer",
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    response = await client.get(
        "/api/v1/owners/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert "type" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_owner_me_returns_profile(client: AsyncClient, registered_owner: dict, auth_headers: dict):
    response = await client.get("/api/v1/owners/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == registered_owner["id"]
    assert data["phone"] == registered_owner["phone"]
    assert data["name"] == registered_owner["name"]
