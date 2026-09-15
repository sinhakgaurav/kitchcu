"""Admin pantry + recipe coverage — JWT, RBAC, tenant scope."""

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from tests.conftest import JWT_SECRET, SYNC_DB_URL, build_dish_payload


def _admin_token(admin_id: uuid.UUID, email: str) -> str:
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


def _seed_admin(role: str, *, grants: list[str] | None = None) -> str:
    admin_id = uuid.uuid4()
    email = f"pantry-{role}-{admin_id.hex[:8]}@kitchcu.dev"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', %s, %s, true)
            """,
            (str(admin_id), email, f"{role} Pantry Admin", role),
        )
        if grants is not None:
            for code in grants:
                cur.execute(
                    """
                    INSERT INTO ckac_identity.admin_permissions (code, description)
                    VALUES (%s, %s)
                    ON CONFLICT (code) DO NOTHING
                    """,
                    (code, code),
                )
                cur.execute(
                    """
                    INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (role, code),
                )
    conn.close()
    return _admin_token(admin_id, email)


@pytest.mark.asyncio
async def test_admin_pantry_requires_auth(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, _ = kitchen_ctx
    resp = await client.get(f"/api/v1/admin/kitchens/{kitchen_id}/ingredients")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_pantry_forbidden_without_permission(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, _ = kitchen_ctx
    token = _seed_admin("auditor", grants=["refunds:read"])
    resp = await client.get(
        f"/api/v1/admin/kitchens/{kitchen_id}/ingredients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert "kitchens:read" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_pantry_coverage_and_tenant_scope(client: AsyncClient, kitchen_ctx, kitchen_ctx_other):
    _, kitchen_id, owner_token = kitchen_ctx
    _, other_id, other_token = kitchen_ctx_other
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    ing = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/ingredients",
        json={
            "name": "Haldi",
            "unit": "g",
            "current_stock": 350,
            "brand": "Everest",
            "pack_size": 100,
            "pack_label": "100 g carton",
            "photo_url": "https://example.com/haldi.jpg",
        },
        headers=owner_headers,
    )
    assert ing.status_code == 201, ing.text
    ingredient_id = ing.json()["id"]

    await client.post(
        f"/api/v1/kitchens/{other_id}/ingredients",
        json={"name": "Other Kitchen Salt", "unit": "g", "current_stock": 10, "brand": "Tata"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    dish_payload = await build_dish_payload(client, kitchen_id, owner_token)
    mapped = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=dish_payload,
        headers=owner_headers,
    )
    mapped_id = mapped.json()["id"]
    await client.put(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{mapped_id}/recipe",
        json={"lines": [{"ingredient_id": ingredient_id, "quantity": 3, "unit": "g"}]},
        headers=owner_headers,
    )

    unmapped_payload = await build_dish_payload(client, kitchen_id, owner_token)
    unmapped_payload["name"] = "Draft Dal Tadka"
    unmapped_payload["is_active"] = False
    unmapped = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=unmapped_payload,
        headers=owner_headers,
    )
    assert unmapped.status_code == 201, unmapped.text

    token = _seed_admin("superadmin", grants=["*"])
    summary = await client.get(
        f"/api/v1/admin/kitchens/{kitchen_id}/ingredients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["kitchen_id"] == str(kitchen_id)
    names = {row["name"] for row in body["ingredients"]}
    assert "Haldi" in names
    assert "Other Kitchen Salt" not in names
    haldi = next(row for row in body["ingredients"] if row["name"] == "Haldi")
    assert haldi["brand"] == "Everest"
    assert haldi["pack_size"] == 100
    assert body["coverage"]["dishes_total"] == 2
    assert body["coverage"]["dishes_mapped"] == 1
    unmapped_names = {row["name"] for row in body["coverage"]["dishes_unmapped"]}
    assert "Draft Dal Tadka" in unmapped_names
    assert unmapped.json()["name"] in unmapped_names

    missing = await client.get(
        f"/api/v1/admin/kitchens/{uuid.uuid4()}/ingredients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing.status_code == 404
