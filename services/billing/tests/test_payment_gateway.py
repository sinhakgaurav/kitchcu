"""Kitchen payment gateway credentials — owner + super-admin CRUD (TDD)."""

import os
import uuid

import psycopg2
from jose import jwt

from tests.conftest import SYNC_DB_URL, _seed_owner_with_order

JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_EMAIL = "admin-pgw@test.ckac"


async def test_owner_payment_gateway_get_empty_then_upsert(client):
    owner_id, kitchen_id, _order_id, _code, token = _seed_owner_with_order()
    headers = {"Authorization": f"Bearer {token}"}

    empty = await client.get(
        f"/api/v1/billing/kitchens/{kitchen_id}/payment-gateway",
        headers=headers,
    )
    assert empty.status_code == 200, empty.text
    body = empty.json()
    assert body["kitchen_id"] == str(kitchen_id)
    assert body["provider"] == "razorpay"
    assert body["key_secret_configured"] is False

    saved = await client.put(
        f"/api/v1/billing/kitchens/{kitchen_id}/payment-gateway",
        headers=headers,
        json={
            "key_id": "rzp_test_kitchen_abc",
            "key_secret": "kitchen_secret_value_9999",
            "webhook_secret": "whsec_kitchen_aaaa",
            "linked_account_id": "acc_test_linked",
            "is_active": True,
        },
    )
    assert saved.status_code == 200, saved.text
    out = saved.json()
    assert out["key_id"] == "rzp_test_kitchen_abc"
    assert out["key_secret_configured"] is True
    assert out["key_secret_masked"].endswith("9999")
    assert "kitchen_secret" not in (out["key_secret_masked"] or "")
    assert out["webhook_secret_configured"] is True
    assert out["linked_account_id"] == "acc_test_linked"

    # Omit secrets — keep existing
    keep = await client.put(
        f"/api/v1/billing/kitchens/{kitchen_id}/payment-gateway",
        headers=headers,
        json={"key_id": "rzp_test_kitchen_abc", "linked_account_id": "acc_test_linked_2"},
    )
    assert keep.status_code == 200
    assert keep.json()["key_secret_configured"] is True
    assert keep.json()["linked_account_id"] == "acc_test_linked_2"


async def test_owner_cannot_access_other_kitchen_gateway(client):
    _owner_a, kitchen_a, _, _, token_a = _seed_owner_with_order()
    _owner_b, kitchen_b, _, _, _token_b = _seed_owner_with_order()
    headers = {"Authorization": f"Bearer {token_a}"}
    res = await client.get(
        f"/api/v1/billing/kitchens/{kitchen_b}/payment-gateway",
        headers=headers,
    )
    assert res.status_code == 403
    _ = kitchen_a


async def test_owner_can_clear_payment_gateway(client):
    _owner_id, kitchen_id, _order_id, _code, token = _seed_owner_with_order()
    headers = {"Authorization": f"Bearer {token}"}
    await client.put(
        f"/api/v1/billing/kitchens/{kitchen_id}/payment-gateway",
        headers=headers,
        json={"key_id": "rzp_test_clear_me", "key_secret": "secret_to_clear_1234"},
    )
    cleared = await client.delete(
        f"/api/v1/billing/kitchens/{kitchen_id}/payment-gateway",
        headers=headers,
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["key_id"] is None
    assert cleared.json()["key_secret_configured"] is False


def _seed_admin(admin_id: uuid.UUID | None = None) -> str:
    admin_id = admin_id or uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, 'hash', 'PGW Admin', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE SET is_active = true
            RETURNING id
            """,
            (str(admin_id), ADMIN_EMAIL),
        )
        row = cur.fetchone()
        admin_id = row[0] if row else admin_id
    conn.close()
    return jwt.encode(
        {"sub": str(admin_id), "type": "admin", "email": ADMIN_EMAIL},
        JWT_SECRET,
        algorithm="HS256",
    )


async def test_admin_kitchen_payment_gateway_crud(client):
    _owner_id, kitchen_id, _order_id, _code, _token = _seed_owner_with_order()
    admin_headers = {"Authorization": f"Bearer {_seed_admin()}"}

    empty = await client.get(
        f"/api/v1/admin/kitchens/{kitchen_id}/payment-gateway",
        headers=admin_headers,
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["key_secret_configured"] is False

    saved = await client.put(
        f"/api/v1/admin/kitchens/{kitchen_id}/payment-gateway",
        headers=admin_headers,
        json={
            "key_id": "rzp_test_admin_kitchen",
            "key_secret": "admin_secret_value_4321",
            "linked_account_id": "acc_admin_linked",
            "is_active": True,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["key_id"] == "rzp_test_admin_kitchen"
    assert saved.json()["key_secret_configured"] is True

    cleared = await client.delete(
        f"/api/v1/admin/kitchens/{kitchen_id}/payment-gateway",
        headers=admin_headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["key_id"] is None
