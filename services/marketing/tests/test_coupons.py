from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_validate_percent_coupon(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}
    customer_headers = {"Authorization": f"Bearer {marketing_ctx['customer_token']}"}

    create = await client.post(
        f"/api/v1/kitchens/{kid}/coupons",
        json={
            "code": "SAVE10",
            "discount_type": "percent",
            "discount_value": 10,
            "min_order_amount": 200,
        },
        headers=owner_headers,
    )
    assert create.status_code == 201
    assert create.json()["code"] == "SAVE10"

    validate = await client.post(
        "/api/v1/marketing/coupons/validate",
        json={"kitchen_id": str(kid), "code": "save10", "subtotal": 400},
        headers=customer_headers,
    )
    assert validate.status_code == 200
    body = validate.json()
    assert body["valid"] is True
    assert body["discount_amount"] == 40.0


@pytest.mark.asyncio
async def test_validate_rejects_expired_coupon(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}
    customer_headers = {"Authorization": f"Bearer {marketing_ctx['customer_token']}"}

    past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    await client.post(
        f"/api/v1/kitchens/{kid}/coupons",
        json={
            "code": "OLD",
            "discount_type": "fixed",
            "discount_value": 50,
            "valid_until": past,
        },
        headers=owner_headers,
    )

    validate = await client.post(
        "/api/v1/marketing/coupons/validate",
        json={"kitchen_id": str(kid), "code": "OLD", "subtotal": 500},
        headers=customer_headers,
    )
    assert validate.json()["valid"] is False


@pytest.mark.asyncio
async def test_deactivate_coupon(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    created = await client.post(
        f"/api/v1/kitchens/{kid}/coupons",
        json={"code": "OFF", "discount_type": "fixed", "discount_value": 25},
        headers=headers,
    )
    coupon_id = created.json()["id"]

    patched = await client.patch(
        f"/api/v1/kitchens/{kid}/coupons/{coupon_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False
