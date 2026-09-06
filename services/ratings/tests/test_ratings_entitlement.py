"""Hard-mode package without ratings must 403 customer create-rating."""

import uuid

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL


def _assign_package_without_feature(kitchen_id: uuid.UUID, missing: str) -> None:
    pkg_id = uuid.uuid4()
    code = f"no{missing[:8]}{pkg_id.hex[:8]}"
    conn = psycopg2.connect(SYNC_DB_URL)
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
async def test_create_rating_403_when_packaged_without_ratings(client: AsyncClient, ratings_ctx):
    _assign_package_without_feature(ratings_ctx["kitchen_id"], "ratings")
    headers = {"Authorization": f"Bearer {ratings_ctx['customer_token']}"}

    response = await client.post(
        f"/api/v1/customers/me/orders/{ratings_ctx['order_id']}/ratings",
        json={
            "ratings": [
                {
                    "dish_id": str(ratings_ctx["dish_id"]),
                    "home_taste_score": 5,
                    "quality_score": 4,
                }
            ]
        },
        headers=headers,
    )
    assert response.status_code == 403, response.text
    assert "ratings" in response.json()["detail"]
