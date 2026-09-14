import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_otp_returns_accepted(client: AsyncClient, registered_owner: dict):
    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"phone": registered_owner["phone"]},
    )
    assert response.status_code == 202
    data = response.json()
    assert "dev_hint" in data
    # Demo mode delivers nothing — saying "sent" would strand the caller waiting for an SMS.
    assert data["message"] == "Demo mode — no message sent"
    assert data["demo_otp"] == "123456"
    assert data["delivered"] is False


@pytest.mark.asyncio
async def test_verify_otp_success(client: AsyncClient, registered_owner: dict):
    phone = registered_owner["phone"]
    await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_verify_otp_invalid_code(client: AsyncClient, registered_owner: dict):
    phone = registered_owner["phone"]
    await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": "000000"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid OTP"


@pytest.mark.asyncio
async def test_request_otp_rejects_invalid_phone(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"phone": "not-a-phone"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("phone", ["987654321011", "98765", "98765 4321!", "+14155550123"])
async def test_request_otp_rejects_undeliverable_phone(client: AsyncClient, phone: str):
    """QA tracker BUG_01 — an over-long or foreign number must never mint an OTP."""
    response = await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert response.status_code == 422, phone


@pytest.mark.asyncio
async def test_otp_request_openapi_documents_live_body(client: AsyncClient):
    spec = (await client.get("/openapi.json")).json()
    content = spec["paths"]["/api/v1/auth/otp/request"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]
    ref = content["schema"]["$ref"].rsplit("/", 1)[-1]
    props = spec["components"]["schemas"][ref]["properties"]
    assert "demo_otp" in props
    assert "delivered" in props
    assert "429" in spec["paths"]["/api/v1/auth/otp/request"]["post"]["responses"]


@pytest.mark.asyncio
async def test_oauth_token_openapi_documents_access_token(client: AsyncClient):
    spec = (await client.get("/openapi.json")).json()
    content = spec["paths"]["/api/v1/auth/token"]["post"]["responses"]["200"]["content"][
        "application/json"
    ]
    ref = content["schema"]["$ref"].rsplit("/", 1)[-1]
    assert "access_token" in spec["components"]["schemas"][ref]["properties"]


@pytest.mark.asyncio
async def test_oauth_password_token_issues_owner_jwt(client: AsyncClient, registered_owner: dict):
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": registered_owner["phone"], "password": "123456", "grant_type": "password"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    me = await client.get(
        "/api/v1/owners/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["id"] == registered_owner["id"]


@pytest.mark.asyncio
async def test_verify_otp_unregistered_phone(client: AsyncClient):
    phone = "+919999999999"
    await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Owner not registered"
