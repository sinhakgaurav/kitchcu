import uuid

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL

KITCHEN_PAYLOAD = {
    "name": "Raj Home Kitchen",
    "address_line": "Koregaon Park",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411001",
    "latitude": 18.5362,
    "longitude": 73.8958,
}


@pytest.mark.asyncio
async def test_create_kitchen_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_kitchen_success(client: AsyncClient, auth_headers: dict):
    response = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "CKPNQ001"
    assert data["name"] == KITCHEN_PAYLOAD["name"]
    assert data["city"] == "Pune"
    assert data["state"] == "Maharashtra"
    assert data["status"] == "active"
    assert data["free_delivery_radius_km"] == 3.0
    assert data["max_delivery_radius_km"] == 10.0
    assert data["latitude"] == pytest.approx(18.5362, rel=1e-4)
    assert data["longitude"] == pytest.approx(73.8958, rel=1e-4)
    assert "id" in data
    assert "owner_id" in data


@pytest.mark.asyncio
async def test_create_kitchen_increments_code(client: AsyncClient, auth_headers: dict):
    for expected_code in ("CKPNQ001", "CKPNQ002"):
        payload = {**KITCHEN_PAYLOAD, "name": f"Kitchen {expected_code}"}
        response = await client.post("/api/v1/kitchens", json=payload, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["code"] == expected_code


@pytest.mark.asyncio
async def test_list_kitchens_empty(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/kitchens/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_kitchens_returns_owner_kitchens(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    response = await client.get("/api/v1/kitchens/me", headers=auth_headers)
    assert response.status_code == 200
    kitchens = response.json()
    assert len(kitchens) == 1
    assert kitchens[0]["code"] == "CKPNQ001"
    assert kitchens[0]["name"] == KITCHEN_PAYLOAD["name"]


@pytest.mark.asyncio
async def test_create_kitchen_invalid_coordinates(client: AsyncClient, auth_headers: dict):
    payload = {**KITCHEN_PAYLOAD, "latitude": 999}
    response = await client.post("/api/v1/kitchens", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_full_onboarding_flow(client: AsyncClient, unique_phone: str):
    """End-to-end: register → OTP → create kitchen → list kitchens."""
    reg = await client.post(
        "/api/v1/owners/register",
        json={"phone": unique_phone, "name": "Flow Owner"},
    )
    assert reg.status_code == 201
    phone = reg.json()["phone"]

    await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    token_resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    headers = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}

    kitchen_resp = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=headers)
    assert kitchen_resp.status_code == 201

    me_resp = await client.get("/api/v1/owners/me", headers=headers)
    assert me_resp.status_code == 200

    list_resp = await client.get("/api/v1/kitchens/me", headers=headers)
    assert len(list_resp.json()) == 1

    code = kitchen_resp.json()["code"]
    public_resp = await client.get(f"/api/v1/kitchens/public/by-code/{code}")
    assert public_resp.status_code == 200
    assert public_resp.json()["name"] == KITCHEN_PAYLOAD["name"]


@pytest.mark.asyncio
async def test_nearby_kitchens_empty(client: AsyncClient):
    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kitchens"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_nearby_kitchens_sorted_by_distance(client: AsyncClient, auth_headers: dict):
    """Nearest kitchen first (sort=asc)."""
    locations = [
        {**KITCHEN_PAYLOAD, "name": "Far Kitchen", "latitude": 18.60, "longitude": 73.95},
        {**KITCHEN_PAYLOAD, "name": "Near Kitchen", "latitude": 18.5370, "longitude": 73.8960},
    ]
    for payload in locations:
        r = await client.post("/api/v1/kitchens", json=payload, headers=auth_headers)
        assert r.status_code == 201

    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "sort": "asc"},
    )
    assert resp.status_code == 200
    kitchens = resp.json()["kitchens"]
    assert len(kitchens) == 2
    assert kitchens[0]["name"] == "Near Kitchen"
    assert kitchens[0]["distance_km"] < kitchens[1]["distance_km"]
    assert "latitude" in kitchens[0]


@pytest.mark.asyncio
async def test_nearby_kitchens_sort_desc(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "sort": "desc"},
    )
    assert resp.status_code == 200
    assert resp.json()["sort"] == "desc"


def _seed_catalog_for_kitchen(
    kitchen_id: uuid.UUID,
    *,
    category_slug: str = "veg",
    live_capture: bool = False,
) -> None:
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
            (id, kitchen_id, category_id, name, price, prep_time_min, is_active)
            VALUES (%s::uuid, %s::uuid, %s::uuid, 'Test Dish', 149.00, 20, true)
            """,
            (str(dish_id), str(kitchen_id), str(category_id)),
        )
        if live_capture:
            cur.execute(
                """
                INSERT INTO ckac_catalog.dish_media
                (id, dish_id, url, is_hero, is_live_capture)
                VALUES (%s::uuid, %s::uuid, 'https://example.com/live.jpg', true, true)
                """,
                (str(uuid.uuid4()), str(dish_id)),
            )
    conn.close()


@pytest.mark.asyncio
async def test_nearby_kitchens_diet_filter(client: AsyncClient, auth_headers: dict):
    veg_payload = {**KITCHEN_PAYLOAD, "name": "Veg Kitchen", "latitude": 18.5370, "longitude": 73.8960}
    non_veg_payload = {**KITCHEN_PAYLOAD, "name": "Non-Veg Kitchen", "latitude": 18.5375, "longitude": 73.8965}

    veg_resp = await client.post("/api/v1/kitchens", json=veg_payload, headers=auth_headers)
    non_veg_resp = await client.post("/api/v1/kitchens", json=non_veg_payload, headers=auth_headers)
    assert veg_resp.status_code == 201
    assert non_veg_resp.status_code == 201

    _seed_catalog_for_kitchen(uuid.UUID(veg_resp.json()["id"]), category_slug="veg")
    _seed_catalog_for_kitchen(uuid.UUID(non_veg_resp.json()["id"]), category_slug="non_veg")

    all_resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958},
    )
    assert all_resp.status_code == 200
    assert all_resp.json()["total"] == 2

    veg_only = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "diet": "veg"},
    )
    assert veg_only.status_code == 200
    names = [k["name"] for k in veg_only.json()["kitchens"]]
    assert names == ["Veg Kitchen"]
    assert veg_only.json()["kitchens"][0]["has_veg"] is True


@pytest.mark.asyncio
async def test_nearby_kitchens_live_capture_filter(client: AsyncClient, auth_headers: dict):
    plain_payload = {**KITCHEN_PAYLOAD, "name": "Plain Kitchen", "latitude": 18.5370, "longitude": 73.8960}
    live_payload = {**KITCHEN_PAYLOAD, "name": "Live Photo Kitchen", "latitude": 18.5372, "longitude": 73.8962}

    plain_resp = await client.post("/api/v1/kitchens", json=plain_payload, headers=auth_headers)
    live_resp = await client.post("/api/v1/kitchens", json=live_payload, headers=auth_headers)
    assert plain_resp.status_code == 201
    assert live_resp.status_code == 201

    _seed_catalog_for_kitchen(uuid.UUID(plain_resp.json()["id"]), category_slug="veg", live_capture=False)
    _seed_catalog_for_kitchen(uuid.UUID(live_resp.json()["id"]), category_slug="veg", live_capture=True)

    filtered = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "live_capture": True},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["kitchens"][0]["name"] == "Live Photo Kitchen"
    assert filtered.json()["kitchens"][0]["has_live_capture"] is True
