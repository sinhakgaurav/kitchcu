"""EDD — referral writes must publish Redis Stream + transactional outbox."""

from __future__ import annotations

import json

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL


async def _customer_token(client: AsyncClient, phone: str) -> str:
    await client.post("/api/v1/auth/customer/whatsapp/request", json={"phone": phone})
    res = await client.post(
        "/api/v1/auth/customer/whatsapp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert res.status_code == 200
    return res.json()["access_token"]


async def _owner_kitchen(client: AsyncClient, phone: str) -> tuple[str, dict]:
    reg = await client.post(
        "/api/v1/owners/register",
        json={"phone": phone, "name": "EDD Ref Owner", "email": f"{phone}@test.com"},
    )
    assert reg.status_code in (200, 201), reg.text
    otp_req = await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    assert otp_req.status_code in (200, 202), otp_req.text
    verify = await client.post(
        "/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"}
    )
    assert verify.status_code == 200, verify.text
    tok = verify.json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}
    kitchen_res = await client.post(
        "/api/v1/kitchens",
        headers=headers,
        json={
            "name": "EDD Ref Kitchen",
            "address_line": "1 Event St",
            "city": "Pune",
            "state": "MH",
            "pincode": "411001",
            "latitude": 18.52,
            "longitude": 73.85,
        },
    )
    assert kitchen_res.status_code == 201, kitchen_res.text
    return tok, kitchen_res.json()


def _latest_outbox(event_type: str) -> tuple[str, bool] | None:
    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT event_type, published FROM ckac_events.outbox "
            "WHERE event_type = %s ORDER BY created_at DESC LIMIT 1",
            (event_type,),
        )
        row = cur.fetchone()
    conn.close()
    return (row[0], row[1]) if row else None


@pytest.mark.asyncio
async def test_referral_lead_submitted_publishes_stream_and_outbox(client: AsyncClient):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:identity:referral")

    tok = await _customer_token(client, "9111122001")
    ch = {"Authorization": f"Bearer {tok}"}
    created = await client.post(
        "/api/v1/customers/me/referrals/kitchens",
        headers=ch,
        json={
            "kitchen_name": "EDD Spice",
            "contact_name": "Owner",
            "contact_phone": "9111122002",
            "city": "Pune",
        },
    )
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:identity:referral": "0-0"}, count=20)
    assert len(messages) >= 1
    _, entries = messages[0]
    event_data = json.loads(entries[-1][1]["data"])
    assert event_data["event_type"] == "referral.lead_submitted"
    assert event_data["aggregate_type"] == "referral"
    assert event_data["aggregate_id"] == lead_id
    assert event_data["producer"] == "identity-service"
    assert event_data["payload"]["direction"] == "customer_to_kitchen"

    outbox = _latest_outbox("referral.lead_submitted")
    assert outbox is not None
    assert outbox[0] == "referral.lead_submitted"
    assert outbox[1] is True


@pytest.mark.asyncio
async def test_referral_rewarded_publishes_on_owner_onboard(client: AsyncClient):
    from app.main import redis_client

    cust_tok = await _customer_token(client, "9111123001")
    ch = {"Authorization": f"Bearer {cust_tok}"}
    created = await client.post(
        "/api/v1/customers/me/referrals/kitchens",
        headers=ch,
        json={
            "kitchen_name": "Reward Kitchen",
            "contact_phone": "9111123002",
        },
    )
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]

    if redis_client:
        await redis_client.delete("ckac:identity:referral")

    await _owner_kitchen(client, "9111123002")

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:identity:referral": "0-0"}, count=20)
    assert len(messages) >= 1
    _, entries = messages[0]
    rewarded = [
        json.loads(e[1]["data"])
        for e in entries
        if json.loads(e[1]["data"]).get("event_type") == "referral.rewarded"
    ]
    assert rewarded, "expected referral.rewarded on stream after kitchen onboard"
    assert rewarded[-1]["aggregate_id"] == lead_id
    assert rewarded[-1]["payload"]["amount_inr"] == 10.0
    assert rewarded[-1]["producer"] == "identity-service"

    outbox = _latest_outbox("referral.rewarded")
    assert outbox is not None
    assert outbox[1] is True
