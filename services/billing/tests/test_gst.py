import pytest
from httpx import AsyncClient

from tests.conftest import VALID_GSTIN, _mark_order_delivered, _seed_owner_with_order


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
    """Invoice numbers are unique per kitchen (GSTIN), not globally — bulk seed
    previously 500'd when every kitchen reused prefix SHK."""
    _, kitchen_a, order_a, _, token_a = _seed_owner_with_order()
    _, kitchen_b, order_b, _, token_b = _seed_owner_with_order()
    _mark_order_delivered(order_a)
    _mark_order_delivered(order_b)

    for kitchen_id, token, gstin in (
        (kitchen_a, token_a, "27AAAAA0001C1Z5"),
        (kitchen_b, token_b, "27AAAAA0002C1Z5"),
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
        assert sync.json()["invoices"][0]["invoice_number"].startswith("SHK-GST-")


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
        f"/api/v1/kitchens/{kitchen_id}/gst/reports/monthly?year=2026&month=7",
        headers=headers,
    )
    assert report.status_code == 200
    report_data = report.json()
    assert report_data["invoice_count"] == 1
    assert report_data["total_gross_sales"] == 398.0
    assert report_data["total_tax"] > 0
    assert report_data["audit_status"] == "open"

    sheet = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/gst/reports/balance-sheet?year=2026&month=7",
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
        f"/api/v1/kitchens/{kitchen_id}/gst/audit/close?year=2026&month=7",
        headers=headers,
    )
    assert close.status_code == 200
    audit = close.json()
    assert audit["status"] == "closed"
    assert audit["balance_sheet"] is not None
    assert audit["closed_at"] is not None

    again = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/gst/audit/close?year=2026&month=7",
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
        f"/api/v1/kitchens/{kitchen_id}/gst/reports/monthly/export.xlsx?year=2026&month=7",
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
        f"/api/v1/kitchens/{kitchen_id}/gst/reports/monthly/export.pdf?year=2026&month=7",
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
