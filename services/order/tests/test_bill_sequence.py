"""Bill/order-code allocation must survive gaps in the day's orders.

The sequence used to be `COUNT(*) + 1`, which silently reissues a code the moment
any of today's orders disappears — an admin cleanup, a PII erasure, or a dev reset
that drops orders. The reissued code then trips the unique index and the customer
gets a 500 at checkout.
"""

import uuid

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL


async def _place(client: AsyncClient, kitchen_id, token: str, payload: dict) -> dict:
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _delete_order(order_id: str) -> None:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DELETE FROM ckac_orders.orders WHERE id = %s::uuid", (order_id,))
    conn.close()


@pytest.mark.asyncio
async def test_bill_ids_increment_within_the_day(
    client: AsyncClient, order_ctx, manual_order_payload
):
    _, kitchen_id, _, kitchen_code, token = order_ctx
    first = await _place(client, kitchen_id, token, manual_order_payload)
    second = await _place(client, kitchen_id, token, manual_order_payload)

    assert first["bill_id"] == first["order_code"]
    assert first["bill_id"].startswith(f"{kitchen_code}-BILL-")
    assert first["bill_id"].endswith("-0001")
    assert second["bill_id"].endswith("-0002")
    assert first["order_code"] != second["order_code"]


@pytest.mark.asyncio
async def test_order_code_not_reissued_after_an_order_is_deleted(
    client: AsyncClient, order_ctx, manual_order_payload
):
    """A gap in the day's orders must not push the next order onto a used code."""
    _, kitchen_id, _, _, token = order_ctx
    first = await _place(client, kitchen_id, token, manual_order_payload)
    second = await _place(client, kitchen_id, token, manual_order_payload)
    _delete_order(first["id"])

    third = await _place(client, kitchen_id, token, manual_order_payload)
    assert third["order_code"] != second["order_code"]
    assert third["bill_id"].endswith("-0003")


@pytest.mark.asyncio
async def test_order_code_survives_a_recycled_kitchen_code(
    client: AsyncClient, order_ctx, manual_order_payload
):
    """Kitchen codes are per-city sequential and get recycled after a reset.

    Orders live in their own schema with no FK to kitchens, so the old kitchen's
    orders outlive it. The replacement kitchen has no orders of its own, yet the
    codes it would issue are already taken platform-wide.
    """
    owner_id, kitchen_id, _, code, token = order_ctx
    stale = await _place(client, kitchen_id, token, manual_order_payload)

    new_kitchen_id = uuid.uuid4()
    new_category_id = uuid.uuid4()
    new_dish_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        # Retire the kitchen, keeping its orders — then hand the code to a new one.
        cur.execute("DELETE FROM ckac_identity.kitchens WHERE id = %s::uuid", (str(kitchen_id),))
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens (id, owner_id, code, name, location, status)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Rebuilt Kitchen',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active'
            )
            """,
            (str(new_kitchen_id), str(owner_id), code),
        )
        cur.execute(
            """
            INSERT INTO ckac_catalog.categories (id, kitchen_id, name, slug, sort_order)
            VALUES (%s::uuid, %s::uuid, 'Veg', 'veg', 0)
            """,
            (str(new_category_id), str(new_kitchen_id)),
        )
        cur.execute(
            """
            INSERT INTO ckac_catalog.dishes
            (id, kitchen_id, category_id, name, price, prep_time_min,
             delivery_time_min, max_time_min, is_active)
            VALUES (%s::uuid, %s::uuid, %s::uuid, 'Paneer Tikka', 199.00, 25, 20, 45, true)
            """,
            (str(new_dish_id), str(new_kitchen_id), str(new_category_id)),
        )
    conn.close()

    payload = {**manual_order_payload, "items": [{"dish_id": str(new_dish_id), "quantity": 1}]}
    fresh = await _place(client, new_kitchen_id, token, payload)
    assert fresh["order_code"] != stale["order_code"]
