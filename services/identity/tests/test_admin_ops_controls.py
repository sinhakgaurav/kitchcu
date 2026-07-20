"""Super-admin ops control fills — kitchen-scoped orders + health fields."""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest
from httpx import AsyncClient
from jose import jwt

from app.admin_routes import hash_password

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
ADMIN_EMAIL = "admin-ops-controls@test.ckac"


def _seed_admin_and_order() -> tuple[str, uuid.UUID, uuid.UUID]:
    admin_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    kitchen_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    order_id = uuid.uuid4()
    phone = f"+9191{customer_id.int % 900000000 + 100000000}"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, %s, 'Ops Admin', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash, is_active = true
            RETURNING id
            """,
            (str(admin_id), ADMIN_EMAIL, hash_password("admin123456")),
        )
        row = cur.fetchone()
        if row:
            admin_id = row[0]
        owner_phone = f"+9198{owner_id.int % 900000000 + 100000000}"
        cur.execute(
            """
            INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status)
            VALUES (%s::uuid, %s, 'Ops Owner', 'starter', 'trial')
            """,
            (str(owner_id), owner_phone),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, location, status, city)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Ops Kitchen',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active', 'Pune'
            )
            """,
            (str(kitchen_id), str(owner_id), f"CKO{owner_id.hex[:4].upper()}"),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.customers (id, name, phone, status)
            VALUES (%s::uuid, 'Ops Customer', %s, 'active')
            """,
            (str(customer_id), phone),
        )
        bill = f"BILL-{order_id.hex[:8].upper()}"
        cur.execute(
            """
            INSERT INTO ckac_orders.orders (
              id, kitchen_id, bill_id, order_code, status, source,
              delivery_type, payment_method, subtotal, delivery_fee, total,
              customer_name, customer_phone
            ) VALUES (
              %s::uuid, %s::uuid, %s, %s, 'received', 'manual',
              'delivery', 'cod', 200, 20, 220, 'Ops Customer', %s
            )
            """,
            (
                str(order_id),
                str(kitchen_id),
                bill,
                f"CKO{owner_id.hex[:3].upper()}-{bill}",
                phone,
            ),
        )
    conn.close()
    token = jwt.encode(
        {"sub": str(admin_id), "email": ADMIN_EMAIL, "type": "admin"},
        JWT_SECRET,
        algorithm="HS256",
    )
    return token, kitchen_id, customer_id


@pytest.mark.asyncio
async def test_admin_orders_filter_by_kitchen_and_customer(client: AsyncClient):
    token, kitchen_id, customer_id = _seed_admin_and_order()
    headers = {"Authorization": f"Bearer {token}"}

    by_kitchen = await client.get(
        f"/api/v1/admin/orders?kitchen_id={kitchen_id}&limit=50",
        headers=headers,
    )
    assert by_kitchen.status_code == 200, by_kitchen.text
    rows = by_kitchen.json()
    assert len(rows) >= 1
    assert all(r["kitchen_id"] == str(kitchen_id) for r in rows)

    by_customer = await client.get(
        f"/api/v1/admin/orders?customer_id={customer_id}&limit=50",
        headers=headers,
    )
    assert by_customer.status_code == 200, by_customer.text
    cust_rows = by_customer.json()
    assert len(cust_rows) >= 1
    assert any(r.get("customer_id") == str(customer_id) for r in cust_rows)


@pytest.mark.asyncio
async def test_admin_kitchens_include_health_fields(client: AsyncClient):
    token, kitchen_id, _ = _seed_admin_and_order()
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/admin/kitchens", headers=headers)
    assert res.status_code == 200, res.text
    kitchen = next((k for k in res.json() if k["id"] == str(kitchen_id)), None)
    assert kitchen is not None
    assert "open_ticket_count" in kitchen
    assert "open_refund_count" in kitchen
    assert "last_order_at" in kitchen
    assert kitchen["last_order_at"] is not None
