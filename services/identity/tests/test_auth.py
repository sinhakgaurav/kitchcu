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
    assert data["message"] == "OTP sent"
    assert "dev_hint" in data


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
async def test_verify_otp_unregistered_phone(client: AsyncClient):
    phone = "+919999999999"
    await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Owner not registered"
