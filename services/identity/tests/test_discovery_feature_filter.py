"""Discovery feed must hide hard-mode kitchens lacking the discovery feature."""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL
from tests.test_kitchens import KITCHEN_PAYLOAD


def _assign_package_without_feature(kitchen_id: uuid.UUID, missing: str) -> None:
    pkg_id = uuid.uuid4()
    code = f"no{missing[:8]}{pkg_id.hex[:8]}"
    conn = psycopg2.connect(os.environ.get("DATABASE_SYNC_URL", SYNC_DB_URL))
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_billing.packages (id, code, name, audience, is_active)
            VALUES (%s::uuid, %s, %s, 'owner', true)
            """,
            (str(pkg_id), code, f"No {missing}"),
        )
        cur.execute(
            """
            INSERT INTO ckac_billing.kitchen_packages (kitchen_id, package_id)
            VALUES (%s::uuid, %s::uuid)
            ON CONFLICT (kitchen_id) DO UPDATE SET package_id = EXCLUDED.package_id
            """,
            (str(kitchen_id), str(pkg_id)),
        )
    conn.close()


@pytest.mark.asyncio
async def test_nearby_excludes_hard_mode_kitchen_without_discovery(
    client: AsyncClient, auth_headers: dict
):
    blocked = await client.post(
        "/api/v1/kitchens",
        json={**KITCHEN_PAYLOAD, "name": "Blocked Discovery Kitchen"},
        headers=auth_headers,
    )
    assert blocked.status_code == 201, blocked.text
    allowed = await client.post(
        "/api/v1/kitchens",
        json={
            **KITCHEN_PAYLOAD,
            "name": "Open Discovery Kitchen",
            "latitude": 18.5370,
            "longitude": 73.8960,
        },
        headers=auth_headers,
    )
    assert allowed.status_code == 201, allowed.text
    blocked_id = blocked.json()["id"]
    allowed_id = allowed.json()["id"]
    _assign_package_without_feature(uuid.UUID(blocked_id), "discovery")

    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958},
    )
    assert resp.status_code == 200, resp.text
    ids = {k["id"] for k in resp.json()["kitchens"]}
    assert allowed_id in ids
    assert blocked_id not in ids


@pytest.mark.asyncio
async def test_discovery_home_excludes_hard_mode_kitchen_without_discovery(
    client: AsyncClient, auth_headers: dict
):
    blocked = await client.post(
        "/api/v1/kitchens",
        json={**KITCHEN_PAYLOAD, "name": "Home Blocked Kitchen"},
        headers=auth_headers,
    )
    assert blocked.status_code == 201, blocked.text
    _assign_package_without_feature(uuid.UUID(blocked.json()["id"]), "discovery")

    home = await client.get(
        "/api/v1/discovery/home",
        params={"latitude": 18.5362, "longitude": 73.8958},
        headers=auth_headers,
    )
    assert home.status_code == 200, home.text
    near_ids = {k["id"] for k in home.json()["near_you"]}
    assert blocked.json()["id"] not in near_ids
