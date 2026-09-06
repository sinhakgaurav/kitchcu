"""Hard-mode package without loyalty_crm must 403 owner CRM/coupon/promotion routes."""

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
async def test_coupon_create_403_when_packaged_without_loyalty_crm(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    _assign_package_without_feature(kid, "loyalty_crm")
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    create = await client.post(
        f"/api/v1/kitchens/{kid}/coupons",
        json={"code": "BLOCKED", "discount_type": "fixed", "discount_value": 10},
        headers=headers,
    )
    assert create.status_code == 403, create.text
    assert "loyalty_crm" in create.json()["detail"]


@pytest.mark.asyncio
async def test_crm_list_403_when_packaged_without_loyalty_crm(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    _assign_package_without_feature(kid, "loyalty_crm")
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    listed = await client.get(f"/api/v1/kitchens/{kid}/crm/customers", headers=headers)
    assert listed.status_code == 403, listed.text
    assert "loyalty_crm" in listed.json()["detail"]


@pytest.mark.asyncio
async def test_promotions_list_403_when_packaged_without_loyalty_crm(client: AsyncClient, marketing_ctx):
    kid = marketing_ctx["kitchen_id"]
    _assign_package_without_feature(kid, "loyalty_crm")
    headers = {"Authorization": f"Bearer {marketing_ctx['owner_token']}"}

    listed = await client.get(f"/api/v1/kitchens/{kid}/promotions", headers=headers)
    assert listed.status_code == 403, listed.text
    assert "loyalty_crm" in listed.json()["detail"]
