"""Shared contact validators applied to the fee-denial callback (`ckac_common.validators`).

The owner calls this number back to rescue the sale, so it has to be a real,
reachable India mobile in the same E.164 form every other service stores.
"""

import pytest
from httpx import AsyncClient

from app.schemas import DeliveryFeeDenialRequest


async def _quote_id(client: AsyncClient, delivery_ctx) -> str:
    quote = await client.post(
        "/api/v1/delivery/quote",
        json={
            "kitchen_id": str(delivery_ctx["kitchen_id"]),
            "latitude": delivery_ctx["far_lat"],
            "longitude": delivery_ctx["far_lng"],
            "subtotal": 200,
        },
    )
    assert quote.status_code == 200
    return quote.json()["quote_id"]


@pytest.mark.parametrize(
    "raw",
    ["+919876500001", "919876500001", "9876500001", "0091 9876500001", "09876500001"],
)
def test_denial_phone_normalized_to_e164(raw: str):
    body = DeliveryFeeDenialRequest(
        quote_id="3fa85f64-5717-4562-b3fc-2c963f66afa6", customer_phone=raw
    )
    assert body.customer_phone == "+919876500001"


def test_denial_phone_optional():
    body = DeliveryFeeDenialRequest(quote_id="3fa85f64-5717-4562-b3fc-2c963f66afa6")
    assert body.customer_phone is None


@pytest.mark.parametrize(
    "raw",
    [
        "987650000111",  # 12 digits, no 91 dial code
        "98765000011",  # 11 digits
        "+14155552671",  # foreign country code
        "0123456789",  # leading 0 is not a mobile prefix
        "5876543210",  # leading 5 is not a mobile prefix
    ],
)
@pytest.mark.asyncio
async def test_deny_rejects_undeliverable_phone(client: AsyncClient, delivery_ctx, raw: str):
    quote_id = await _quote_id(client, delivery_ctx)
    response = await client.post(
        f"/api/v1/delivery/quote/{quote_id}/deny",
        json={"quote_id": quote_id, "subtotal": 200, "customer_phone": raw},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_deny_accepts_bare_ten_digit_phone(client: AsyncClient, delivery_ctx):
    quote_id = await _quote_id(client, delivery_ctx)
    response = await client.post(
        f"/api/v1/delivery/quote/{quote_id}/deny",
        json={"quote_id": quote_id, "subtotal": 200, "customer_phone": "9876500001"},
    )
    assert response.status_code == 200
    assert response.json()["acknowledged"] is True
