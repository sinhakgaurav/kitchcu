import uuid
from datetime import UTC, datetime

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL, VALID_GSTIN, _mark_order_delivered, _seed_owner_with_order

# Invoices are synced from orders created "now", so reports must target the current
# period — a hardcoded month silently reports zero invoices once the calendar moves on.
_NOW = datetime.now(UTC)
PERIOD = f"year={_NOW.year}&month={_NOW.month}"


def _profile_payload(**overrides):
    data = {
        "gstin": VALID_GSTIN,
        "legal_name": "Test Kitchen Foods Pvt Ltd",
        "trade_name": "Test Kitchen",
        "registered_address": "123 MG Road, Pune, Maharashtra 411001",
        "default_tax_rate": 5.0,
        "is_active": True,
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_upsert_gst_profile(client: AsyncClient, billing_ctx):
    _, kitchen_id, _, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/gst/profile",
        json=_profile_payload(),
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["gstin"] == VALID_GSTIN
    assert data["state_code"] == "27"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_upsert_gst_profile_rejects_invalid_gstin(client: AsyncClient, billing_ctx):
    _, kitchen_id, _, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/gst/profile",
        json=_profile_payload(gstin="INVALID-GSTIN"),
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_two_kitchens_same_invoice_prefix_can_both_sync(client: AsyncClient):
    """Invoice numbers always use the kitchen code, even when profiles share a prefix."""
    _, kitchen_a, order_a, code_a, token_a = _seed_owner_with_order()
    _, kitchen_b, order_b, code_b, token_b = _seed_owner_with_order()
    _mark_order_delivered(order_a)
    _mark_order_delivered(order_b)

    numbers: list[str] = []
    for kitchen_id, token, gstin, code in (
        (kitchen_a, token_a, "27AAAAA0001C1Z5", code_a),
        (kitchen_b, token_b, "27AAAAA0002C1Z5", code_b),
    ):
        headers = {"Authorization": f"Bearer {token}"}
        profile = await client.put(
            f"/api/v1/kitchens/{kitchen_id}/gst/profile",
            json=_profile_payload(gstin=gstin, invoice_prefix="SHK"),
            headers=headers,
        )
        assert profile.status_code == 200, profile.text
        sync = await client.post(
            f"/api/v1/kitchens/{kitchen_id}/gst/sync",
            headers=headers,
        )
        assert sync.status_code == 200, sync.text
        assert sync.json()["synced_count"] == 1
        number = sync.json()["invoices"][0]["invoice_number"]
        assert number.startswith(f"{code}-GST-")
        assert not number.startswith("SHK-GST-")
        numbers.append(number)
    assert numbers[0] != numbers[1]


@pytest.mark.asyncio
async def test_invoice_numbers_increment_within_the_period(client: AsyncClient):
    _, kitchen_id, order_a, kitchen_code, token = _seed_owner_with_order()
    order_b = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_orders.orders
            (id, kitchen_id, bill_id, order_code, status, source, delivery_type,
             payment_method, subtotal, delivery_fee, total, updated_at)
            VALUES (
                %s::uuid, %s::uuid, %s, %s, 'delivered', 'manual',
                'pickup', 'cod', 199, 0, 199, NOW() + interval '1 second'
            )
            """,
            (
                str(order_b),
                str(kitchen_id),
                f"{kitchen_code}-BILL-20260712-0002",
                f"{kitchen_code}-BILL-20260712-0002",
            ),
        )
    conn.close()
    _mark_order_delivered(order_a)

    headers = {"Authorization": f"Bearer {token}"}
    profile = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/gst/profile",
        json=_profile_payload(),
        headers=headers,
    )
    assert profile.status_code == 200, profile.text
    sync = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/gst/sync",
        headers=headers,
    )
    assert sync.status_code == 200, sync.text
    body = sync.json()
    assert body["synced_count"] == 2
    numbers = [inv["invoice_number"] for inv in body["invoices"]]
    assert all(n.startswith(f"{kitchen_code}-GST-") for n in numbers)
    assert sorted(n.rsplit("-", 1)[-1] for n in numbers) == ["0001", "0002"]


@pytest.mark.asyncio
async def test_sync_creates_invoice_for_delivered_order(client: AsyncClient, billing_ctx):
    _, kitchen_id, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    profile = await client.put(
        f"/api/v1/kitchens/{kitchen_id}/gst/profile",
        json=_profile_payload(),
        headers=headers,
    )
    assert profile.status_code == 200

    _mark_order_delivered(order_id)

    sync = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/gst/sync",
        headers=headers,
    )
    assert sync.status_code == 200
    body = sync.json()
    assert body["synced_count"] == 1
    assert body["invoices"][0]["order_id"] == str(order_id)
    assert body["invoices"][0]["tax_rate"] == 5.0
    assert body["invoices"][0]["gross_total"] == 398.0


@pytest.mark.asyncio
async def test_monthly_report_and_balance_sheet(client: AsyncClient, billing_ctx):
    _, kitchen_id, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        f"/api/v1/kitchens/{kitchen_id}/gst/profile",
        json=_profile_payload(),
        headers=headers,
    )
    _mark_order_delivered(order_id)
    await client.post(f"/api/v1/kitchens/{kitchen_id}/gst/sync", headers=headers)

    report = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/gst/reports/monthly?{PERIOD}",
        headers=headers,
    )
    assert report.status_code == 200
    report_data = report.json()
    assert report_data["invoice_count"] == 1
    assert report_data["total_gross_sales"] == 398.0
    assert report_data["total_tax"] > 0
    assert report_data["audit_status"] == "open"

    sheet = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/gst/reports/balance-sheet?{PERIOD}",
        headers=headers,
    )
    assert sheet.status_code == 200
    sheet_data = sheet.json()
    assert sheet_data["total_assets"] >= sheet_data["total_liabilities"]


@pytest.mark.asyncio
async def test_close_monthly_audit(client: AsyncClient, billing_ctx):
    _, kitchen_id, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        f"/api/v1/kitchens/{kitchen_id}/gst/profile",
        json=_profile_payload(),
        headers=headers,
    )
    _mark_order_delivered(order_id)
    await client.post(f"/api/v1/kitchens/{kitchen_id}/gst/sync", headers=headers)

    close = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/gst/audit/close?{PERIOD}",
        headers=headers,
    )
    assert close.status_code == 200
    audit = close.json()
    assert audit["status"] == "closed"
    assert audit["balance_sheet"] is not None
    assert audit["closed_at"] is not None

    again = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/gst/audit/close?{PERIOD}",
        headers=headers,
    )
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_monthly_gst_excel_and_pdf_exports(client: AsyncClient, billing_ctx):
    _, kitchen_id, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    await client.put(
        f"/api/v1/kitchens/{kitchen_id}/gst/profile",
        json=_profile_payload(),
        headers=headers,
    )
    _mark_order_delivered(order_id)
    await client.post(f"/api/v1/kitchens/{kitchen_id}/gst/sync", headers=headers)

    xlsx = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/gst/reports/monthly/export.xlsx?{PERIOD}",
        headers=headers,
    )
    assert xlsx.status_code == 200, xlsx.text
    assert (
        "spreadsheetml" in xlsx.headers.get("content-type", "")
        or xlsx.headers.get("content-type", "").endswith("sheet")
    )
    assert xlsx.content[:2] == b"PK"  # zip/xlsx magic
    assert "attachment" in xlsx.headers.get("content-disposition", "")

    pdf = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/gst/reports/monthly/export.pdf?{PERIOD}",
        headers=headers,
    )
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers.get("content-type", "").startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_gst_sync_publishes_event(client: AsyncClient, billing_ctx):
    _, kitchen_id, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:billing:gst")

    await client.put(
        f"/api/v1/kitchens/{kitchen_id}/gst/profile",
        json=_profile_payload(),
        headers=headers,
    )
    _mark_order_delivered(order_id)
    sync = await client.post(f"/api/v1/kitchens/{kitchen_id}/gst/sync", headers=headers)
    assert sync.status_code == 200

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:billing:gst": "0-0"}, count=20)
    assert len(messages) >= 1
