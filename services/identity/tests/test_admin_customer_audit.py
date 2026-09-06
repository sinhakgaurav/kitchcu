"""Admin customer mutations must write audit rows with masked phone."""

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
ADMIN_EMAIL = "admin-customer-audit@test.ckac"


def _seed_admin_and_customer() -> tuple[str, uuid.UUID, str]:
    admin_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    phone = f"+9198{customer_id.int % 900000000 + 100000000}"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, %s, 'Audit Admin', 'superadmin', true)
            ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash, is_active = true
            RETURNING id
            """,
            (str(admin_id), ADMIN_EMAIL, hash_password("admin123456")),
        )
        row = cur.fetchone()
        if row:
            admin_id = row[0]
        cur.execute(
            """
            INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
            VALUES ('superadmin', '*')
            ON CONFLICT DO NOTHING
            """
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.customers (id, name, phone, status, password_hash)
            VALUES (%s::uuid, 'Audit Customer', %s, 'active', 'hashed-secret')
            """,
            (str(customer_id), phone),
        )
    conn.close()
    token = jwt.encode(
        {"sub": str(admin_id), "email": ADMIN_EMAIL, "type": "admin"},
        JWT_SECRET,
        algorithm="HS256",
    )
    return token, customer_id, phone


def _audit_rows(customer_id: uuid.UUID, action: str) -> list[tuple]:
    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT action, summary, resource_type, resource_id
            FROM ckac_identity.admin_audit_events
            WHERE resource_id = %s AND action = %s
            ORDER BY created_at DESC
            """,
            (str(customer_id), action),
        )
        rows = cur.fetchall()
    conn.close()
    return rows


@pytest.mark.asyncio
async def test_customer_status_update_writes_audit(client: AsyncClient):
    token, customer_id, phone = _seed_admin_and_customer()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(
        f"/api/v1/admin/customers/{customer_id}/status",
        json={"status": "suspended"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "suspended"

    rows = _audit_rows(customer_id, "customer.status.updated")
    assert len(rows) >= 1
    _action, summary, resource_type, resource_id = rows[0]
    assert resource_type == "customer"
    assert resource_id == str(customer_id)
    assert phone not in summary
    assert phone[-4:] in summary


@pytest.mark.asyncio
async def test_customer_clear_password_writes_audit(client: AsyncClient):
    token, customer_id, phone = _seed_admin_and_customer()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        f"/api/v1/admin/customers/{customer_id}/clear-password",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["has_password"] is False

    rows = _audit_rows(customer_id, "customer.password_cleared")
    assert len(rows) >= 1
    _action, summary, resource_type, resource_id = rows[0]
    assert resource_type == "customer"
    assert resource_id == str(customer_id)
    assert phone not in summary
    assert phone[-4:] in summary
