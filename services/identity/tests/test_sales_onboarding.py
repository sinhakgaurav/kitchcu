"""P55 — sales role onboards kitchens and trains owners (scoped)."""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from app.admin_routes import hash_password
from app.sales import TRAINING_STEPS

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
SALES_EMAIL = "sales-rep@test.ckac"
OTHER_SALES_EMAIL = "sales-other@test.ckac"
SUPER_EMAIL = "sales-super@test.ckac"
SUPPORT_EMAIL = "sales-support@test.ckac"


def _seed_staff() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    sales_id = uuid.uuid4()
    other_id = uuid.uuid4()
    super_id = uuid.uuid4()
    support_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        for admin_id, email, role in (
            (sales_id, SALES_EMAIL, "sales"),
            (other_id, OTHER_SALES_EMAIL, "sales"),
            (super_id, SUPER_EMAIL, "superadmin"),
            (support_id, SUPPORT_EMAIL, "support"),
        ):
            cur.execute(
                """
                INSERT INTO ckac_identity.platform_admins
                  (id, email, password_hash, name, role, is_active)
                VALUES (%s::uuid, %s, %s, %s, %s, true)
                ON CONFLICT (email) DO UPDATE SET
                  password_hash = EXCLUDED.password_hash,
                  role = EXCLUDED.role,
                  is_active = true
                RETURNING id
                """,
                (str(admin_id), email, hash_password("salespass99"), email, role),
            )
            row = cur.fetchone()
            if row:
                if email == SALES_EMAIL:
                    sales_id = row[0]
                elif email == OTHER_SALES_EMAIL:
                    other_id = row[0]
                elif email == SUPER_EMAIL:
                    super_id = row[0]
                else:
                    support_id = row[0]
        cur.execute(
            """
            INSERT INTO ckac_identity.feature_flags (key, enabled, scope, description)
            VALUES ('sales_onboarding', true, 'platform', 'Sales kitchen onboard + training')
            ON CONFLICT (key) DO UPDATE SET enabled = true
            """
        )
        for role, perm in (("sales", "sales:write"), ("sales", "kitchens:read")):
            cur.execute(
                """
                INSERT INTO ckac_identity.admin_permissions (code, description)
                VALUES (%s, %s)
                ON CONFLICT (code) DO NOTHING
                """,
                (perm, perm),
            )
            cur.execute(
                """
                INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (role, perm),
            )
    conn.close()
    return sales_id, other_id, super_id, support_id


def _token(admin_id: uuid.UUID, email: str) -> str:
    return jwt.encode(
        {"sub": str(admin_id), "email": email, "type": "admin"},
        JWT_SECRET,
        algorithm="HS256",
    )


def _headers(admin_id: uuid.UUID, email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(admin_id, email)}"}


ONBOARD = {
    "owner_name": "Meera Joshi",
    "owner_phone": "9112223334",
    "owner_email": "meera@test.ckac",
    "kitchen_name": "Meera Home Tiffins",
    "address_line": "12 FC Road",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411004",
    "latitude": 18.5204,
    "longitude": 73.8567,
}


@pytest.mark.asyncio
async def test_sales_onboard_creates_owner_and_kitchen(client: AsyncClient):
    sales_id, _, _, _ = _seed_staff()
    res = await client.post(
        "/api/v1/admin/sales/onboard",
        headers=_headers(sales_id, SALES_EMAIL),
        json=ONBOARD,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["kitchen"]["name"] == "Meera Home Tiffins"
    assert body["kitchen"]["code"].startswith("CKPNQ")
    assert body["owner_created"] is True
    assert body["kitchen"]["onboarded_by_admin_id"] == str(sales_id)
    assert body["training"]["total"] == len(TRAINING_STEPS)
    assert body["training"]["completed"] == 0


@pytest.mark.asyncio
async def test_sales_list_is_scoped_and_other_rep_forbidden(client: AsyncClient):
    sales_id, other_id, super_id, _ = _seed_staff()
    created = await client.post(
        "/api/v1/admin/sales/onboard",
        headers=_headers(sales_id, SALES_EMAIL),
        json=ONBOARD,
    )
    assert created.status_code == 201, created.text
    kid = created.json()["kitchen"]["id"]

    mine = await client.get("/api/v1/admin/kitchens", headers=_headers(sales_id, SALES_EMAIL))
    assert mine.status_code == 200
    assert any(r["id"] == kid for r in mine.json())

    other = await client.get("/api/v1/admin/kitchens", headers=_headers(other_id, OTHER_SALES_EMAIL))
    assert other.status_code == 200
    assert all(r["id"] != kid for r in other.json())

    blocked = await client.get(
        f"/api/v1/admin/kitchens/{kid}",
        headers=_headers(other_id, OTHER_SALES_EMAIL),
    )
    assert blocked.status_code == 403

    ok = await client.get(
        f"/api/v1/admin/kitchens/{kid}",
        headers=_headers(super_id, SUPER_EMAIL),
    )
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_sales_training_checklist(client: AsyncClient):
    sales_id, _, _, _ = _seed_staff()
    created = await client.post(
        "/api/v1/admin/sales/onboard",
        headers=_headers(sales_id, SALES_EMAIL),
        json=ONBOARD,
    )
    kid = created.json()["kitchen"]["id"]
    headers = _headers(sales_id, SALES_EMAIL)

    got = await client.get(f"/api/v1/admin/kitchens/{kid}/training", headers=headers)
    assert got.status_code == 200, got.text
    steps = got.json()["steps"]
    assert steps[0]["key"] == TRAINING_STEPS[0]["key"]
    assert steps[0]["completed"] is False

    from app.main import redis_client
    import json

    if redis_client:
        await redis_client.delete("ckac:identity:kitchen")

    patched = await client.patch(
        f"/api/v1/admin/kitchens/{kid}/training",
        headers=headers,
        json={"step_key": TRAINING_STEPS[0]["key"], "completed": True, "note": "Walked profile"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["completed"] == 1
    assert patched.json()["steps"][0]["completed"] is True

    if redis_client:
        messages = await redis_client.xread({"ckac:identity:kitchen": "0-0"}, count=80)
        events = []
        for _stream, entries in messages:
            for _id, fields in entries:
                events.append(json.loads(fields["data"]))
        assert any(e.get("event_type") == "kitchen.training.updated" for e in events)


@pytest.mark.asyncio
async def test_support_cannot_onboard(client: AsyncClient):
    _, _, _, support_id = _seed_staff()
    res = await client.post(
        "/api/v1/admin/sales/onboard",
        headers=_headers(support_id, SUPPORT_EMAIL),
        json=ONBOARD,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_onboard_reuses_existing_owner(client: AsyncClient):
    sales_id, _, _, _ = _seed_staff()
    headers = _headers(sales_id, SALES_EMAIL)
    first = await client.post("/api/v1/admin/sales/onboard", headers=headers, json=ONBOARD)
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/admin/sales/onboard",
        headers=headers,
        json={**ONBOARD, "kitchen_name": "Meera Sweets"},
    )
    assert second.status_code == 201, second.text
    assert second.json()["owner_created"] is False
    assert second.json()["kitchen"]["name"] == "Meera Sweets"
    assert first.json()["kitchen"]["owner_id"] == second.json()["kitchen"]["owner_id"]


@pytest.mark.asyncio
async def test_sales_onboard_requires_auth(client: AsyncClient):
    res = await client.post("/api/v1/admin/sales/onboard", json=ONBOARD)
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_sales_me_tabs_and_stats_forbidden(client: AsyncClient):
    sales_id, _, _, _ = _seed_staff()
    headers = _headers(sales_id, SALES_EMAIL)
    me = await client.get("/api/v1/admin/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["allowed_tabs"] == ["sales", "kitchens"]
    stats = await client.get("/api/v1/admin/stats", headers=headers)
    assert stats.status_code == 403


@pytest.mark.asyncio
async def test_other_rep_cannot_train(client: AsyncClient):
    sales_id, other_id, _, _ = _seed_staff()
    created = await client.post(
        "/api/v1/admin/sales/onboard",
        headers=_headers(sales_id, SALES_EMAIL),
        json=ONBOARD,
    )
    assert created.status_code == 201, created.text
    kid = created.json()["kitchen"]["id"]
    blocked = await client.patch(
        f"/api/v1/admin/kitchens/{kid}/training",
        headers=_headers(other_id, OTHER_SALES_EMAIL),
        json={"step_key": TRAINING_STEPS[0]["key"], "completed": True},
    )
    assert blocked.status_code == 403
