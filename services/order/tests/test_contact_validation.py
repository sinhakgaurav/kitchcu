"""Shared contact validators applied to order intake (`ckac_common.validators`).

Manual orders, WhatsApp/pasted-message drafts, and customer checkout must all
reject the same bad phone that owner registration rejects, and store the same
E.164 form regardless of how the caller typed it.
"""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import JWT_SECRET, SYNC_DB_URL

PARSE_PAYLOAD = {"message_text": "2 Paneer Tikka", "source": "manual_message"}


def _make_customer_token(customer_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode(
        {"sub": str(customer_id), "type": "customer", "exp": expire},
        JWT_SECRET,
        algorithm="HS256",
    )


def _seed_customer(*, phone: str = "+919988776655", name: str = "Test Customer") -> uuid.UUID:
    customer_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.customers (id, name, phone, status)
            VALUES (%s::uuid, %s, %s, 'active')
            """,
            (str(customer_id), name, phone),
        )
    conn.close()
    return customer_id


# ------------------------------------------------------------- manual orders


@pytest.mark.parametrize(
    "raw",
    [
        "+919876543210",
        "919876543210",
        "9876543210",
        "0091 9876543210",
        "09876543210",
    ],
)
@pytest.mark.asyncio
async def test_manual_order_phone_normalized_to_e164(
    client: AsyncClient, order_ctx, manual_order_payload, raw: str
):
    _, kitchen_id, _, _, token = order_ctx
    payload = {**manual_order_payload, "customer_phone": raw}
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["customer_phone"] == "+919876543210"


@pytest.mark.parametrize(
    "raw",
    [
        "987654321011",  # 12 digits, no 91 dial code
        "98765432101",  # 11 digits
        "+14155552671",  # foreign country code
        "0123456789",  # leading 0 is not a mobile prefix
        "5876543210",  # leading 5 is not a mobile prefix
    ],
)
@pytest.mark.asyncio
async def test_manual_order_rejects_undeliverable_phone(
    client: AsyncClient, order_ctx, manual_order_payload, raw: str
):
    _, kitchen_id, _, _, token = order_ctx
    payload = {**manual_order_payload, "customer_phone": raw}
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_manual_order_name_allows_digits_and_trims(
    client: AsyncClient, order_ctx, manual_order_payload
):
    """Customer/master checkout rebuild this body with the profile's `Customer NNNN`
    label, so this field takes display-name rules, not person-name rules."""
    _, kitchen_id, _, _, token = order_ctx
    payload = {**manual_order_payload, "customer_name": "  Customer 0481  "}
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["customer_name"] == "Customer 0481"


@pytest.mark.asyncio
async def test_manual_order_rejects_overlong_customer_name(
    client: AsyncClient, order_ctx, manual_order_payload
):
    _, kitchen_id, _, _, token = order_ctx
    payload = {**manual_order_payload, "customer_name": "x" * 121}
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_manual_order_keeps_blank_contact_optional(
    client: AsyncClient, order_ctx, manual_order_payload
):
    _, kitchen_id, _, _, token = order_ctx
    payload = {**manual_order_payload, "customer_name": "", "customer_phone": ""}
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] is None
    assert data["customer_phone"] is None


# -------------------------------------------------------------------- drafts


@pytest.mark.parametrize("raw", ["9876543210", "0091 9876543210", "+91 98765 43210"])
@pytest.mark.asyncio
async def test_draft_phone_normalized_to_e164(client: AsyncClient, order_ctx, raw: str):
    _, kitchen_id, _, _, token = order_ctx
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/parse-message",
        json={**PARSE_PAYLOAD, "customer_phone": raw},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["customer_phone"] == "+919876543210"


@pytest.mark.parametrize("raw", ["98765432101", "0123456789"])
@pytest.mark.asyncio
async def test_draft_rejects_undeliverable_phone(client: AsyncClient, order_ctx, raw: str):
    _, kitchen_id, _, _, token = order_ctx
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/parse-message",
        json={**PARSE_PAYLOAD, "customer_phone": raw},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------- customer checkout


@pytest.mark.parametrize("raw", ["9876500011", "00919876500011", "+91-98765-00011"])
@pytest.mark.asyncio
async def test_customer_order_phone_override_normalized(client: AsyncClient, order_ctx, raw: str):
    _, kitchen_id, dish_id, _, _ = order_ctx
    token = _make_customer_token(_seed_customer())
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json={
            "items": [{"dish_id": str(dish_id), "quantity": 1}],
            "delivery_type": "pickup",
            "payment_method": "cod",
            "delivery_fee": 0,
            "customer_phone": raw,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["customer_phone"] == "+919876500011"


@pytest.mark.parametrize("raw", ["987654321011", "0123456789"])
@pytest.mark.asyncio
async def test_customer_order_rejects_undeliverable_phone(
    client: AsyncClient, order_ctx, raw: str
):
    _, kitchen_id, dish_id, _, _ = order_ctx
    token = _make_customer_token(_seed_customer())
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json={
            "items": [{"dish_id": str(dish_id), "quantity": 1}],
            "delivery_type": "pickup",
            "payment_method": "cod",
            "delivery_fee": 0,
            "customer_phone": raw,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_customer_order_keeps_machine_assigned_profile_name(
    client: AsyncClient, order_ctx
):
    """Identity labels OTP signups `Customer 0481`; checkout must not reject it."""
    _, kitchen_id, dish_id, _, _ = order_ctx
    token = _make_customer_token(
        _seed_customer(phone="+919876500022", name="Customer 0022")
    )
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/customer",
        json={
            "items": [{"dish_id": str(dish_id), "quantity": 1}],
            "delivery_type": "pickup",
            "payment_method": "cod",
            "delivery_fee": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["customer_name"] == "Customer 0022"
