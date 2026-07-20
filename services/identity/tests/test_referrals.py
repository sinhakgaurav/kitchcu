"""Referral program — customer→kitchen and kitchen→customer (TDD)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _customer_token(client: AsyncClient, phone: str) -> str:
    await client.post("/api/v1/auth/customer/whatsapp/request", json={"phone": phone})
    res = await client.post(
        "/api/v1/auth/customer/whatsapp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


async def _owner_kitchen(client: AsyncClient, phone: str) -> tuple[str, dict]:
    await client.post(
        "/api/v1/owners/register",
        json={"phone": phone, "name": "Ref Owner", "email": f"{phone}@test.com"},
    )
    await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    tok = (
        await client.post(
            "/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"}
        )
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}
    kitchen = (
        await client.post(
            "/api/v1/kitchens",
            headers=headers,
            json={
                "name": "Ref Kitchen",
                "address_line": "1 Test St",
                "city": "Pune",
                "state": "MH",
                "pincode": "411001",
                "latitude": 18.52,
                "longitude": 73.85,
            },
        )
    ).json()
    return tok, kitchen


@pytest.mark.asyncio
async def test_customer_refer_kitchen_and_reward_on_onboard(client: AsyncClient):
    cust_phone = "9111111001"
    owner_phone = "9111111002"
    cust_tok = await _customer_token(client, cust_phone)
    ch = {"Authorization": f"Bearer {cust_tok}"}

    created = await client.post(
        "/api/v1/customers/me/referrals/kitchens",
        headers=ch,
        json={
            "kitchen_name": "Spice Home",
            "contact_name": "Owner",
            "contact_phone": owner_phone,
            "city": "Pune",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "submitted"

    dash = await client.get("/api/v1/customers/me/referrals", headers=ch)
    assert dash.status_code == 200
    assert dash.json()["credit"]["balance_inr"] == 0
    assert dash.json()["pending_count"] == 1

    await _owner_kitchen(client, owner_phone)

    dash2 = await client.get("/api/v1/customers/me/referrals", headers=ch)
    body = dash2.json()
    assert body["credit"]["balance_inr"] == 10.0
    assert body["converted_count"] == 1
    assert body["estimated_subscription_savings_inr"] == 10.0


@pytest.mark.asyncio
async def test_owner_refer_customer_reward_on_onboard(client: AsyncClient):
    owner_phone = "9111112001"
    cust_phone = "9111112002"
    tok, kitchen = await _owner_kitchen(client, owner_phone)
    oh = {"Authorization": f"Bearer {tok}"}

    lead = await client.post(
        "/api/v1/owners/me/referrals/customers",
        headers=oh,
        json={
            "kitchen_id": kitchen["id"],
            "contact_name": "Asha",
            "contact_phone": cust_phone,
        },
    )
    assert lead.status_code == 201, lead.text

    await _customer_token(client, cust_phone)

    dash = await client.get("/api/v1/owners/me/referrals", headers=oh)
    assert dash.status_code == 200
    body = dash.json()
    assert body["credit"]["balance_inr"] == 10.0
    assert body["converted_count"] == 1


@pytest.mark.asyncio
async def test_customer_bulk_and_template(client: AsyncClient):
    tok = await _customer_token(client, "9111113001")
    ch = {"Authorization": f"Bearer {tok}"}

    tmpl = await client.get("/api/v1/customers/me/referrals/template.csv", headers=ch)
    assert tmpl.status_code == 200
    assert "kitchen_name" in tmpl.text
    assert "contact_phone" in tmpl.text

    bulk = await client.post(
        "/api/v1/customers/me/referrals/bulk",
        headers=ch,
        json={
            "rows": [
                {
                    "kitchen_name": "K1",
                    "contact_phone": "9111113010",
                    "city": "Pune",
                },
                {
                    "kitchen_name": "K2",
                    "contact_phone": "9111113011",
                    "city": "Mumbai",
                },
            ]
        },
    )
    assert bulk.status_code == 200, bulk.text
    assert bulk.json()["accepted"] == 2


@pytest.mark.asyncio
async def test_internal_apply_owner_credit(client: AsyncClient):
    owner_phone = "9111114001"
    cust_phone = "9111114002"
    tok, kitchen = await _owner_kitchen(client, owner_phone)
    oh = {"Authorization": f"Bearer {tok}"}
    await client.post(
        "/api/v1/owners/me/referrals/customers",
        headers=oh,
        json={"kitchen_id": kitchen["id"], "contact_phone": cust_phone},
    )
    await _customer_token(client, cust_phone)

    # Resolve owner id from JWT me endpoint if available; use kitchens list owner
    kitchens = await client.get("/api/v1/kitchens/me", headers=oh)
    owner_id = kitchens.json()[0]["owner_id"]

    applied = await client.post(
        "/api/v1/internal/referrals/apply-owner-credit",
        headers={"X-Internal-Key": "test-internal-key-for-pytest"},
        json={"owner_id": owner_id, "charge_amount_inr": 499},
    )
    assert applied.status_code == 200, applied.text
    data = applied.json()
    assert data["applied_inr"] == 10.0
    assert data["remaining_charge_inr"] == 489.0

    dash = await client.get("/api/v1/owners/me/referrals", headers=oh)
    assert dash.json()["credit"]["balance_inr"] == 0.0
    assert dash.json()["credit"]["lifetime_applied_inr"] == 10.0


@pytest.mark.asyncio
async def test_admin_referral_settings(client: AsyncClient):
    import os

    import psycopg2

    from app.admin_routes import hash_password

    admin_id = str(uuid.uuid4())
    conn = psycopg2.connect(os.environ["DATABASE_SYNC_URL"])
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ckac_identity.platform_admins
                  (id, email, password_hash, name, role, is_active)
                VALUES (%s, %s, %s, %s, %s, true)
                ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """,
                (
                    admin_id,
                    "ref-admin@kitchcu.dev",
                    hash_password("admin123456"),
                    "Ref Admin",
                    "superadmin",
                ),
            )
    finally:
        conn.close()

    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "ref-admin@kitchcu.dev", "password": "admin123456"},
    )
    assert login.status_code == 200, login.text
    ah = {"Authorization": f"Bearer {login.json()['access_token']}"}

    patched = await client.patch(
        "/api/v1/admin/referrals/settings",
        headers=ah,
        json={
            "customer_to_kitchen_reward_inr": 25,
            "kitchen_to_customer_reward_inr": 15,
            "enabled": True,
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["customer_to_kitchen_reward_inr"] == 25.0
    assert patched.json()["kitchen_to_customer_reward_inr"] == 15.0

    leads = await client.get("/api/v1/admin/referrals/leads", headers=ah)
    assert leads.status_code == 200
