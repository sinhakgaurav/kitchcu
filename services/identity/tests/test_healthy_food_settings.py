"""P54 — Super-admin dish calories / Healthy kill-switches + kcal cap."""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient

from app.admin_routes import hash_password

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
ADMIN_EMAIL = "healthy-food-admin@test.ckac"


def _admin_headers() -> dict[str, str]:
    from jose import jwt

    admin_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins
              (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, %s, 'Healthy Food Admin', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE SET
              password_hash = EXCLUDED.password_hash,
              is_active = true
            RETURNING id
            """,
            (str(admin_id), ADMIN_EMAIL, hash_password("admin123456")),
        )
        row = cur.fetchone()
        if row:
            admin_id = row[0]
    conn.close()
    token = jwt.encode(
        {
            "sub": str(admin_id),
            "email": ADMIN_EMAIL,
            "type": "admin",
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _restore_defaults() -> None:
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.healthy_food_settings
              (id, healthy_max_kcal, healthy_min_score)
            VALUES (1, 500, 65)
            ON CONFLICT (id) DO UPDATE SET
              healthy_max_kcal = 500,
              healthy_min_score = 65
            """
        )
        for key, desc in (
            (
                "dish_calories",
                "Public dish calorie totals from pantry × recipe (kitchen estimate)",
            ),
            (
                "dish_healthy_tag",
                "Automatic Healthy badge when the plate meets the Control kcal cap",
            ),
        ):
            cur.execute(
                """
                INSERT INTO ckac_identity.feature_flags (key, enabled, scope, description)
                VALUES (%s, true, 'kitchen', %s)
                ON CONFLICT (key) DO UPDATE SET enabled = true
                """,
                (key, desc),
            )
    conn.close()


@pytest.fixture(autouse=True)
def _reset_healthy_food():
    _restore_defaults()
    yield
    _restore_defaults()


@pytest.mark.asyncio
async def test_healthy_food_requires_admin(client: AsyncClient):
    res = await client.get("/api/v1/admin/healthy-food")
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_healthy_food_defaults(client: AsyncClient):
    headers = _admin_headers()
    res = await client.get("/api/v1/admin/healthy-food", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["healthy_max_kcal"] == 500
    assert body["healthy_min_score"] == 65
    assert body["dish_calories_enabled"] is True
    assert body["dish_healthy_tag_enabled"] is True


@pytest.mark.asyncio
async def test_feature_flags_include_calories_and_healthy(client: AsyncClient):
    headers = _admin_headers()
    res = await client.get("/api/v1/admin/feature-flags", headers=headers)
    assert res.status_code == 200, res.text
    keys = {row["key"] for row in res.json()}
    assert "dish_calories" in keys
    assert "dish_healthy_tag" in keys


@pytest.mark.asyncio
async def test_patch_healthy_max_kcal_and_flags(client: AsyncClient):
    headers = _admin_headers()
    patched = await client.patch(
        "/api/v1/admin/healthy-food",
        headers=headers,
        json={
            "healthy_max_kcal": 400,
            "healthy_min_score": 70,
            "dish_calories_enabled": True,
            "dish_healthy_tag_enabled": False,
        },
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["healthy_max_kcal"] == 400
    assert body["healthy_min_score"] == 70
    assert body["dish_healthy_tag_enabled"] is False
    assert body["dish_calories_enabled"] is True

    again = await client.get("/api/v1/admin/healthy-food", headers=headers)
    assert again.json()["healthy_max_kcal"] == 400
    assert again.json()["dish_healthy_tag_enabled"] is False

    flags = await client.get("/api/v1/admin/feature-flags", headers=headers)
    by_key = {row["key"]: row["enabled"] for row in flags.json()}
    assert by_key["dish_healthy_tag"] is False
    assert by_key["dish_calories"] is True


@pytest.mark.asyncio
async def test_healthy_max_kcal_out_of_range(client: AsyncClient):
    headers = _admin_headers()
    low = await client.patch(
        "/api/v1/admin/healthy-food",
        headers=headers,
        json={"healthy_max_kcal": 49},
    )
    assert low.status_code == 422
    high = await client.patch(
        "/api/v1/admin/healthy-food",
        headers=headers,
        json={"healthy_max_kcal": 5001},
    )
    assert high.status_code == 422
    score = await client.patch(
        "/api/v1/admin/healthy-food",
        headers=headers,
        json={"healthy_min_score": 101},
    )
    assert score.status_code == 422
