"""Customer refund payout profile — UPI / bank / QR."""

import io

import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient, phone: str = "+919111222333") -> str:
    await client.post("/api/v1/auth/customer/whatsapp/request", json={"phone": phone})
    ok = await client.post(
        "/api/v1/auth/customer/whatsapp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert ok.status_code == 200
    return ok.json()["access_token"]


@pytest.mark.asyncio
async def test_customer_payout_update_and_mask(client: AsyncClient):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    updated = await client.patch(
        "/api/v1/customers/me/payout",
        json={
            "upi_vpa": "priya@oksbi",
            "bank_account_number": "12345678901234",
            "bank_ifsc": "hdfc0001234",
            "bank_account_name": "Priya Customer",
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["upi_vpa"] == "priya@oksbi"
    assert body["bank_ifsc"] == "HDFC0001234"
    assert body["bank_account_name"] == "Priya Customer"
    assert body["bank_account_number_masked"].endswith("1234")
    assert "12345678901234" not in body.get("bank_account_number_masked", "")

    me = await client.get("/api/v1/customers/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["upi_vpa"] == "priya@oksbi"


@pytest.mark.asyncio
async def test_customer_payout_qr_upload(client: AsyncClient):
    token = await _login(client, "+919444555666")
    headers = {"Authorization": f"Bearer {token}"}
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00"
        b"\x00\x00IEND\xaeB`\x82"
    )
    res = await client.post(
        "/api/v1/customers/me/payout/qr",
        headers=headers,
        files={"file": ("qr.png", io.BytesIO(png), "image/png")},
    )
    assert res.status_code == 200, res.text
    assert res.json()["upi_qr_url"]
