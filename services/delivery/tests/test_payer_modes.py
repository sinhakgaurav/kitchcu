"""In-range owner pays / out-of-range customer pays + platform courier modes."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quote_in_range_modes_owner_pays(client: AsyncClient, delivery_ctx):
    response = await client.post(
        "/api/v1/delivery/quote",
        json={
            "kitchen_id": str(delivery_ctx["kitchen_id"]),
            "latitude": delivery_ctx["near_lat"],
            "longitude": delivery_ctx["near_lng"],
            "subtotal": 200,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["in_range"] is True
    assert data["status"] == "ok"
    assert data["fee"] == 0.0
    assert data["platform_fee"] > 0
    modes = {m["mode"]: m for m in data["modes"]}
    assert modes["self"]["payer"] == "owner"
    assert modes["self"]["customer_fee"] == 0.0
    assert modes["platform"]["payer"] == "owner"
    assert modes["platform"]["customer_fee"] == 0.0
    assert modes["platform"]["owner_fee"] == data["platform_fee"]


@pytest.mark.asyncio
async def test_quote_out_of_range_extended_customer_pays(client: AsyncClient, delivery_ctx):
    response = await client.post(
        "/api/v1/delivery/quote",
        json={
            "kitchen_id": str(delivery_ctx["kitchen_id"]),
            "latitude": delivery_ctx["far_lat"],
            "longitude": delivery_ctx["far_lng"],
            "subtotal": 200,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["in_range"] is False
    assert data["status"] == "extended"
    assert data["fee"] >= 0
    modes = {m["mode"]: m for m in data["modes"]}
    # No min-order subsidy configured on seed kitchen → customer bears full.
    assert modes["self"]["payer"] == "customer"
    assert modes["platform"]["payer"] == "customer"
    assert modes["platform"]["customer_fee"] == data["platform_fee"]
    assert modes["self"]["customer_fee"] == data["kitchen_self_fee"]


@pytest.mark.asyncio
async def test_quote_out_of_range_min_order_kitchen_subsidy(client: AsyncClient, delivery_ctx):
    import psycopg2
    from tests.conftest import SYNC_DB_URL

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ckac_identity.kitchens
            SET min_order_for_free_delivery = 300,
                delivery_subsidy_percent = 50
            WHERE id = %s::uuid
            """,
            (str(delivery_ctx["kitchen_id"]),),
        )
    conn.close()

    response = await client.post(
        "/api/v1/delivery/quote",
        json={
            "kitchen_id": str(delivery_ctx["kitchen_id"]),
            "latitude": delivery_ctx["far_lat"],
            "longitude": delivery_ctx["far_lng"],
            "subtotal": 400,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["in_range"] is False
    modes = {m["mode"]: m for m in data["modes"]}
    assert modes["platform"]["payer"] == "shared"
    # platform_fee on the quote is the gross courier quote before cost-share.
    assert modes["platform"]["owner_fee"] == round(float(data["platform_fee"]) * 0.5, 2)
    assert modes["platform"]["customer_fee"] == round(
        float(data["platform_fee"]) - modes["platform"]["owner_fee"], 2
    )
    assert modes["self"]["payer"] == "shared"
