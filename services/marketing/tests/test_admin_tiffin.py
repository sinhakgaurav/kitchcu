"""Admin tiffin subscription list + accept/deny."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import JWT_SECRET, SYNC_DB_URL, _seed_marketing_ctx


def _seed_admin() -> str:
    admin_id = uuid.uuid4()
    email = f"admin-{admin_id.hex[:8]}@kitchcu.dev"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', 'Tiffin Admin', 'superadmin', true)
            """,
            (str(admin_id), email),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
            VALUES ('superadmin', '*')
            ON CONFLICT DO NOTHING
            """
        )
    conn.close()
    return jwt.encode(
        {
            "sub": str(admin_id),
            "type": "admin",
            "email": email,
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_admin_list_and_accept_pending_subscription(client: AsyncClient):
    ctx = _seed_marketing_ctx()
    kitchen_id = ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {ctx['owner_token']}"}
    customer_headers = {"Authorization": f"Bearer {ctx['customer_token']}"}
    admin_headers = {"Authorization": f"Bearer {_seed_admin()}"}

    plan = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
        headers=owner_headers,
        json={
            "name": "Admin Ops Thali",
            "plan_type": "thali",
            "price_monthly": 1999,
            "dishes_config": {
                "dish_ids": [str(ctx["dish_id"])],
                "weekdays": [0, 1, 2, 3, 4],
                "meals_per_day": 1,
            },
        },
    )
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]

    req = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans/{plan_id}/subscribe",
        headers=customer_headers,
        json={"customer_name": "Ravi"},
    )
    assert req.status_code == 201, req.text
    sub_id = req.json()["id"]

    listed = await client.get(
        f"/api/v1/admin/kitchens/{kitchen_id}/subscriptions?status=pending",
        headers=admin_headers,
    )
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["total"] >= 1
    assert any(s["id"] == sub_id for s in body["subscriptions"])

    accept = await client.post(
        f"/api/v1/admin/kitchens/{kitchen_id}/subscriptions/{sub_id}/accept",
        headers=admin_headers,
        json={"owner_note": "Platform accepted"},
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["status"] == "active"
