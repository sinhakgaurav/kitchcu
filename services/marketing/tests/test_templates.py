"""Owner WhatsApp / email marketing templates — API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_template_crud_whatsapp_and_email(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    wa = await client.post(
        f"/api/v1/kitchens/{kid}/templates",
        headers=headers,
        json={
            "channel": "whatsapp",
            "name": "Daily menu WA",
            "body": "Hi {{ customer_name }} — today's special is {{ dish_name }}!",
        },
    )
    assert wa.status_code == 201, wa.text
    assert wa.json()["channel"] == "whatsapp"
    assert "customer_name" in wa.json()["variables"]
    assert "dish_name" in wa.json()["variables"]
    tid = wa.json()["id"]

    email = await client.post(
        f"/api/v1/kitchens/{kid}/templates",
        headers=headers,
        json={
            "channel": "email",
            "name": "Weekly digest",
            "subject": "This week at our kitchen",
            "body": "Hello {{ customer_name }}, see our menu.",
        },
    )
    assert email.status_code == 201, email.text
    assert email.json()["subject"] == "This week at our kitchen"

    listed = await client.get(f"/api/v1/kitchens/{kid}/templates", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 2

    patched = await client.patch(
        f"/api/v1/kitchens/{kid}/templates/{tid}",
        headers=headers,
        json={"name": "Daily menu updated", "is_active": False},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Daily menu updated"
    assert patched.json()["is_active"] is False

    deleted = await client.delete(
        f"/api/v1/kitchens/{kid}/templates/{tid}",
        headers=headers,
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_email_template_requires_subject(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    res = await client.post(
        f"/api/v1/kitchens/{kid}/templates",
        headers=headers,
        json={
            "channel": "email",
            "name": "No subject",
            "body": "Body without subject line here",
        },
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_template_send_dry_run_preview(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    created = await client.post(
        f"/api/v1/kitchens/{kid}/templates",
        headers=headers,
        json={
            "channel": "whatsapp",
            "name": "Send preview",
            "body": "Hello {{ customer_name }} from {{ kitchen_name }}",
        },
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    preview = await client.post(
        f"/api/v1/kitchens/{kid}/templates/{tid}/send",
        headers=headers,
        json={
            "audience": "all",
            "dry_run": True,
            "sample_vars": {"kitchen_name": "Demo Kitchen"},
        },
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["dry_run"] is True
    assert "Demo Kitchen" in body["preview"]
    assert body["channel"] == "whatsapp"


@pytest.mark.asyncio
async def test_template_send_includes_storefront_defaults(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}
    created = await client.post(
        f"/api/v1/kitchens/{kid}/templates",
        headers=headers,
        json={
            "channel": "whatsapp",
            "name": "Brand link",
            "body": "Order at {{ storefront_url }} — {{ tagline }} · {{ menu_line }}",
        },
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    preview = await client.post(
        f"/api/v1/kitchens/{kid}/templates/{tid}/send",
        headers=headers,
        json={
            "audience": "all",
            "dry_run": True,
            "sample_vars": {
                "storefront_url": "https://customer.example/k/CKPNQ001",
                "tagline": "Home taste",
            },
        },
    )
    assert preview.status_code == 200, preview.text
    text = preview.json()["preview"]
    assert "https://customer.example/k/CKPNQ001" in text
    assert "Home taste" in text
    assert "chef specials" in text  # menu_line default when omitted


@pytest.mark.asyncio
async def test_template_send_402_when_wallet_deduct_fails(
    client: AsyncClient, marketing_ctx, monkeypatch
):
    async def _fail_deduct(*_a, **_k) -> bool:
        return False

    from app import billing_client

    monkeypatch.setattr(billing_client, "deduct_messaging_wallet", _fail_deduct)

    kid = marketing_ctx["kitchen_id"]
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}
    created = await client.post(
        f"/api/v1/kitchens/{kid}/templates",
        headers=headers,
        json={
            "channel": "whatsapp",
            "name": "Paid blast",
            "body": "Specials for {{ customer_name }} — order now!",
        },
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    res = await client.post(
        f"/api/v1/kitchens/{kid}/templates/{tid}/send",
        headers=headers,
        json={
            "audience": "phones",
            "phones": ["+919111111111"],
            "dry_run": False,
        },
    )
    assert res.status_code == 402, res.text
    assert "wallet" in res.json()["detail"].lower()
