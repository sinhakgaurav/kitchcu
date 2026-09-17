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
    assert data["address_line"] == KITCHEN_PAYLOAD["address_line"]
    assert data["pincode"] == KITCHEN_PAYLOAD["pincode"]
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
async def test_update_kitchen_profile_requires_auth(client: AsyncClient):
    response = await client.patch(
        f"/api/v1/kitchens/{uuid.uuid4()}/profile",
        json={"name": "Moved Kitchen"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_kitchen_profile_owner_can_fix_pin(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    assert created.status_code == 201
    kitchen_id = created.json()["id"]
    code = created.json()["code"]

    response = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/profile",
        json={
            "name": "Raj Home Kitchen Koregaon",
            "address_line": "Lane 7, Koregaon Park",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "latitude": 19.0760,
            "longitude": 72.8777,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Raj Home Kitchen Koregaon"
    assert data["address_line"] == "Lane 7, Koregaon Park"
    assert data["city"] == "Mumbai"
    assert data["pincode"] == "400001"
    assert data["code"] == code
    assert data["latitude"] == pytest.approx(19.0760, rel=1e-4)
    assert data["longitude"] == pytest.approx(72.8777, rel=1e-4)


@pytest.mark.asyncio
async def test_update_kitchen_profile_tenant_isolated(
    client: AsyncClient, auth_headers: dict
):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    assert created.status_code == 201
    kitchen_id = created.json()["id"]

    other_phone = str(uuid.uuid4().int % 4_000_000_000 + 6_000_000_000)
    reg = await client.post(
        "/api/v1/owners/register",
        json={"phone": other_phone, "name": "Other Owner"},
    )
    assert reg.status_code == 201
    await client.post("/api/v1/auth/otp/request", json={"phone": reg.json()["phone"]})
    token_resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": reg.json()["phone"], "otp": "123456"},
    )
    other_headers = {"Authorization": f"Bearer {token_resp.json()['access_token']}"}

    response = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/profile",
        json={"name": "Hijacked"},
        headers=other_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_kitchen_profile_invalid_coordinates(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen_id = created.json()["id"]
    response = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/profile",
        json={"latitude": 999, "longitude": 73.8},
        headers=auth_headers,
    )
    assert response.status_code == 422


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
    assert "avg_rating" in kitchens[0]
    assert kitchens[0]["rating_count"] == 0


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
    dish_name: str = "Test Dish",
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
                (id, kitchen_id, category_id, name, price, prep_time_min, delivery_time_min, max_time_min, is_active)
                VALUES (%s::uuid, %s::uuid, %s::uuid, %s, 149.00, 20, 15, 35, true)
                """,
                (str(dish_id), str(kitchen_id), str(category_id), dish_name),
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


@pytest.mark.asyncio
async def test_nearby_kitchens_search_matches_dish_name(client: AsyncClient, auth_headers: dict):
    """A diner searching a dish finds the kitchen that cooks it, not every kitchen in range."""
    samosa = {**KITCHEN_PAYLOAD, "name": "Chaat Corner", "latitude": 18.5370, "longitude": 73.8960}
    biryani = {**KITCHEN_PAYLOAD, "name": "Dum Handi", "latitude": 18.5372, "longitude": 73.8962}

    samosa_resp = await client.post("/api/v1/kitchens", json=samosa, headers=auth_headers)
    biryani_resp = await client.post("/api/v1/kitchens", json=biryani, headers=auth_headers)
    assert samosa_resp.status_code == 201
    assert biryani_resp.status_code == 201

    _seed_catalog_for_kitchen(uuid.UUID(samosa_resp.json()["id"]), dish_name="Samosa (2 pc)")
    _seed_catalog_for_kitchen(uuid.UUID(biryani_resp.json()["id"]), dish_name="Veg Biryani")

    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "q": "samosa"},
    )
    assert resp.status_code == 200
    assert [k["name"] for k in resp.json()["kitchens"]] == ["Chaat Corner"]


@pytest.mark.asyncio
async def test_nearby_search_and_diet_apply_together(client: AsyncClient, auth_headers: dict):
    """Diet must not wipe free-text search — both filters stay on."""
    veg = await client.post(
        "/api/v1/kitchens",
        json={**KITCHEN_PAYLOAD, "name": "Veg Samosa Kitchen", "latitude": 18.5370, "longitude": 73.8960},
        headers=auth_headers,
    )
    meat = await client.post(
        "/api/v1/kitchens",
        json={**KITCHEN_PAYLOAD, "name": "Nonveg Samosa Kitchen", "latitude": 18.5372, "longitude": 73.8962},
        headers=auth_headers,
    )
    assert veg.status_code == 201
    assert meat.status_code == 201
    _seed_catalog_for_kitchen(uuid.UUID(veg.json()["id"]), category_slug="veg", dish_name="Samosa")
    _seed_catalog_for_kitchen(uuid.UUID(meat.json()["id"]), category_slug="non_veg", dish_name="Samosa")

    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "q": "samosa", "diet": "veg"},
    )
    assert resp.status_code == 200
    assert [k["name"] for k in resp.json()["kitchens"]] == ["Veg Samosa Kitchen"]


@pytest.mark.asyncio
async def test_nearby_kitchens_search_matches_kitchen_fields(client: AsyncClient, auth_headers: dict):
    """Name, code, and city stay searchable alongside dish names."""
    created = await client.post(
        "/api/v1/kitchens",
        json={**KITCHEN_PAYLOAD, "name": "Sharma Home Kitchen"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    code = created.json()["code"]

    for term in ("sharma", "pune", code.lower()):
        resp = await client.get(
            "/api/v1/kitchens/public/nearby",
            params={"latitude": 18.5362, "longitude": 73.8958, "q": term},
        )
        assert resp.status_code == 200, term
        assert resp.json()["total"] == 1, term


@pytest.mark.asyncio
async def test_nearby_kitchens_search_without_match_is_empty(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "q": "definitely-not-on-any-menu"},
    )
    assert resp.status_code == 200
    assert resp.json()["kitchens"] == []


@pytest.mark.asyncio
async def test_nearby_falls_back_to_nearest_when_radius_is_empty(client: AsyncClient, auth_headers: dict):
    """Out of range must not dead-end: return the nearest kitchens with real distances."""
    mumbai = {
        **KITCHEN_PAYLOAD,
        "name": "Bandra Tiffin Room",
        "city": "Mumbai",
        "latitude": 19.0760,
        "longitude": 72.8777,
    }
    assert (await client.post("/api/v1/kitchens", json=mumbai, headers=auth_headers)).status_code == 201

    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "max_km": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kitchens"] == []
    assert data["total"] == 0
    assert len(data["nearest"]) == 1
    assert data["nearest"][0]["name"] == "Bandra Tiffin Room"
    assert data["nearest"][0]["distance_km"] > 10


@pytest.mark.asyncio
async def test_nearest_fallback_respects_the_search_term(client: AsyncClient, auth_headers: dict):
    """Searching a dish from an unserved city answers with kitchens that actually cook it."""
    samosa = {
        **KITCHEN_PAYLOAD,
        "name": "Bandra Chaat Cart",
        "city": "Mumbai",
        "latitude": 19.0760,
        "longitude": 72.8777,
    }
    biryani = {
        **KITCHEN_PAYLOAD,
        "name": "Bandra Dum Handi",
        "city": "Mumbai",
        "latitude": 19.0770,
        "longitude": 72.8787,
    }
    samosa_resp = await client.post("/api/v1/kitchens", json=samosa, headers=auth_headers)
    biryani_resp = await client.post("/api/v1/kitchens", json=biryani, headers=auth_headers)
    _seed_catalog_for_kitchen(uuid.UUID(samosa_resp.json()["id"]), dish_name="Samosa (2 pc)")
    _seed_catalog_for_kitchen(uuid.UUID(biryani_resp.json()["id"]), dish_name="Veg Biryani")

    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "max_km": 10, "q": "samosa"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kitchens"] == []
    assert [k["name"] for k in data["nearest"]] == ["Bandra Chaat Cart"]


@pytest.mark.asyncio
async def test_nearby_omits_nearest_when_radius_has_results(client: AsyncClient, auth_headers: dict):
    assert (await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)).status_code == 201
    resp = await client.get(
        "/api/v1/kitchens/public/nearby",
        params={"latitude": 18.5362, "longitude": 73.8958, "max_km": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["nearest"] == []
