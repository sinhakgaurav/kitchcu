"""Customer discovery home feed — near you, featured, liked, cheapest dishes."""

import uuid

import pytest
from httpx import AsyncClient

from tests.test_kitchens import KITCHEN_PAYLOAD, _seed_catalog_for_kitchen


@pytest.mark.asyncio
async def test_discovery_home_empty_area(client: AsyncClient):
    resp = await client.get(
        "/api/v1/discovery/home",
        params={"latitude": 28.6139, "longitude": 77.2090, "max_km": 10},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["near_you"] == []
    assert data["featured"] == []
    assert data["most_liked"] == []
    assert data["live_now"] == []
    assert data["cheapest_dishes"] == []
    assert data["customer_latitude"] == 28.6139


@pytest.mark.asyncio
async def test_discovery_home_includes_nearby_kitchen(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    assert created.status_code == 201
    kitchen_id = created.json()["id"]
    _seed_catalog_for_kitchen(uuid.UUID(kitchen_id))

    await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/branded-page",
        headers=auth_headers,
        json={"enabled": True, "tagline": "Discovery specials"},
    )

    resp = await client.get(
        "/api/v1/discovery/home",
        params={
            "latitude": KITCHEN_PAYLOAD["latitude"],
            "longitude": KITCHEN_PAYLOAD["longitude"],
            "max_km": 25,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_kitchens"] >= 1
    assert any(k["id"] == kitchen_id for k in data["near_you"])
    assert any(k["id"] == kitchen_id for k in data["featured"])
    featured = next(k for k in data["featured"] if k["id"] == kitchen_id)
    assert featured["tagline"] == "Discovery specials"
    assert "distance_km" in featured


async def _discovery(client: AsyncClient, **params) -> dict:
    resp = await client.get(
        "/api/v1/discovery/home",
        params={
            "latitude": KITCHEN_PAYLOAD["latitude"],
            "longitude": KITCHEN_PAYLOAD["longitude"],
            "max_km": 25,
            **params,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_discovery_search_matches_kitchen_name_case_insensitively(
    client: AsyncClient, auth_headers: dict
):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    assert created.status_code == 201
    kitchen_id = created.json()["id"]
    _seed_catalog_for_kitchen(uuid.UUID(kitchen_id))
    name = created.json()["name"]

    hit = await _discovery(client, q=name[:6].lower())
    assert hit["total_kitchens"] >= 1
    assert any(k["id"] == kitchen_id for k in hit["near_you"])


@pytest.mark.asyncio
async def test_discovery_search_matches_kitchen_code_and_city(
    client: AsyncClient, auth_headers: dict
):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen = created.json()
    _seed_catalog_for_kitchen(uuid.UUID(kitchen["id"]))

    by_code = await _discovery(client, q=kitchen["code"])
    assert any(k["id"] == kitchen["id"] for k in by_code["near_you"])

    by_city = await _discovery(client, q=KITCHEN_PAYLOAD["city"])
    assert any(k["id"] == kitchen["id"] for k in by_city["near_you"])


@pytest.mark.asyncio
async def test_discovery_search_no_match_returns_empty(client: AsyncClient, auth_headers: dict):
    await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)

    miss = await _discovery(client, q="zzz-no-such-kitchen-zzz")
    assert miss["total_kitchens"] == 0
    assert miss["near_you"] == []
    assert miss["featured"] == []
    assert miss["cheapest_dishes"] == []


@pytest.mark.asyncio
async def test_discovery_search_wildcards_are_literal(client: AsyncClient, auth_headers: dict):
    """A bare % must not behave like "match everything"."""
    await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)

    resp = await _discovery(client, q="%")
    assert resp["total_kitchens"] == 0


@pytest.mark.asyncio
async def test_discovery_blank_search_is_ignored(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    kitchen_id = created.json()["id"]
    _seed_catalog_for_kitchen(uuid.UUID(kitchen_id))

    blank = await _discovery(client, q="   ")
    assert any(k["id"] == kitchen_id for k in blank["near_you"])
