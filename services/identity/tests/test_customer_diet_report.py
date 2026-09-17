"""Customer checkup upload, ML diet profile, optional kitchen filter."""

from __future__ import annotations

import io
import json
import uuid

import psycopg2
import pytest
from httpx import AsyncClient

from app.admin_routes import hash_password
from tests.conftest import SYNC_DB_URL
from tests.test_diet_report_ml import _pdf

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00"
    b"\x00\x00IEND\xaeB`\x82"
)

KITCHEN_PAYLOAD = {
    "name": "Diet Kitchen",
    "address_line": "Koregaon Park",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411001",
    "latitude": 18.5362,
    "longitude": 73.8958,
}


async def _login(client: AsyncClient, phone: str = "+919711222333") -> str:
    await client.post("/api/v1/auth/customer/whatsapp/request", json={"phone": phone})
    ok = await client.post(
        "/api/v1/auth/customer/whatsapp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert ok.status_code == 200
    return ok.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_dish(kitchen_id: uuid.UUID, *, name: str, category_slug: str) -> uuid.UUID:
    category_id = uuid.uuid4()
    dish_id = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_catalog.categories (id, kitchen_id, name, slug, sort_order)
            VALUES (%s::uuid, %s::uuid, %s, %s, 0)
            """,
            (str(category_id), str(kitchen_id), category_slug.title(), category_slug),
        )
        cur.execute(
            """
            INSERT INTO ckac_catalog.dishes
            (id, kitchen_id, category_id, name, price, prep_time_min, delivery_time_min,
             max_time_min, is_active, ingredients_description)
            VALUES (%s::uuid, %s::uuid, %s::uuid, %s, 149.00, 20, 15, 35, true, %s)
            """,
            (str(dish_id), str(kitchen_id), str(category_id), name, name.lower()),
        )
    conn.close()
    return dish_id


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    admin_id = uuid.uuid4()
    email = f"diet-admin-{admin_id.hex[:8]}@test.ckac"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, %s, %s, 'Diet Admin', 'superadmin', true)
            """,
            (str(admin_id), email, hash_password("admin123456")),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
            VALUES ('superadmin', '*')
            ON CONFLICT DO NOTHING
            """
        )
    conn.close()
    login = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": email, "password": "admin123456"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_checkup_requires_auth(client: AsyncClient):
    res = await client.post(
        "/api/v1/customers/me/checkup-report",
        files={"file": ("labs.pdf", io.BytesIO(_pdf("HbA1c 8.2")), "application/pdf")},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_image_without_text_is_rejected(client: AsyncClient):
    token = await _login(client, "+919711222001")
    res = await client.post(
        "/api/v1/customers/me/checkup-report",
        headers=_auth(token),
        files={"file": ("scan.png", io.BytesIO(PNG), "image/png")},
    )
    assert res.status_code == 422, res.text
    assert "text" in res.json()["detail"].lower() or "pdf" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_pdf_builds_diabetes_profile_and_event(client: AsyncClient):
    from app.main import redis_client

    token = await _login(client, "+919711222002")
    if redis_client:
        await redis_client.delete("ckac:identity:customer")

    pdf = _pdf("Laboratory report HbA1c 8.2% Type 2 Diabetes Mellitus fasting glucose 168")
    res = await client.post(
        "/api/v1/customers/me/checkup-report",
        headers=_auth(token),
        files={"file": ("labs.pdf", io.BytesIO(pdf), "application/pdf")},
        data={"notes": ""},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["has_checkup_report"] is True
    assert "diabetes" in body["conditions"]
    assert body["diet_filter_enabled"] is False
    assert "checkup_report_url" not in body
    assert "not a diagnosis" in body["disclaimer"].lower()

    me = await client.get("/api/v1/customers/me/diet-profile", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["conditions"] == body["conditions"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:identity:customer": "0-0"}, count=20)
    event_data = json.loads(messages[0][1][-1][1]["data"])
    assert event_data["event_type"] == "customer.diet_profile.updated"
    assert "diabetes" in event_data["payload"]["conditions"]
    assert "report_text" not in event_data["payload"]
    assert "checkup_report_url" not in event_data["payload"]


@pytest.mark.asyncio
async def test_diet_filter_hides_dessert_only_kitchen(
    client: AsyncClient, auth_headers: dict
):
    sweet = await client.post(
        "/api/v1/kitchens",
        json={**KITCHEN_PAYLOAD, "name": "Sweet Only Kitchen", "latitude": 18.5370, "longitude": 73.8960},
        headers=auth_headers,
    )
    savoury = await client.post(
        "/api/v1/kitchens",
        json={**KITCHEN_PAYLOAD, "name": "Dal Kitchen", "latitude": 18.5372, "longitude": 73.8962},
        headers=auth_headers,
    )
    assert sweet.status_code == 201, sweet.text
    assert savoury.status_code == 201, savoury.text
    sweet_id = uuid.UUID(sweet.json()["id"])
    dal_id = uuid.UUID(savoury.json()["id"])
    _seed_dish(sweet_id, name="Gulab Jamun", category_slug="desserts")
    dal_dish = _seed_dish(dal_id, name="Dal Tadka", category_slug="veg")

    token = await _login(client, "+919711222003")
    pdf = _pdf("HbA1c 8.4% Type 2 Diabetes Mellitus")
    uploaded = await client.post(
        "/api/v1/customers/me/checkup-report",
        headers=_auth(token),
        files={"file": ("labs.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text

    public = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958},
    )
    assert public.status_code == 200
    public_names = {k["name"] for k in public.json()["kitchens"]}
    assert "Sweet Only Kitchen" in public_names
    assert "Dal Kitchen" in public_names
    assert public.json()["diet_filter_applied"] is False

    enable = await client.patch(
        "/api/v1/customers/me/diet-filter",
        headers=_auth(token),
        json={"enabled": True},
    )
    assert enable.status_code == 200, enable.text
    assert enable.json()["diet_filter_enabled"] is True

    filtered = await client.get(
        "/api/v1/kitchens/public/nearby",
        headers=_auth(token),
        params={"latitude": 18.5362, "longitude": 73.8958},
    )
    assert filtered.status_code == 200, filtered.text
    body = filtered.json()
    assert body["diet_filter_applied"] is True
    names = [k["name"] for k in body["kitchens"]]
    assert "Dal Kitchen" in names
    assert "Sweet Only Kitchen" not in names
    dal_row = next(k for k in body["kitchens"] if k["name"] == "Dal Kitchen")
    assert dal_row["compatible_dish_count"] >= 1
    assert dal_row["better_for_report"] is True

    veg_only = await client.get(
        "/api/v1/kitchens/public/nearby",
        headers=_auth(token),
        params={"latitude": 18.5362, "longitude": 73.8958, "diet": "veg"},
    )
    assert veg_only.status_code == 200, veg_only.text
    veg_names = [k["name"] for k in veg_only.json()["kitchens"]]
    assert "Dal Kitchen" in veg_names
    assert "Sweet Only Kitchen" not in veg_names
    assert veg_only.json()["diet_filter_applied"] is True

    dishes = await client.get(
        "/api/v1/customers/me/diet-compatible-dishes",
        headers=_auth(token),
        params={"kitchen_id": str(dal_id)},
    )
    assert dishes.status_code == 200
    assert str(dal_dish) in dishes.json()["dish_ids"]

    home = await client.get(
        "/api/v1/discovery/home",
        headers=_auth(token),
        params={"latitude": 18.5362, "longitude": 73.8958, "max_km": 50},
    )
    assert home.status_code == 200
    assert home.json()["diet_filter_applied"] is True
    near_names = {k["name"] for k in home.json()["near_you"]}
    assert "Sweet Only Kitchen" not in near_names
    assert "Dal Kitchen" in near_names


@pytest.mark.asyncio
async def test_filter_blocked_when_flag_disabled(client: AsyncClient):
    token = await _login(client, "+919711222004")
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE ckac_identity.feature_flags SET enabled = false "
            "WHERE key = 'customer_diet_report'"
        )
    conn.close()
    try:
        res = await client.post(
            "/api/v1/customers/me/checkup-report",
            headers=_auth(token),
            files={"file": ("labs.pdf", io.BytesIO(_pdf("HbA1c 8.2 diabetes")), "application/pdf")},
        )
        assert res.status_code == 403, res.text
        assert "customer_diet_report" in res.json()["detail"]
    finally:
        conn = psycopg2.connect(SYNC_DB_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE ckac_identity.feature_flags SET enabled = true "
                "WHERE key = 'customer_diet_report'"
            )
        conn.close()


@pytest.mark.asyncio
async def test_admin_customer_shows_conditions_not_file(client: AsyncClient):
    token = await _login(client, "+919711222005")
    uploaded = await client.post(
        "/api/v1/customers/me/checkup-report",
        headers=_auth(token),
        files={
            "file": (
                "labs.pdf",
                io.BytesIO(_pdf("HbA1c 8.2% Type 2 Diabetes Mellitus")),
                "application/pdf",
            )
        },
    )
    assert uploaded.status_code == 200, uploaded.text
    customer_id = uploaded.json()["id"] if "id" in uploaded.json() else None
    profile = await client.get("/api/v1/customers/me", headers=_auth(token))
    customer_id = profile.json()["id"]

    headers = await _admin_headers(client)
    detail = await client.get(f"/api/v1/admin/customers/{customer_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["has_checkup_report"] is True
    assert "diabetes" in body["diet_conditions"]
    assert "checkup_report_url" not in body
    listing = await client.get("/api/v1/admin/customers", headers=headers)
    row = next(r for r in listing.json() if r["id"] == customer_id)
    assert row["has_checkup_report"] is True
