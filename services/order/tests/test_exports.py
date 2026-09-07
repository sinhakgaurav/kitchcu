"""F05 CSV export + F01 parse-stats (owner JWT)."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.exports import compute_parse_stats, render_orders_csv
from tests.test_analytics import _insert_order


def test_render_orders_csv_headers_and_utf8_bom():
    body = render_orders_csv(
        [
            {
                "order_code": "CKTST-BILL-1",
                "created_at": "2026-09-07T10:00:00+00:00",
                "status": "delivered",
                "source": "manual",
                "customer_name": "Asha",
                "customer_phone": "+919876543210",
                "items": "2x Paneer Tikka",
                "subtotal": "398.00",
                "delivery_fee": "0.00",
                "discount_amount": "0.00",
                "total": "398.00",
                "payment_method": "cod",
                "delivery_type": "pickup",
            }
        ]
    )
    assert body.startswith(b"\xef\xbb\xbf")
    text = body.decode("utf-8-sig")
    header = text.splitlines()[0]
    assert header.startswith("order_code,created_at,status,source")
    assert "CKTST-BILL-1" in text
    assert "2x Paneer Tikka" in text


def test_compute_parse_stats_match_rate():
    stats = compute_parse_stats(
        [
            {
                "parsed_items": [
                    {"matched": True},
                    {"matched": True},
                    {"matched": False},
                ],
                "unmatched_lines": ["mystery"],
            },
            {
                "parsed_items": [{"matched": True}],
                "unmatched_lines": [],
            },
        ],
        days=30,
    )
    assert stats["drafts"] == 2
    assert stats["lines_total"] == 4
    assert stats["lines_matched"] == 3
    assert stats["match_rate"] == 0.75
    assert stats["drafts_with_unmatched"] == 1
    assert stats["days"] == 30


def test_compute_parse_stats_empty_window():
    stats = compute_parse_stats([], days=7)
    assert stats["drafts"] == 0
    assert stats["lines_total"] == 0
    assert stats["match_rate"] is None


@pytest.mark.asyncio
async def test_export_csv_requires_auth(client: AsyncClient, order_ctx):
    _, kitchen_id, _, _, _ = order_ctx
    response = await client.get(f"/api/v1/kitchens/{kitchen_id}/orders/export.csv")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_export_csv_forbidden_for_other_owner(client: AsyncClient, order_ctx):
    import uuid

    from tests.conftest import _make_token

    _, kitchen_id, _, _, _ = order_ctx
    stranger = _make_token(uuid.uuid4())
    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders/export.csv",
        headers={"Authorization": f"Bearer {stranger}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_export_csv_rows_and_filters(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, dish_id, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    assert created.status_code == 201
    order_code = created.json()["order_code"]

    now = datetime.now(UTC)
    _insert_order(
        kitchen_id,
        total=199,
        status="delivered",
        created_at=now - timedelta(days=10),
        dish_id=dish_id,
        dish_name="Old Dish",
        customer_name="Older",
    )

    all_rows = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders/export.csv",
        headers=headers,
    )
    assert all_rows.status_code == 200
    assert all_rows.headers["content-type"].startswith("text/csv")
    body = all_rows.content.decode("utf-8-sig")
    assert "order_code,created_at,status,source" in body
    assert order_code in body
    assert "2x Paneer Tikka" in body
    assert "Walk-in Customer" in body

    filtered = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders/export.csv",
        params={"status": "received", "source": "manual"},
        headers=headers,
    )
    assert filtered.status_code == 200
    filtered_body = filtered.content.decode("utf-8-sig")
    assert order_code in filtered_body
    assert "Old Dish" not in filtered_body


@pytest.mark.asyncio
async def test_export_csv_does_not_leak_other_kitchen(
    client: AsyncClient, order_ctx, manual_order_payload
):
    from tests.conftest import _seed_kitchen_with_dish

    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    assert created.status_code == 201
    leaked_code = created.json()["order_code"]

    _, other_kitchen, _, _, other_token = _seed_kitchen_with_dish()
    response = await client.get(
        f"/api/v1/kitchens/{other_kitchen}/orders/export.csv",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 200
    assert leaked_code not in response.content.decode("utf-8-sig")

    blocked = await client.get(
        f"/api/v1/kitchens/{other_kitchen}/orders/export.csv",
        headers=headers,
    )
    assert blocked.status_code == 403
