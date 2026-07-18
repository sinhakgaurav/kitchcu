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
